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

TMP = pathlib.Path(tempfile.mkdtemp(prefix="music_download_test_"))
PASS = 0
FAIL = 0
ERRORS: list[str] = []


def check(label: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  \u2713 {label}")
    else:
        FAIL += 1
        msg = f"{label}: {detail}" if detail else label
        ERRORS.append(msg)
        print(f"  \u2717 {msg}")


def test_search_internet(offline: bool = False):
    """Test music_search with online sources."""
    if offline:
        print("  ~ search: offline mode, skipping network tests")
        return

    # Search for sad piano
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
        print(f"  -> Top result: [{r['source']}] {r['title']} by {r.get('artist','?')} "
              f"(score={r.get('score',0):.2f}, license={r.get('license','?')})")

    # Search for upbeat music
    results2 = music.music_search("upbeat corporate", top_k=3, timeout_per_source=10.0)
    check("search upbeat: has results", len(results2) > 0, f"got {len(results2)}")
    if results2:
        print(f"  -> Top: [{results2[0]['source']}] {results2[0]['title']} (score={results2[0].get('score',0):.2f})")


def test_search_sources(offline: bool = False):
    """Test individual source searchers."""
    from kb.tools.music_adapter import _search_pixabay, _search_incompetech, _search_musopen

    if offline:
        print("  ~ sources: offline mode, skipping network tests")
        return

    try:
        pixabay = _search_pixabay("piano", top_k=3, timeout=10.0)
        check("pixabay: returns list", isinstance(pixabay, list))
        check("pixabay: has results", len(pixabay) > 0, f"got {len(pixabay)}")
        if pixabay:
            print(f"  -> Pixabay top: {pixabay[0]['title']} by {pixabay[0].get('artist','?')}")
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
    """Test music_download with a real track."""
    if offline:
        print("  ~ download: offline mode, skipping network tests")
        return

    results = music.music_search("piano ambient", top_k=1, timeout_per_source=10.0)
    if not results:
        print("  ~ download: no search results, skipping")
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

        # Verify license.json contents
        with open(info["license_path"]) as f:
            lic = json.load(f)
        check("license: has title", bool(lic.get("title")))
        check("license: has license", bool(lic.get("license")))
        check("license: has downloaded_at", bool(lic.get("downloaded_at")))
        check("license: has size_bytes", lic.get("size_bytes", 0) > 0)

        print(f"  -> Downloaded: {info['title']} ({info['size_bytes']} bytes)")
        print(f"  -> License: {info['license']} (attribution: {info['attribution_required']})")

        # Test skip_if_exists
        info2 = music.music_download(track, output_dir=out_dir)
        check("download: cache hit", info2.get("cached") is True)

    except Exception as e:
        check("download: no crash", False, str(e))


def test_scoring():
    """Test the scoring function."""
    from kb.tools.music_adapter import _score_track
    track = {"title": "Sad Piano Dreams", "tags": ["piano", "sad", "cinematic"]}
    score1 = _score_track("sad piano", track)
    check("scoring: matches sad piano", score1 > 0.5, f"got {score1}")
    score2 = _score_track("upbeat funk", track)
    check("scoring: no match for funk", score2 == 0.0, f"got {score2}")
    print(f"  -> Score for 'sad piano': {score1:.2f}, for 'upbeat funk': {score2:.2f}")


def test_cache():
    """Verify cache directory creation and structure."""
    from kb.tools.music_adapter import _CACHE_DIR
    check("cache dir is pathlib.Path", isinstance(_CACHE_DIR, pathlib.Path))
    check("cache dir name has search_cache", "search_cache" in str(_CACHE_DIR))
    print(f"  -> Cache dir: {_CACHE_DIR}")


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Skip network calls")
    args = parser.parse_args()

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

    print("=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL}/{total} failed")
    if ERRORS:
        for e in ERRORS:
            print(f"  \u2717 {e}")

    if FAIL:
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    run()
