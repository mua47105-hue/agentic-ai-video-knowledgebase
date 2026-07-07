"""
Visual feature extraction for the intelligent pipeline (Phase 6).

Extracts per-frame / per-window visual features. Every heavy-model dependency is
OPTIONAL: if a model is not installed, the corresponding features are simply
omitted and the rest of the profile is still produced. This keeps the framework
runnable on a minimal install (ffmpeg + opencv + numpy) while unlocking richer
signals when mediapipe / hsemotion / open-clip / easyocr / pyscenedetect are
available.

Public surface:
  - probe_visual(video_path) -> VisualProfile (dataclass + .as_dict())

Features extracted (best-effort, in order of weight):
  - ffprobe metadata (always)
  - scene boundaries via PySceneDetect (falls back to ffmpeg scdet)
  - face presence + emotion via MediaPipe Face Landmarker + HSEmotion (optional)
  - motion energy via OpenCV frame differencing (always, opencv required)
  - aesthetic score via LAION-Aesthetic + CLIP-L/14 (optional, subsampled)
  - shot-scale classification via MediaPipe Face Detector (optional)
  - on-screen text via EasyOCR (optional, subsampled)
"""
from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import subprocess
import tempfile
import typing as t
from collections import defaultdict


@dataclasses.dataclass
class VisualFrameFeatures:
    timestamp: float
    face_present: bool = False
    face_emotion: t.Optional[str] = None
    face_arousal: float = 0.0
    face_valence: float = 0.5
    motion_energy: float = 0.0
    aesthetic_score: float = 0.5
    shot_scale: str = "unknown"
    ocr_text: t.Optional[str] = None


@dataclasses.dataclass
class VisualProfile:
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    aspect_ratio: float = 0.0
    has_video_stream: bool = False
    codec: str = "unknown"
    scene_boundaries: list[float] = dataclasses.field(default_factory=list)
    frame_features: list[dict] = dataclasses.field(default_factory=list)
    per_second: list[dict] = dataclasses.field(default_factory=list)
    motion_peaks: list[dict] = dataclasses.field(default_factory=list)
    emotion_peaks: list[dict] = dataclasses.field(default_factory=list)
    aesthetic_peaks: list[dict] = dataclasses.field(default_factory=list)
    components_used: list[str] = dataclasses.field(default_factory=list)

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


# ── ffprobe metadata (always available) ──

def probe_ffprobe(video_path: str) -> dict:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate,codec_name:format=duration",
             "-of", "json", video_path],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        if not streams:
            return {}
        s = streams[0]
        fps_str = s.get("r_frame_rate", "30/1")
        try:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        except (ValueError, ZeroDivisionError):
            fps = 30.0
        w = int(s.get("width", 0))
        h = int(s.get("height", 0))
        return {
            "duration": float(fmt.get("duration", 0)),
            "width": w,
            "height": h,
            "fps": fps,
            "aspect_ratio": (w / h) if h else 0.0,
            "codec": s.get("codec_name", "unknown"),
        }
    except Exception:
        return {}


# ── Scene detection ──

def probe_scenes(video_path: str, threshold: float = 27.0) -> list[float]:
    """Prefer PySceneDetect; fall back to ffmpeg scdet."""
    try:
        from scenedetect import detect, AdaptiveDetector
        scene_list = detect(video_path, AdaptiveDetector(adaptive_threshold=threshold))
        return [float(scene[0].get_seconds()) for scene in scene_list]
    except Exception:
        return _probe_scenes_ffmpeg(video_path, threshold)


def _probe_scenes_ffmpeg(video_path: str, threshold: float) -> list[float]:
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", video_path, "-hide_banner", "-nostats",
             "-filter:v", f"scdet=threshold={threshold}", "-f", "null", "-"],
            capture_output=True, text=True, timeout=600,
        )
        boundaries = [0.0]
        for line in result.stderr.split("\n"):
            if "scene_change" in line:
                try:
                    ts_str = line.split("scene_change:")[1].strip().split()[0]
                    boundaries.append(float(ts_str))
                except (ValueError, IndexError):
                    pass
        return sorted(set(boundaries))
    except Exception:
        return []


# ── Motion energy (OpenCV frame differencing) ──

def probe_motion(video_path: str, fps: float, duration: float,
                 sample_stride: int = 1) -> tuple[list[dict], list[dict]]:
    """Returns (per_frame_features, motion_peaks). Falls back to cv2.VideoCapture if PyAV missing."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return [], []

    features: list[dict] = []
    energies: list[float] = []
    timestamps: list[float] = []
    prev_gray = None
    frame_idx = 0

    # Try PyAV first (faster), fall back to cv2.VideoCapture (P1 #3 fix)
    use_pyav = False
    try:
        import av
        use_pyav = True
    except ImportError:
        pass

    if use_pyav:
        try:
            container = av.open(video_path)
            for frame in container.decode(video=0):
                if frame_idx % sample_stride != 0:
                    frame_idx += 1
                    continue
                ts = frame_idx / fps if fps > 0 else 0.0
                if ts > duration:
                    break
                try:
                    img = frame.to_ndarray(format="bgr24")
                    small = cv2.resize(img, (160, 90))
                    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
                    if prev_gray is not None:
                        diff = np.abs(gray - prev_gray)
                        energy = float(diff.mean())
                        energies.append(energy)
                        timestamps.append(ts)
                        features.append({"timestamp": ts, "motion_energy": energy})
                    prev_gray = gray
                except Exception:
                    pass
                frame_idx += 1
            container.close()
        except Exception:
            use_pyav = False  # fall through to cv2

    if not use_pyav:
        # Fallback: cv2.VideoCapture (P1 #3 fix — always available when opencv installed)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return [], []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_stride != 0:
                frame_idx += 1
                continue
            ts = frame_idx / fps if fps > 0 else 0.0
            if ts > duration:
                break
            try:
                small = cv2.resize(frame, (160, 90))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
                if prev_gray is not None:
                    diff = np.abs(gray - prev_gray)
                    energy = float(diff.mean())
                    energies.append(energy)
                    timestamps.append(ts)
                    features.append({"timestamp": ts, "motion_energy": energy})
                prev_gray = gray
            except Exception:
                pass
            frame_idx += 1
        cap.release()

    if not energies:
        return [], []

    arr = np.array(energies)
    mean_e = float(arr.mean())
    std_e = float(arr.std())
    baseline = mean_e + 2 * std_e

    peaks: list[dict] = []
    for ts, e in zip(timestamps, energies):
        if e > baseline and std_e > 0:
            sigma = (e - mean_e) / std_e
            peaks.append({"timestamp": ts, "intensity": float(e), "sigma": float(sigma)})

    # Merge adjacent peaks within 0.5s
    merged = _merge_adjacent_peaks(peaks, gap=0.5)

    # Normalize motion_energy to 0-1
    max_e = max(energies) if energies else 1.0
    for f in features:
        f["motion_energy"] = f["motion_energy"] / max_e if max_e > 0 else 0.0

    return features, merged


def _merge_adjacent_peaks(peaks: list[dict], gap: float = 0.5) -> list[dict]:
    if not peaks:
        return []
    merged = [peaks[0]]
    for p in peaks[1:]:
        if p["timestamp"] - merged[-1]["timestamp"] <= gap:
            if p["sigma"] > merged[-1]["sigma"]:
                merged[-1] = p
        else:
            merged.append(p)
    return merged


# ── Face + emotion (MediaPipe + HSEmotion — optional) ──

# Emotion map from blendshape categories (rule-based, FACS-inspired)
_BLENDSPACE_EMOTION_MAP = {
    "happy": [("mouthSmileLeft", 1.0), ("mouthSmileRight", 1.0), ("cheekSquintLeft", 0.5), ("cheekSquintRight", 0.5)],
    "sad": [("mouthFrownLeft", 1.0), ("mouthFrownRight", 1.0), ("browInnerUp", 0.7)],
    "angry": [("browDownLeft", 1.0), ("browDownRight", 1.0), ("jawOpen", 0.3)],
    "surprise": [("eyeWideLeft", 1.0), ("eyeWideRight", 1.0), ("jawOpen", 0.8), ("browOuterUpLeft", 0.7), ("browOuterUpRight", 0.7)],
    "fear": [("eyeWideLeft", 0.8), ("eyeWideRight", 0.8), ("browInnerUp", 0.7), ("jawOpen", 0.5)],
    "disgust": [("noseSneerLeft", 1.0), ("noseSneerRight", 1.0), ("mouthFrownLeft", 0.5)],
    "neutral": [],
}

# Russell circumplex arousal/valence per emotion
_EMOTION_AV = {
    "happy": (0.5, 0.9), "sad": (0.2, 0.2), "angry": (0.85, 0.3),
    "surprise": (0.9, 0.7), "fear": (0.9, 0.2), "disgust": (0.6, 0.2),
    "neutral": (0.3, 0.5),
}


def probe_faces(video_path: str, fps: float, duration: float,
                sample_stride: int = 6) -> list[dict]:
    """Face presence + emotion. Requires mediapipe. Returns [] if unavailable."""
    try:
        import av
        import mediapipe as mp
    except ImportError:
        return []

    features: list[dict] = []
    frame_idx = 0
    try:
        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode
    except Exception:
        return []

    model_path = _mediapipe_model_path("face_landmarker.task")
    if not model_path:
        return []

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True,
    )

    try:
        container = av.open(video_path)
        with FaceLandmarker.create_from_options(options) as landmarker:
            for frame in container.decode(video=0):
                if frame_idx % sample_stride != 0:
                    frame_idx += 1
                    continue
                ts = frame_idx / fps if fps > 0 else 0.0
                if ts > duration:
                    break
                try:
                    img = frame.to_ndarray(format="rgb24")
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)
                    result = landmarker.detect_for_video(mp_image, int(ts * 1000))
                    if result.face_blendshapes:
                        bs = result.face_blendshapes[0]
                        emotion, arousal, valence = _classify_emotion_from_blendshapes(bs)
                        features.append({
                            "timestamp": ts,
                            "face_present": True,
                            "face_emotion": emotion,
                            "face_arousal": arousal,
                            "face_valence": valence,
                        })
                except Exception:
                    pass
                frame_idx += 1
        container.close()
    except Exception:
        pass
    return features


def _classify_emotion_from_blendshapes(blendshapes) -> tuple[str, float, float]:
    bs_dict = {b.category_name: b.score for b in blendshapes}
    scores: dict[str, float] = {}
    for emotion, indicators in _BLENDSPACE_EMOTION_MAP.items():
        if not indicators:
            continue
        scores[emotion] = sum(bs_dict.get(name, 0) * weight for name, weight in indicators)
    if not scores:
        return "neutral", 0.3, 0.5
    top = max(scores, key=scores.get)
    top_score = scores[top]
    base_aro, base_val = _EMOTION_AV.get(top, (0.3, 0.5))
    arousal = min(1.0, base_aro * top_score * 2)
    return top, arousal, base_val


def _mediapipe_model_path(model_name: str) -> t.Optional[str]:
    cache_dir = pathlib.Path.home() / ".cache" / "mediapipe"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / model_name
    if cache_path.exists():
        return str(cache_path)
    urls = {
        "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "face_detector.task": "https://storage.googleapis.com/mediapipe-models/face_detector/face_detector_short_range/float16/1/face_detector_short_range.task",
    }
    if model_name not in urls:
        return None
    try:
        import urllib.request
        urllib.request.urlretrieve(urls[model_name], str(cache_path))
        return str(cache_path)
    except Exception:
        return None


# ── Aesthetic scoring (LAION-Aesthetic — optional, subsampled) ──

_AESTHETIC_MODEL = None


def probe_aesthetic(video_path: str, fps: float, duration: float,
                    sample_every_n_seconds: float = 4.0) -> list[dict]:
    """Aesthetic scoring. Default samples every 4s (was 2s) — 2x speedup, low quality risk
    (aesthetic scores are smooth across adjacent frames; 4s still captures the distribution)."""
    try:
        import av
        import torch
        from PIL import Image
    except ImportError:
        return []

    model_fn, preprocess = _load_aesthetic_model()
    if model_fn is None:
        return []

    features: list[dict] = []
    stride = max(1, int(fps * sample_every_n_seconds))
    try:
        container = av.open(video_path)
        frame_idx = 0
        for frame in container.decode(video=0):
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            ts = frame_idx / fps if fps > 0 else 0.0
            if ts > duration:
                break
            try:
                img = frame.to_ndarray(format="rgb24")
                pil = Image.fromarray(img)
                with torch.no_grad():
                    tensor = preprocess(pil).unsqueeze(0)
                    score = model_fn(tensor).item()
                normalized = max(0.0, min(1.0, (score + 2) / 4))
                features.append({"timestamp": ts, "aesthetic_score": normalized})
            except Exception:
                pass
            frame_idx += 1
        container.close()
    except Exception:
        pass
    return features


def _load_aesthetic_model():
    global _AESTHETIC_MODEL
    if _AESTHETIC_MODEL is not None:
        return _AESTHETIC_MODEL
    try:
        import clip
        import torch
        from urllib.request import urlretrieve

        model_path = pathlib.Path(tempfile.gettempdir()) / "aesthetic_predictor_v1.pt"
        if not model_path.exists():
            urlretrieve(
                "https://github.com/LAION-AI/aesthetic-predictor/blob/main/saved_models/aesthetic_predictor_v1.pt?raw=true",
                str(model_path),
            )
        clip_model, preprocess = clip.load("ViT-L/14", device="cpu")
        aesthetic_head = torch.nn.Linear(768, 1)
        aesthetic_head.load_state_dict(torch.load(str(model_path), map_location="cpu"))
        aesthetic_head.eval()

        def combined(img_tensor):
            with torch.no_grad():
                feats = clip_model.encode_image(img_tensor).float()
                return aesthetic_head(feats)

        _AESTHETIC_MODEL = (combined, preprocess)
    except Exception:
        _AESTHETIC_MODEL = (None, None)
    return _AESTHETIC_MODEL


# ── Shot-scale classification (MediaPipe Face Detector — optional) ──

def probe_shot_scale(video_path: str, scene_boundaries: list[float],
                     fps: float, duration: float) -> dict[float, str]:
    try:
        import av
        import mediapipe as mp
    except ImportError:
        return {}

    try:
        BaseOptions = mp.tasks.BaseOptions
        FaceDetector = mp.tasks.vision.FaceDetector
        FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
        VisionRunningMode = mp.tasks.vision.RunningMode
    except Exception:
        return {}

    model_path = _mediapipe_model_path("face_detector.task")
    if not model_path:
        return {}

    options = FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.VIDEO,
    )

    shot_scales: dict[float, str] = {}
    try:
        container = av.open(video_path)
        scene_starts = list(scene_boundaries) + [duration]
        with FaceDetector.create_from_options(options) as detector:
            for i, start in enumerate(scene_starts[:-1]):
                end = scene_starts[i + 1]
                mid_ts = (start + end) / 2
                if mid_ts > duration or mid_ts < 0:
                    continue
                try:
                    container.seek(int(mid_ts * 1e6), stream=container.streams.video[0])
                    frame = next(container.decode(video=0))
                except (StopIteration, Exception):
                    continue
                try:
                    img = frame.to_ndarray(format="rgb24")
                    h, w = img.shape[:2]
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)
                    result = detector.detect_for_video(mp_image, int(mid_ts * 1000))
                    if result.detections:
                        bbox = result.detections[0].bounding_box
                        ratio = (bbox.width * bbox.height) / (w * h)
                        if ratio > 0.30:
                            shot_scales[start] = "close_up"
                        elif ratio > 0.10:
                            shot_scales[start] = "medium"
                        else:
                            shot_scales[start] = "wide"
                    else:
                        shot_scales[start] = "wide"
                except Exception:
                    shot_scales[start] = "unknown"
        container.close()
    except Exception:
        pass
    return shot_scales


# ── OCR (EasyOCR — optional, subsampled) ──

_EASYOCR_READER = None


def probe_ocr(video_path: str, fps: float, duration: float,
              sample_every_n_seconds: float = 3.0) -> list[dict]:
    global _EASYOCR_READER
    try:
        import av
        import easyocr
    except ImportError:
        return []

    if _EASYOCR_READER is None:
        try:
            _EASYOCR_READER = easyocr.Reader(["en"], gpu=False)
        except Exception:
            return []

    features: list[dict] = []
    stride = max(1, int(fps * sample_every_n_seconds))
    try:
        container = av.open(video_path)
        frame_idx = 0
        for frame in container.decode(video=0):
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            ts = frame_idx / fps if fps > 0 else 0.0
            if ts > duration:
                break
            try:
                img = frame.to_ndarray(format="rgb24")
                results = _EASYOCR_READER.readtext(img)
                if results:
                    text = " ".join(r[1] for r in results if r[2] > 0.5)
                    if text.strip():
                        features.append({"timestamp": ts, "ocr_text": text.strip()})
            except Exception:
                pass
            frame_idx += 1
        container.close()
    except Exception:
        pass
    return features


# ── Top-level visual probe ──

def probe_visual(video_path: str) -> VisualProfile:
    """Run all available visual probes, merge into VisualProfile."""
    profile = VisualProfile()
    components: list[str] = []

    # 1. ffprobe metadata (always)
    meta = probe_ffprobe(video_path)
    profile.duration = meta.get("duration", 0.0)
    profile.width = meta.get("width", 0)
    profile.height = meta.get("height", 0)
    profile.fps = meta.get("fps", 30.0)
    profile.aspect_ratio = meta.get("aspect_ratio", 0.0)
    profile.codec = meta.get("codec", "unknown")
    profile.has_video_stream = bool(meta)
    if profile.has_video_stream:
        components.append("ffprobe")

    if not profile.has_video_stream or profile.duration == 0:
        profile.components_used = components
        return profile

    # 2. Scene boundaries
    # P3 #15 fix: correctly label which scene detection method actually ran
    _scenedetect_available = False
    try:
        import scenedetect  # noqa
        _scenedetect_available = True
    except ImportError:
        pass
    profile.scene_boundaries = probe_scenes(video_path)
    if profile.scene_boundaries:
        components.append("pyscenedetect" if _scenedetect_available else "scdet_fallback")
    else:
        components.append("scdet_fallback" if not _scenedetect_available else "pyscenedetect_no_scenes")

    # 3. Motion energy + peaks (opencv) — sample every 2nd frame (2x speedup, no quality loss for peak detection)
    motion_features, profile.motion_peaks = probe_motion(
        video_path, profile.fps, profile.duration, sample_stride=2
    )
    if motion_features:
        components.append("opencv_motion")

    # 4. Faces + emotion (mediapipe — optional)
    face_features = probe_faces(video_path, profile.fps, profile.duration)
    if face_features:
        components.append("mediapipe_face")

    # 5. Aesthetic (LAION — optional)
    aesthetic_features = probe_aesthetic(video_path, profile.fps, profile.duration)
    if aesthetic_features:
        components.append("laion_aesthetic")

    # 6. Shot scale (mediapipe face detector — optional)
    shot_scales = probe_shot_scale(
        video_path, profile.scene_boundaries, profile.fps, profile.duration
    )
    if shot_scales:
        components.append("shot_scale")

    # 7. OCR (easyocr — optional)
    ocr_features = probe_ocr(video_path, profile.fps, profile.duration)
    if ocr_features:
        components.append("easyocr")

    # 8. Merge into per-second buckets
    face_by_ts = {f["timestamp"]: f for f in face_features}
    motion_by_ts = {f["timestamp"]: f for f in motion_features}
    aesthetic_by_ts = {f["timestamp"]: f for f in aesthetic_features}
    ocr_by_ts = {f["timestamp"]: f for f in ocr_features}

    all_ts = sorted(set(
        list(face_by_ts.keys()) + list(motion_by_ts.keys()) +
        list(aesthetic_by_ts.keys()) + list(ocr_by_ts.keys())
    ))

    per_sec: dict[int, dict] = defaultdict(lambda: {
        "face_present": False, "face_emotion": None,
        "face_arousal": 0.0, "face_valence": 0.5,
        "motion_energy": 0.0, "aesthetic_score": 0.5,
        "ocr_text": None, "shot_scale": "unknown",
    })

    for ts in all_ts:
        sec = int(ts)
        f = face_by_ts.get(ts)
        if f:
            per_sec[sec]["face_present"] = f["face_present"]
            per_sec[sec]["face_emotion"] = f["face_emotion"]
            per_sec[sec]["face_arousal"] = max(per_sec[sec]["face_arousal"], f["face_arousal"])
            per_sec[sec]["face_valence"] = f["face_valence"]
        m = motion_by_ts.get(ts)
        if m:
            per_sec[sec]["motion_energy"] = max(per_sec[sec]["motion_energy"], m["motion_energy"])
        a = aesthetic_by_ts.get(ts)
        if a:
            per_sec[sec]["aesthetic_score"] = a["aesthetic_score"]
        o = ocr_by_ts.get(ts)
        if o:
            per_sec[sec]["ocr_text"] = o["ocr_text"]

    # shot scale per second (from scene mapping)
    for sec in per_sec:
        for scene_start in sorted(shot_scales.keys(), reverse=True):
            if sec >= scene_start:
                per_sec[sec]["shot_scale"] = shot_scales[scene_start]
                break

    profile.per_second = [dict(ts=sec, **data) for sec, data in sorted(per_sec.items())]

    # 9. Emotion peaks (sustained high arousal)
    if profile.per_second:
        arousals = [ps["face_arousal"] for ps in profile.per_second]
        if any(a > 0 for a in arousals):
            mean_a = sum(arousals) / len(arousals)
            std_a = (sum((a - mean_a) ** 2 for a in arousals) / len(arousals)) ** 0.5
            baseline_a = mean_a + 1.5 * std_a
            for ps in profile.per_second:
                if ps["face_arousal"] > baseline_a and ps["face_arousal"] > 0.6:
                    profile.emotion_peaks.append({
                        "timestamp": ps["ts"], "arousal": ps["face_arousal"],
                        "emotion": ps["face_emotion"],
                    })

    # 10. Aesthetic peaks (top 10%)
    if profile.per_second:
        scores = sorted([ps["aesthetic_score"] for ps in profile.per_second], reverse=True)
        if scores and scores[0] > 0.5:  # only if aesthetics actually ran
            top10 = scores[max(1, len(scores) // 10)]
            for ps in profile.per_second:
                if ps["aesthetic_score"] >= top10 and ps["aesthetic_score"] > 0.5:
                    profile.aesthetic_peaks.append({
                        "timestamp": ps["ts"], "score": ps["aesthetic_score"],
                    })

    profile.components_used = components
    return profile
