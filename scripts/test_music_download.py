#!/usr/bin/env python3
"""
Test music_search + music_download end-to-end.
Searches Pixabay + Incompetech, downloads a track, verifies output.

Usage:
    python3 scripts/test_music_download.py          # full test (needs internet)
    python3 scripts/test_music_download.py --offline # test logic only
"""
import sys, os, pathlib, argparse, json, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kb.tools.music_adapter import music
from _test_utils import check, run_main

TMP = pathlib.Path(tempfile.mkdtemp(prefix="music_download_test_"))
ERRORS: list[str] = []


def test_search_internet(offline: bool = False):
    if offline:
        print("  SKIP: search: offline mode, skipping network tests")
        return
    results = music.music_search("sad piano", top_k=5, timeout_per_source=10.0)
    check("search: returns list", isinstance(results, list))
    check("search: has results", len(results) > 0, f"got {len(results)}")
    if results:
        r = results[0]
        check("search: result has id", bool(r.get("id")))
        check("search: result has source", bool(r.get("source")))
        check("search: result has title", bool(r.get("title")))
        check("search: result has download_url", bool(r.get("download_url")))
        check("search: result has score", isinstance(r.get("score"), (int, float)))
    results2 = music.music_search("upbeat corporate", top_k=3, timeout_per_source=10.0)
    check("search upbeat: has results", len(results2) > 0, f"got {len(results2)}")


def test_search_sources(offline: bool = False):
    from kb.tools.music_adapter import _search_pixabay, _search_incompetech, _search_musopen
    if offline:
        print("  SKIP: sources: offline mode, skipping network tests")
        return
    try:
        pixabay = _search_pixabay("piano", top_k=3, timeout=10.0)
        check("pixabay: returns list", isinstance(pixabay, list))
        check("pixabay: has results", len(pixabay) > 0, f"got {len(pixabay)}")
    except Exception as e:
        check("pixabay: no crash", False, str(e))
    try:
        incomp = _search_incompetech("piano", top_k=3, timeout=10.0)
        check("incompetech: returns list", isinstance(incomp, list))
        if incomp:
            print(f"  -> Incompetech top: {incomp[0]['title']}")
    except Exception as e:
        check("incompetech: no crash", False, str(e))
    try:
        musopen = _search_musopen("Beethoven", top_k=3, timeout=10.0)
        check("musopen: returns list", isinstance(musopen, list))
    except Exception as e:
        check("musopen: no crash", False, str(e))


def test_download(offline: bool = False):
    if offline:
        print("  SKIP: download: offline mode, skipping network tests")
        return
    results = music.music_search("piano ambient", top_k=1, timeout_per_source=10.0)
    if not results:
        print("  SKIP: download: no search results, skipping")
        return
    track = results[0]
    out_dir = str(TMP / "downloads")
    try:
        info = music.music_download(track, output_dir=out_dir, skip_if_exists=False)
        check("download: returns dict", isinstance(info, dict))
        check("download: has path", bool(info.get("path")))
        check("download: file exists", os.path.exists(info["path"]))
        check("download: file > 1KB", info.get("size_bytes", 0) > 1024)
        check("download: has license_path", bool(info.get("license_path")))
        check("download: license file exists", os.path.exists(info["license_path"]))
        check("download: has title", bool(info.get("title")))
        check("download: has artist", bool(info.get("artist")))
        check("download: has source", bool(info.get("source")))
        check("download: has license type", bool(info.get("license")))
        with open(info["license_path"]) as f:
            lic = json.load(f)
        check("license: has title", bool(lic.get("title")))
        check("license: has license", bool(lic.get("license")))
        check("license: has downloaded_at", bool(lic.get("downloaded_at")))
        check("license: has size_bytes", lic.get("size_bytes", 0) > 0)
        print(f"  -> Downloaded: {info['title']} ({info['size_bytes']} bytes)")
        info2 = music.music_download(track, output_dir=out_dir)
        check("download: cache hit", info2.get("cached") is True)
    except Exception as e:
        check("download: no crash", False, str(e))


def test_scoring():
    from kb.tools.music_adapter import _score_track
    track = {"title": "Sad Piano Dreams", "tags": ["piano", "sad", "cinematic"]}
    s1 = _score_track("sad piano", track)
    check("scoring: matches sad piano", s1 > 0.5, f"got {s1}")
    s2 = _score_track("upbeat funk", track)
    check("scoring: no match for funk", s2 == 0.0, f"got {s2}")


def test_cache():
    from kb.tools.music_adapter import _CACHE_DIR
    check("cache dir is pathlib.Path", isinstance(_CACHE_DIR, pathlib.Path))
    check("cache dir name has search_cache", "search_cache" in str(_CACHE_DIR))


def run_tests():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Skip network calls")
    args, _ = parser.parse_known_args()
    print("=" * 60)
    print("music_search + music_download — Tests")
    print("=" * 60)
    if args.offline:
        print("  OFFLINE MODE — network tests skipped")
    test_search_internet(offline=args.offline)
    test_search_sources(offline=args.offline)
    test_download(offline=args.offline)
    test_scoring()
    test_cache()


if __name__ == "__main__":
    run_main(run_tests)
