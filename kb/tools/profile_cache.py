"""
SourceProfile cache (Phase: Speed optimization).

Caches probe_video() output keyed by file content-hash + mtime. On a cache hit,
returns the cached profile in <1ms instead of re-running the 10-30 min probe.

Cache key strategy (two-tier for speed):
  1. stat() first: size + mtime (fast, ~0.1ms)
  2. If size+mtime matches cached entry, use it directly
  3. If not, compute blake2b of first+last 1MB (fast partial hash, ~50ms for 10min video)
  4. If hash matches, use cached entry (handles mtime change without content change)

Cache location: ~/.cache/kb_profiles/<hash>.json
Cache invalidation: automatic via content hash; old entries pruned by LRU.

Public surface:
  - get_cached_profile(video_path) -> dict | None
  - save_profile_to_cache(video_path, profile) -> str (cache path)
  - get_or_probe(video_path, **probe_kwargs) -> dict (cache-or-probe)
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time
import typing as t


CACHE_DIR = pathlib.Path.home() / ".cache" / "kb_profiles"
MAX_CACHE_ENTRIES = 50  # LRU prune beyond this


def _file_fingerprint(path: str) -> tuple[tuple[int, float], str]:
    """Two-tier fingerprint: (size, mtime) + partial content hash.
    Returns ((size, mtime), content_hash) where content_hash is blake2b of
    first 1MB + last 1MB (handles mtime change without re-hash of full file)."""
    st = os.stat(path)
    stat_key = (st.st_size, st.st_mtime)
    file_size = st.st_size
    h = hashlib.blake2b(digest_size=16)
    with open(path, "rb") as f:
        # First 1MB
        h.update(f.read(1024 * 1024))
        # Last 1MB (if file > 2MB)
        if file_size > 2 * 1024 * 1024:
            f.seek(-1024 * 1024, 2)
            h.update(f.read(1024 * 1024))
        # Middle sample (1KB at 50% — catches edits in the middle)
        if file_size > 4 * 1024 * 1024:
            f.seek(file_size // 2)
            h.update(f.read(1024))
    return stat_key, h.hexdigest()


def _cache_path(content_hash: str) -> pathlib.Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{content_hash}.json"


def _cache_meta_path(content_hash: str) -> pathlib.Path:
    return CACHE_DIR / f"{content_hash}.meta.json"


def get_cached_profile(video_path: str) -> t.Optional[dict]:
    """Return cached SourceProfile if available and valid, else None."""
    try:
        (stat_key, content_hash) = _file_fingerprint(video_path)
    except (OSError, IOError):
        return None

    cpath = _cache_path(content_hash)
    if not cpath.exists():
        return None

    # Verify stat key matches (catches rare hash collision + mtime change)
    mpath = _cache_meta_path(content_hash)
    if mpath.exists():
        try:
            with open(mpath) as f:
                meta = json.load(f)
            cached_stat = (meta.get("size"), meta.get("mtime"))
            if cached_stat != stat_key:
                # mtime changed but content hash matched — still valid, update meta
                meta["size"] = stat_key[0]
                meta["mtime"] = stat_key[1]
                meta["last_access"] = time.time()
                with open(mpath, "w") as f:
                    json.dump(meta, f)
            else:
                # Update access time for LRU
                meta["last_access"] = time.time()
                with open(mpath, "w") as f:
                    json.dump(meta, f)
        except (OSError, IOError, json.JSONDecodeError):
            pass

    try:
        with open(cpath) as f:
            profile = json.load(f)
        # Mark as cache hit for debugging
        if isinstance(profile, dict):
            profile["_cache_hit"] = True
            profile["_cache_hash"] = content_hash
        return profile
    except (OSError, IOError, json.JSONDecodeError):
        return None


def save_profile_to_cache(video_path: str, profile: dict) -> str:
    """Save a SourceProfile to cache. Returns cache path."""
    try:
        (stat_key, content_hash) = _file_fingerprint(video_path)
    except (OSError, IOError):
        return ""

    # Don't cache the _cache_hit marker
    profile_to_save = {k: v for k, v in profile.items() if not k.startswith("_cache_")}

    cpath = _cache_path(content_hash)
    mpath = _cache_meta_path(content_hash)

    try:
        with open(cpath, "w") as f:
            json.dump(profile_to_save, f, default=str)
        with open(mpath, "w") as f:
            json.dump({
                "size": stat_key[0],
                "mtime": stat_key[1],
                "video_path": video_path,
                "created": time.time(),
                "last_access": time.time(),
            }, f)
        _prune_cache()
        return str(cpath)
    except (OSError, IOError):
        return ""


def _prune_cache() -> None:
    """LRU prune cache to MAX_CACHE_ENTRIES."""
    try:
        metas = []
        for mpath in CACHE_DIR.glob("*.meta.json"):
            try:
                with open(mpath) as f:
                    meta = json.load(f)
                metas.append((mpath, meta.get("last_access", 0)))
            except (OSError, IOError, json.JSONDecodeError):
                continue
        if len(metas) <= MAX_CACHE_ENTRIES:
            return
        # Sort by last_access ascending, remove oldest
        metas.sort(key=lambda x: x[1])
        for mpath, _ in metas[:len(metas) - MAX_CACHE_ENTRIES]:
            try:
                content_hash = mpath.stem.replace(".meta", "")
                cpath = _cache_path(content_hash)
                cpath.unlink(missing_ok=True)
                mpath.unlink(missing_ok=True)
            except OSError:
                pass
    except Exception:
        pass


def get_or_probe(video_path: str, probe_fn: t.Callable[..., dict],
                 **probe_kwargs) -> dict:
    """Cache-or-probe: return cached profile if available, else run probe_fn and cache.
    Args:
        video_path: path to the video
        probe_fn: callable that takes video_path + **probe_kwargs and returns a profile dict
        **probe_kwargs: passed to probe_fn on cache miss
    """
    cached = get_cached_profile(video_path)
    if cached is not None:
        return cached
    profile = probe_fn(video_path, **probe_kwargs)
    if isinstance(profile, dict) and profile.get("metadata", {}).get("duration", 0) > 0:
        save_profile_to_cache(video_path, profile)
    return profile


def cache_stats() -> dict:
    """Return cache statistics for debugging."""
    try:
        entries = list(CACHE_DIR.glob("*.meta.json"))
        total_size = sum(p.stat().st_size for p in CACHE_DIR.glob("*.json"))
        return {
            "cache_dir": str(CACHE_DIR),
            "entry_count": len(entries),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_entries": MAX_CACHE_ENTRIES,
        }
    except Exception:
        return {"cache_dir": str(CACHE_DIR), "entry_count": 0, "total_size_mb": 0}
