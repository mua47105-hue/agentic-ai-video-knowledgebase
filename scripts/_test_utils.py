"""Shared test utilities for scripts/. Provides check(), skip(), and run_main()."""
from __future__ import annotations

import sys

_PASS = 0
_FAIL = 0
_SKIP = 0
_FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  PASS: {label}")
    else:
        _FAIL += 1
        msg = f"  FAIL: {label}" + (f" — {detail}" if detail else "")
        print(msg)
        _FAILURES.append(msg)


def skip(label: str) -> None:
    global _SKIP
    _SKIP += 1
    print(f"  SKIP: {label}")


def summary() -> int:
    total = _PASS + _FAIL + _SKIP
    print(f"\n{_PASS}/{total} passed, {_FAIL}/{total} failed, {_SKIP}/{total} skipped")
    if _FAILURES:
        for m in _FAILURES:
            print(f"  {m}")
    return 1 if _FAIL else 0


def reset() -> None:
    global _PASS, _FAIL, _SKIP, _FAILURES
    _PASS = 0
    _FAIL = 0
    _SKIP = 0
    _FAILURES = []


def run_main(test_fn):
    try:
        test_fn()
    except Exception as e:
        print(f"  ERROR: unhandled exception — {e}", file=sys.stderr)
        sys.exit(2)
    sys.exit(summary())
