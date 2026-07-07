"""
Content acquisition: search and download stock footage (Pexels) and SFX (Freesound).

Mirrors music_adapter.py structure with footage_search/footage_download
and sfx_search/sfx_download pairs.

Usage:
    from kb.tools.content_adapter import footage, sfx
    clips = footage.search("city night", orientation="landscape")
    clip = footage.download(clips[0])
    sfx_list = sfx.search("whoosh", duration_max=2)
    sfx_file = sfx.download(sfx_list[0])
"""

from __future__ import annotations

import json
import os
import pathlib
import time
import typing as t
from hashlib import sha256

import requests
from kb.tools.music_adapter import write_license_sidecar

UA = "Mozilla/5.0 (agentic-ai-video-kb/1.0)"
_CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "kb" / "raw" / "assets" / ".search_cache"
_FOOTAGE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "kb" / "raw" / "assets" / "footage"
_SFX_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "kb" / "raw" / "assets" / "sfx"
_LUT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "kb" / "raw" / "assets" / "luts"

# ═══════════════════════════════════════════════════════════
#  Pexels Video API
# ═══════════════════════════════════════════════════════════

PEXELS_API_KEY_ENV = "PEXELS_API_KEY"
PEXELS_BASE = "https://api.pexels.com/videos"


def _pexels_headers() -> dict:
    api_key = os.environ.get(PEXELS_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"Pexels API key required. Set {PEXELS_API_KEY_ENV} env var. "
            "Get a free key at https://www.pexels.com/api/"
        )
    return {"Authorization": api_key}


def footage_search(
    query: str,
    *,
    orientation: str | None = None,
    size: str | None = None,
    duration_min: float | None = None,
    duration_max: float | None = None,
    resolution_min: tuple[int, int] | None = None,
    license_filter: list[str] | None = None,
    top_k: int = 10,
    per_page: int = 15,
) -> list[dict]:
    """Search Pexels video library. All Pexels videos are CC0 / Pexels license (commercial-safe)."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_key = sha256(
        json.dumps({"src": "pexels", "q": query, "o": orientation, "k": top_k}, sort_keys=True).encode()
    ).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 86400:
            with open(cache_path) as f:
                return json.load(f)

    params: dict[str, t.Any] = {"query": query, "per_page": min(per_page, 80)}
    if orientation:
        params["orientation"] = orientation
    if size:
        params["size"] = size

    headers = _pexels_headers()
    resp = requests.get(f"{PEXELS_BASE}/search", params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    videos = data.get("videos", [])
    results: list[dict] = []
    for v in videos:
        duration = v.get("duration", 0)
        if duration_min and duration < duration_min:
            continue
        if duration_max and duration > duration_max:
            continue

        # Pick best quality video file
        video_files = v.get("video_files", [])
        best_file = _pick_best_video_file(video_files, resolution_min)

        results.append({
            "id": f"pexels_{v['id']}",
            "source": "pexels",
            "title": v.get("url", "").split("/")[-2].replace("-", " ").title() if v.get("url") else "",
            "url": v.get("url", ""),
            "duration": duration,
            "width": v.get("width", 0),
            "height": v.get("height", 0),
            "download_url": best_file.get("link", "") if best_file else "",
            "thumbnail_url": v.get("image", ""),
            "tags": [],
            "license": "Pexels (CC0)",
            "attribution_required": False,
            "commercial_use": True,
            "avg_color": v.get("avg_color", ""),
            "score": 0.0,
        })

    _cache_results(cache_path, results)
    return results[:top_k]


def _pick_best_video_file(
    files: list[dict],
    resolution_min: tuple[int, int] | None = None,
) -> dict:
    best: dict | None = None
    for f in files:
        w = f.get("width", 0) or 0
        h = f.get("height", 0) or 0
        if resolution_min and (w < resolution_min[0] or h < resolution_min[1]):
            continue
        if best is None or (w > best.get("width", 0)):
            best = f
    return best or (files[0] if files else {})


def footage_download(
    track: dict,
    *,
    output_dir: str = "",
    prefer_resolution: tuple[int, int] = (1920, 1080),
    prefer_format: str = "mp4",
) -> dict:
    """Download a Pexels video clip. Writes .license.json sidecar."""
    out_dir = pathlib.Path(output_dir) if output_dir else _FOOTAGE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    download_url = track.get("download_url", "")
    if not download_url:
        raise ValueError(f"no download URL in track: {track.get('id')}")

    filename = f"pexels_{track['id'].split('_')[-1]}.{prefer_format}"
    out_path = out_dir / filename
    lic_path = out_dir / f"{pathlib.Path(filename).stem}.license.json"

    if out_path.exists():
        return _asset_result(track, out_path, lic_path, cached=True,
                             extra={"width": track.get("width", 0), "height": track.get("height", 0)})

    r = requests.get(download_url, headers={"User-Agent": UA}, timeout=120, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    write_license_sidecar(track, lic_path, download_url, out_path.stat().st_size, prefix="Video")
    return _asset_result(track, out_path, lic_path,
                         extra={"width": track.get("width", 0), "height": track.get("height", 0)})


# ═══════════════════════════════════════════════════════════
#  Freesound SFX API
# ═══════════════════════════════════════════════════════════

FREESOUND_API_KEY_ENV = "FREESOUND_API_KEY"
FREESOUND_BASE = "https://freesound.org/apiv2"


def _freesound_headers() -> dict:
    api_key = os.environ.get(FREESOUND_API_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"Freesound API key required. Set {FREESOUND_API_KEY_ENV} env var. "
            "Get a free key at https://freesound.org/docs/api/"
        )
    return {"Authorization": f"Token {api_key}"}


def sfx_search(
    query: str,
    *,
    duration_min: float | None = None,
    duration_max: float | None = None,
    license_filter: list[str] | None = None,
    top_k: int = 10,
) -> list[dict]:
    """Search Freesound for sound effects. Default license filter excludes NC (non-commercial)."""
    if license_filter is None:
        license_filter = ["Creative Commons 0", "Attribution", "Attribution Noncommercial"]

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = sha256(
        json.dumps({"src": "freesound", "q": query, "k": top_k}, sort_keys=True).encode()
    ).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 86400:
            with open(cache_path) as f:
                return json.load(f)

    headers = _freesound_headers()
    params: dict[str, t.Any] = {
        "query": query,
        "page_size": min(top_k * 2, 150),
        "fields": "id,name,description,duration,license,username,download,previews",
    }
    resp = requests.get(f"{FREESOUND_BASE}/search/text/", params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results: list[dict] = []
    for s in data.get("results", []):
        dur = s.get("duration", 0)
        if duration_min and dur < duration_min:
            continue
        if duration_max and dur > duration_max:
            continue

        lic = s.get("license", "")
        if license_filter and not any(f in lic for f in license_filter):
            continue

        commercial_use = "Noncommercial" not in lic
        preview_url = ""
        previews = s.get("previews", {})
        if isinstance(previews, dict):
            preview_url = previews.get("preview-lq-mp3", previews.get("preview-hq-mp3", ""))

        results.append({
            "id": f"freesound_{s['id']}",
            "source": "freesound",
            "title": s.get("name", ""),
            "description": s.get("description", ""),
            "artist": s.get("username", ""),
            "duration": dur,
            "preview_url": preview_url,
            "download_url": f"{FREESOUND_BASE}/sounds/{s['id']}/download/" if commercial_use else preview_url,
            "thumbnail_url": "",
            "tags": [],
            "license": lic,
            "attribution_required": "Attribution" in lic and "0" not in lic,
            "commercial_use": commercial_use,
            "score": 0.0,
        })

    _cache_results(cache_path, results)
    return results[:top_k]


def sfx_download(
    track: dict,
    *,
    output_dir: str = "",
    prefer_format: str = "wav",
) -> dict:
    """Download an SFX from Freesound. Writes .license.json sidecar."""
    out_dir = pathlib.Path(output_dir) if output_dir else _SFX_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    download_url = track.get("download_url") or track.get("preview_url")
    if not download_url:
        raise ValueError(f"no download URL in track: {track.get('id')}")

    ext = download_url.rsplit(".", 1)[-1].split("?")[0]
    if ext not in ("wav", "mp3", "ogg", "flac"):
        ext = prefer_format
    filename = f"freesound_{track['id'].split('_')[-1]}.{ext}"
    out_path = out_dir / filename
    lic_path = out_dir / f"{pathlib.Path(filename).stem}.license.json"

    if out_path.exists():
        return _asset_result(track, out_path, lic_path, cached=True)

    headers = _freesound_headers()
    r = requests.get(download_url, headers=headers, timeout=120, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    write_license_sidecar(track, lic_path, download_url, out_path.stat().st_size, prefix="SFX")
    return _asset_result(track, out_path, lic_path)


# ═══════════════════════════════════════════════════════════
#  IWLTBAP LUT pack
# ═══════════════════════════════════════════════════════════

_LUT_SOURCE_URL = "https://github.com/IWLTBAP/LUTs/archive/refs/heads/main.zip"
_LUT_DIR_NAME = "iwltbap"


def lut_list() -> list[dict]:
    """Return available LUTs with license info from the LUT pack directory."""
    lut_dir = _LUT_DIR / _LUT_DIR_NAME
    if not lut_dir.exists():
        return [{"error": "LUT pack not downloaded. Run lut_download_pack() first."}]

    luts: list[dict] = []
    for f in sorted(lut_dir.glob("*.{cube,png}")) if lut_dir.exists() else []:
        luts.append({
            "name": f.stem,
            "path": str(f.resolve()),
            "format": f.suffix,
            "size_bytes": f.stat().st_size,
        })
    return luts


def lut_apply(video: str, lut_name: str, output: str, *, intensity: float = 1.0) -> str:
    """Apply a LUT to a video file. Wraps ffmpeg filter chain."""
    from kb.tools.ffmpeg_adapter import _run, _check_ffmpeg, _ensure_parent
    _check_ffmpeg()
    _ensure_parent(output)

    lut_dir = _LUT_DIR / _LUT_DIR_NAME
    lut_path = lut_dir / f"{lut_name}.cube"
    if not lut_path.exists():
        # Search subdirectories
        for f in lut_dir.rglob(f"{lut_name}.cube"):
            lut_path = f
            break
        if not lut_path.exists():
            raise FileNotFoundError(f"LUT not found: {lut_name}")

    lut_path_resolved = str(lut_path.resolve())
    if intensity < 1.0:
        vf = f"lut3d=file='{lut_path_resolved}':interp=tetrahedral,split[a][b];[b]lut3d=file='{lut_path_resolved}':interp=tetrahedral[graded];[a][graded]blend=all_mode=average:c0_opacity={intensity}"
    else:
        vf = f"lut3d=file='{lut_path_resolved}':interp=tetrahedral"

    cmd = ["ffmpeg", "-i", video, "-vf", vf, "-c:a", "copy", output]
    _run(cmd, check=True)
    return output


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════


def _asset_result(
    track: dict, out_path: pathlib.Path, lic_path: pathlib.Path,
    *, cached: bool = False, extra: dict | None = None,
) -> dict:
    """Shared result builder for footage and SFX downloads."""
    attr_text = ""
    if track.get("attribution_required"):
        attr_text = (
            f'{track.get("title", "")} by {track.get("artist", "")}. '
            f'License: {track.get("license", "")}.'
        )
    result = {
        "path": str(out_path.resolve()),
        "license_path": str(lic_path.resolve()),
        "title": track.get("title", ""),
        "artist": track.get("artist", ""),
        "source": track.get("source", ""),
        "license": track.get("license", ""),
        "attribution_required": track.get("attribution_required", False),
        "commercial_use": track.get("commercial_use", True),
        "attribution_text": attr_text,
        "size_bytes": out_path.stat().st_size,
        "duration": track.get("duration", 0),
        "cached": cached,
    }
    if extra:
        result.update(extra)
    return result


def _cache_results(cache_path: pathlib.Path, results: list) -> None:
    with open(cache_path, "w") as f:
        json.dump(results, f, indent=2)


class _FootageModule:
    """Convenience module: footage.search(), footage.download()"""

    def search(self, query: str, **kwargs) -> list[dict]:
        return footage_search(query, **kwargs)

    def download(self, track: dict, **kwargs) -> dict:
        return footage_download(track, **kwargs)


class _SfxModule:
    """Convenience module: sfx.search(), sfx.download()"""

    def search(self, query: str, **kwargs) -> list[dict]:
        return sfx_search(query, **kwargs)

    def download(self, track: dict, **kwargs) -> dict:
        return sfx_download(track, **kwargs)


footage = _FootageModule()
sfx = _SfxModule()
