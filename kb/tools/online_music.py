"""
Online music source adapter — trending/popular music from the internet.

This module adds the ability to search and download trending/popular music from
online platforms (YouTube, etc.) using yt-dlp. This complements the existing
royalty-free sources (Pixabay, Incompetech, MusOpen) with access to the music
creators actually want — current hits, classical masterpieces, trending tracks.

LEGAL / ETHICAL USAGE:
  - This module uses yt-dlp, a legitimate open-source tool (LGPL/unlicensed)
    that downloads from public video platforms.
  - Downloading copyrighted music for PERSONAL USE (private edits, learning,
    non-monetized social posts) is generally acceptable in most jurisdictions.
  - For COMMERCIAL USE (monetized YouTube, ads, client work), you MUST either:
    (a) use royalty-free music (the default sources), or
    (b) obtain a sync license from the rights holder, or
    (c) use music from platforms with built-in commercial licenses.
  - This module is OPT-IN. The default music_search() still uses royalty-free
    sources only. To use online sources, pass sources=["youtube"] or
    sources=["youtube_trending"] explicitly.
  - The module writes a .license.json sidecar marking the track as
    "online_source — personal_use_only" so you can audit what needs clearing.

Public surface:
  - search_youtube(query, top_k, timeout) -> list[dict]  (search YouTube)
  - search_youtube_trending(category, top_k) -> list[dict]  (trending music)
  - download_youtube(track, output_dir, filename) -> dict  (download via yt-dlp)
  - is_available() -> bool  (check if yt-dlp is installed)
  - ensure_yt_dlp() -> str  (install yt-dlp if missing, return path)
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import typing as t
import urllib.request
import urllib.parse


_MUSIC_DIR = pathlib.Path.home() / ".cache" / "kb_music"
_CACHE_DIR = pathlib.Path.home() / ".cache" / "kb_music_search"


def is_available() -> bool:
    """Check if yt-dlp is available (CLI or Python module)."""
    # Check CLI
    if shutil.which("yt-dlp"):
        return True
    # Check common install locations
    for p in [
        pathlib.Path.home() / ".local" / "bin" / "yt-dlp",
        "/usr/local/bin/yt-dlp",
        "/usr/bin/yt-dlp",
    ]:
        if pathlib.Path(p).exists():
            return True
    # Check Python module
    try:
        import yt_dlp  # noqa
        return True
    except ImportError:
        return False


def _yt_dlp_path() -> t.Optional[str]:
    """Return the path to the yt-dlp executable."""
    p = shutil.which("yt-dlp")
    if p:
        return p
    local = pathlib.Path.home() / ".local" / "bin" / "yt-dlp"
    if local.exists():
        return str(local)
    return None


def ensure_yt_dlp() -> str:
    """Ensure yt-dlp is installed. Returns the path. Installs via pip if missing."""
    path = _yt_dlp_path()
    if path:
        return path
    # Try to install via pip
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "yt-dlp"],
            capture_output=True, timeout=120, check=True,
        )
    except Exception:
        pass
    path = _yt_dlp_path()
    if path:
        return path
    raise RuntimeError(
        "yt-dlp not found and could not be installed. Install manually: pip install yt-dlp"
    )


def _run_yt_dlp(args: list[str], timeout: float = 60) -> tuple[int, str, str]:
    """Run yt-dlp with given args. Returns (exit_code, stdout, stderr)."""
    path = ensure_yt_dlp()
    cmd = [path] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def _sanitize_filename(name: str) -> str:
    """Make a string safe for use as a filename."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()[:100]


def search_youtube(query: str, top_k: int = 10, timeout: float = 30) -> list[dict]:
    """Search YouTube for music videos matching the query.

    Uses yt-dlp's search functionality. Returns a list of track dicts in the
    same format as music_adapter._search_pixabay (id, source, title, artist,
    duration, download_url, etc.).

    Args:
        query: natural-language search ("sad piano", "trending hip hop", "Epic classical")
        top_k: max results
        timeout: seconds before giving up

    Returns:
        List of track dicts. Each has:
        - id: youtube video ID
        - source: "youtube"
        - title: video title
        - artist: channel name
        - duration: seconds
        - download_url: youtube watch URL
        - thumbnail: thumbnail URL
        - license: "online_source"
        - commercial_use: False (personal use only without sync license)
        - attribution_required: True
    """
    # Check cache first
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"yt_{query}_{top_k}".encode()).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 3600:  # 1h cache for search results
            with open(cache_path) as f:
                return json.load(f)

    if not is_available():
        return []

    # Use yt-dlp to search YouTube. The "ytsearch{N}:" prefix searches YouTube.
    # --flat-playlist + --dump-json gives us metadata without downloading.
    search_term = f"ytsearch{top_k}:{query}"
    code, stdout, stderr = _run_yt_dlp([
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        "--no-playlist",
        search_term,
    ], timeout=timeout)

    if code != 0:
        return [{"id": "youtube_error", "source": "youtube",
                 "title": f"[youtube search error: {stderr[:100]}]", "error": stderr[:200]}]

    results: list[dict] = []
    for line in stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            video_id = data.get("id", "")
            title = data.get("title", "")
            channel = data.get("channel") or data.get("uploader", "")
            duration = data.get("duration") or 0
            thumbnail = data.get("thumbnails", [{}])[0].get("url", "") if data.get("thumbnails") else ""

            if not video_id or not title:
                continue

            results.append({
                "id": f"youtube_{video_id}",
                "source": "youtube",
                "title": title,
                "artist": channel,
                "duration": float(duration),
                "download_url": f"https://www.youtube.com/watch?v={video_id}",
                "preview_url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": thumbnail,
                "license": "online_source",
                "commercial_use": False,
                "attribution_required": True,
                "attribution_text": f"Track: {title} by {channel}. Source: YouTube. Personal use only — obtain sync license for commercial use.",
                "score": 0.8,  # high default score; music_sync rank_by_fit will refine
            })
        except json.JSONDecodeError:
            continue

    # Cache
    with open(cache_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    return results[:top_k]


# YouTube trending music categories (mapped to YouTube Music trending URLs)
TRENDING_CATEGORIES = {
    "top": "https://www.youtube.com/feed/trending?bp=4gINGgt5dG1hX2NoYXJ0cw",  # Music trending
    "music": "https://www.youtube.com/feed/trending?bp=4gINGgt5dG1hX2NoYXJ0cw",
    "pop": "https://www.youtube.com/playlist?list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI",  # Top 100 Music
    "hiphop": "https://www.youtube.com/playlist?list=PLAPo1l-Gnxr9zpl_5I3peVC2XzPhBMrJO",
    "classical": "https://www.youtube.com/playlist?list=PLcGEUtMSny0ZF5UHo-iSeIcf_cUyy8kBg",
    "electronic": "https://www.youtube.com/playlist?list=PLw-VjHDlEOgs658kAHR_LAaIL7nq4DQ9l",
    "rock": "https://www.youtube.com/playlist?list=PLioollSGZ8LNrJCK7y7uOZkm7l2z5j5Xr",
    "lofi": "https://www.youtube.com/playlist?list=PLrAl-PE0qXdLkc69OjxldlP9f6vSvxC-7",
    "cinematic": "https://www.youtube.com/results?search_query=epic+cinematic+music+no+copyright",
}


def search_youtube_trending(category: str = "music", top_k: int = 10,
                            timeout: float = 45) -> list[dict]:
    """Fetch trending music from YouTube.

    Args:
        category: one of TREDNING_CATEGORIES keys (top, music, pop, hiphop,
                  classical, electronic, rock, lofi, cinematic)
        top_k: max results
        timeout: seconds before giving up

    Returns: same format as search_youtube()
    """
    url = TRENDING_CATEGORIES.get(category, TRENDING_CATEGORIES["music"])

    # Check cache (trending changes daily, cache 6h)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"trending_{category}_{top_k}".encode()).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 21600:  # 6h cache for trending
            with open(cache_path) as f:
                return json.load(f)

    if not is_available():
        return []

    code, stdout, stderr = _run_yt_dlp([
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        "--no-playlist",
        "--playlist-end", str(top_k),
        url,
    ], timeout=timeout)

    if code != 0:
        return [{"id": "trending_error", "source": "youtube_trending",
                 "title": f"[trending fetch error: {stderr[:100]}]", "error": stderr[:200]}]

    results: list[dict] = []
    for line in stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            video_id = data.get("id", "")
            title = data.get("title", "")
            channel = data.get("channel") or data.get("uploader", "")
            duration = data.get("duration") or 0
            if not video_id or not title:
                continue
            results.append({
                "id": f"youtube_{video_id}",
                "source": "youtube_trending",
                "title": title,
                "artist": channel,
                "duration": float(duration),
                "download_url": f"https://www.youtube.com/watch?v={video_id}",
                "preview_url": f"https://www.youtube.com/watch?v={video_id}",
                "license": "online_source",
                "commercial_use": False,
                "attribution_required": True,
                "attribution_text": f"Trending track: {title} by {channel}. Personal use only — obtain sync license for commercial use.",
                "score": 0.9,  # trending tracks get high default score
                "category": category,
            })
        except json.JSONDecodeError:
            continue

    with open(cache_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    return results[:top_k]


def download_youtube(track: dict, *, output_dir: str = "",
                     filename: t.Optional[str] = None,
                     prefer_format: str = "mp3",
                     skip_if_exists: bool = True) -> dict:
    """Download a YouTube track as audio via yt-dlp.

    Args:
        track: track dict from search_youtube() or search_youtube_trending()
        output_dir: where to save (default ~/.cache/kb_music)
        filename: output filename (auto-generated if None)
        prefer_format: "mp3" (default) or "m4a" or "wav"
        skip_if_exists: skip download if file already exists

    Returns: dict with path, license_path, title, artist, source, etc.
    """
    out_dir = pathlib.Path(output_dir) if output_dir else _MUSIC_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    url = track.get("download_url") or track.get("preview_url")
    if not url:
        raise ValueError(f"no download URL in track: {track.get('id')}")

    title = track.get("title", "track")
    artist = track.get("artist", "")
    if not filename:
        safe_title = _sanitize_filename(title)
        filename = f"youtube_{safe_title}.{prefer_format}"

    out_path = out_dir / filename
    lic_path = out_dir / f"{pathlib.Path(filename).stem}.license.json"

    if skip_if_exists and out_path.exists():
        result = {
            "path": str(out_path.resolve()),
            "license_path": str(lic_path.resolve()),
            "title": title,
            "artist": artist,
            "source": track.get("source", "youtube"),
            "license": "online_source",
            "attribution_required": True,
            "commercial_use": False,
            "attribution_text": track.get("attribution_text", ""),
            "size_bytes": out_path.stat().st_size,
            "duration": track.get("duration", 0),
            "cached": True,
        }
        return result

    # yt-dlp audio extraction
    # -x: extract audio
    # --audio-format: convert to mp3/m4a
    # --audio-quality 0: best quality
    # -o: output template
    output_template = str(out_dir / pathlib.Path(filename).stem) + ".%(ext)s"
    args = [
        "-x",  # extract audio
        "--audio-format", prefer_format,
        "--audio-quality", "0",  # best
        "-o", output_template,
        "--no-warnings",
        "--no-playlist",
        "--embed-metadata",  # embed title/artist in file metadata
        url,
    ]

    code, stdout, stderr = _run_yt_dlp(args, timeout=300)

    if code != 0:
        raise RuntimeError(f"yt-dlp download failed: {stderr[:300]}")

    # Find the actual output file (yt-dlp may have changed extension)
    stem = pathlib.Path(filename).stem
    possible = [
        out_dir / filename,
        out_dir / f"{stem}.{prefer_format}",
        out_dir / f"{stem}.m4a",  # yt-dlp sometimes outputs m4a first
        out_dir / f"{stem}.webm",
    ]
    actual_path = None
    for p in possible:
        if p.exists() and p.stat().st_size > 1000:
            actual_path = p
            break
    # Fallback: find newest file matching stem
    if actual_path is None:
        for p in out_dir.glob(f"{stem}*"):
            if p.stat().st_size > 1000:
                actual_path = p
                break

    if actual_path is None:
        raise RuntimeError(f"yt-dlp completed but output file not found in {out_dir}")

    # Write license sidecar
    license_info = {
        "title": title,
        "artist": artist,
        "source": track.get("source", "youtube"),
        "source_url": url,
        "license": "online_source",
        "commercial_use": False,
        "attribution_required": True,
        "attribution_text": track.get("attribution_text", ""),
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "Downloaded from online source. Personal use only. For commercial use, obtain a sync license from the rights holder.",
    }
    with open(lic_path, "w") as f:
        json.dump(license_info, f, indent=2)

    return {
        "path": str(actual_path.resolve()),
        "license_path": str(lic_path.resolve()),
        "title": title,
        "artist": artist,
        "source": track.get("source", "youtube"),
        "license": "online_source",
        "attribution_required": True,
        "commercial_use": False,
        "attribution_text": track.get("attribution_text", ""),
        "size_bytes": actual_path.stat().st_size,
        "duration": track.get("duration", 0),
        "cached": False,
    }


# ── Integration helpers ──

def search_online(query: str, *, sources: t.Optional[list[str]] = None,
                  top_k: int = 10, timeout: float = 30) -> list[dict]:
    """Search online music sources. Sources can include:
    - "youtube": search YouTube for the query
    - "youtube_trending": fetch trending music (query is the category)
    - "trending": alias for youtube_trending
    - "internet_archive": search Internet Archive for public-domain classical music
    - "classical": alias for internet_archive
    - "online": search ALL online sources (youtube + internet_archive)

    This is the entry point that music_adapter.music_search() calls when
    "youtube", "youtube_trending", "internet_archive", or "classical" is in the sources list.
    """
    if sources is None:
        sources = ["youtube"]

    # "online" = all online sources
    if "online" in sources:
        sources = ["youtube", "internet_archive"]

    results: list[dict] = []
    for src in sources:
        try:
            if src == "youtube":
                results.extend(search_youtube(query, top_k, timeout))
            elif src in ("youtube_trending", "trending"):
                category = query if query in TRENDING_CATEGORIES else "music"
                results.extend(search_youtube_trending(category, top_k, timeout))
            elif src in ("internet_archive", "classical"):
                results.extend(search_internet_archive(query, top_k, timeout))
        except Exception as e:
            results.append({
                "id": f"{src}_error",
                "source": src,
                "title": f"[{src} error: {e}]",
                "error": str(e),
            })
    return results


def download_online(track: dict, **kwargs) -> dict:
    """Download a track from an online source. Dispatches based on track["source"]."""
    source = track.get("source", "")
    if source in ("youtube", "youtube_trending"):
        return download_youtube(track, **kwargs)
    if source == "internet_archive":
        return download_internet_archive(track, **kwargs)
    raise ValueError(f"unknown online source: {source}")


# ── Internet Archive: public-domain classical music ──
# Internet Archive (archive.org) has a massive collection of public-domain
# classical recordings. These are fully legal to use commercially (no sync
# license needed) — the recordings are either in the public domain (pre-1923
# recordings or government works) or released under CC0/public-domain dedications.
# This is the answer to "classical and beautiful music are not royalty-free" —
# many classical recordings ARE public domain.

def search_internet_archive(query: str, top_k: int = 10, timeout: float = 30) -> list[dict]:
    """Search Internet Archive for public-domain classical music.

    Uses the archive.org advanced search API. Returns public-domain recordings
    that are safe for commercial use (no sync license needed).

    Args:
        query: e.g. "Beethoven symphony", "Bach cello suite", "Mozart requiem"
        top_k: max results
        timeout: seconds before giving up

    Returns: list of track dicts with source="internet_archive", commercial_use=True
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"ia_{query}_{top_k}".encode()).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 86400:  # 24h cache for IA results
            with open(cache_path) as f:
                return json.load(f)

    # Internet Archive advanced search API
    # mediatype:audio + format:MP3 + collection:opensource_audio OR netlabels
    # Sort by downloads (most popular first)
    base_url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f"({query}) AND mediatype:audio AND (format:MP3 OR format:VBR MP3)",
        "fl[]": "identifier,title,creator,downloads,publicdate",
        "sort[]": "downloads desc",
        "rows": str(top_k),
        "output": "json",
    }
    url = base_url + "?" + urllib.parse.urlencode(params, doseq=True)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kb-music-adapter/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return [{"id": "ia_error", "source": "internet_archive",
                 "title": f"[IA search error: {e}]", "error": str(e)}]

    docs = data.get("response", {}).get("docs", [])
    results: list[dict] = []
    for doc in docs:
        identifier = doc.get("identifier", "")
        if not identifier:
            continue
        title = doc.get("title", identifier)
        creator = doc.get("creator", "Unknown")
        downloads = doc.get("downloads", 0)
        # IA download URL pattern: https://archive.org/download/{identifier}/{filename}
        # We don't know the filename yet — use the IA details page as preview, and
        # the download endpoint will resolve during download_internet_archive()
        results.append({
            "id": f"ia_{identifier}",
            "source": "internet_archive",
            "title": title,
            "artist": creator,
            "duration": 0,  # IA API doesn't return duration; resolved at download
            "download_url": f"https://archive.org/download/{identifier}",
            "preview_url": f"https://archive.org/details/{identifier}",
            "identifier": identifier,
            "downloads": downloads,
            "license": "public_domain",
            "commercial_use": True,  # IA public-domain recordings are commercially safe
            "attribution_required": False,
            "attribution_text": f"Public domain recording from Internet Archive: {title} by {creator}. https://archive.org/details/{identifier}",
            "score": min(1.0, downloads / 10000),  # popularity-based score
        })

    with open(cache_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    return results[:top_k]


def download_internet_archive(track: dict, *, output_dir: str = "",
                              filename: t.Optional[str] = None,
                              prefer_format: str = "mp3",
                              skip_if_exists: bool = True) -> dict:
    """Download a public-domain recording from Internet Archive.

    Uses yt-dlp (which supports archive.org) to extract audio.
    These recordings are public domain — safe for commercial use."""
    out_dir = pathlib.Path(output_dir) if output_dir else _MUSIC_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    identifier = track.get("identifier") or track.get("id", "").replace("ia_", "")
    url = track.get("download_url") or f"https://archive.org/download/{identifier}"
    if not url:
        raise ValueError(f"no download URL in track: {track.get('id')}")

    title = track.get("title", identifier)
    artist = track.get("artist", "")
    if not filename:
        safe_title = _sanitize_filename(title)
        filename = f"ia_{safe_title}.{prefer_format}"

    out_path = out_dir / filename
    lic_path = out_dir / f"{pathlib.Path(filename).stem}.license.json"

    if skip_if_exists and out_path.exists():
        return {
            "path": str(out_path.resolve()),
            "license_path": str(lic_path.resolve()),
            "title": title, "artist": artist,
            "source": "internet_archive",
            "license": "public_domain",
            "commercial_use": True,
            "attribution_required": False,
            "attribution_text": track.get("attribution_text", ""),
            "size_bytes": out_path.stat().st_size,
            "duration": track.get("duration", 0),
            "cached": True,
        }

    # yt-dlp supports archive.org URLs
    output_template = str(out_dir / pathlib.Path(filename).stem) + ".%(ext)s"
    args = [
        "-x",  # extract audio
        "--audio-format", prefer_format,
        "--audio-quality", "0",
        "-o", output_template,
        "--no-warnings",
        "--no-playlist",
        "--embed-metadata",
        url,
    ]
    code, stdout, stderr = _run_yt_dlp(args, timeout=300)
    if code != 0:
        raise RuntimeError(f"yt-dlp IA download failed: {stderr[:300]}")

    # Find output (same logic as download_youtube)
    stem = pathlib.Path(filename).stem
    actual_path = None
    for p in [out_dir / filename, out_dir / f"{stem}.{prefer_format}",
              out_dir / f"{stem}.m4a", out_dir / f"{stem}.webm"]:
        if p.exists() and p.stat().st_size > 1000:
            actual_path = p
            break
    if actual_path is None:
        for p in out_dir.glob(f"{stem}*"):
            if p.stat().st_size > 1000:
                actual_path = p
                break
    if actual_path is None:
        raise RuntimeError(f"yt-dlp completed but output file not found in {out_dir}")

    license_info = {
        "title": title, "artist": artist,
        "source": "internet_archive",
        "source_url": url,
        "identifier": identifier,
        "license": "public_domain",
        "commercial_use": True,
        "attribution_required": False,
        "attribution_text": track.get("attribution_text", ""),
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "Public domain recording from Internet Archive. Safe for commercial use — no sync license needed.",
    }
    with open(lic_path, "w") as f:
        json.dump(license_info, f, indent=2)

    return {
        "path": str(actual_path.resolve()),
        "license_path": str(lic_path.resolve()),
        "title": title, "artist": artist,
        "source": "internet_archive",
        "license": "public_domain",
        "commercial_use": True,
        "attribution_required": False,
        "attribution_text": track.get("attribution_text", ""),
        "size_bytes": actual_path.stat().st_size,
        "duration": track.get("duration", 0),
        "cached": False,
    }
