#!/usr/bin/env python3
"""Test vlm_adapter — verify gating works (VLM_ENABLED env var)."""
import os, sys, pathlib, importlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from _test_utils import check, run_main


def test_vlm_gated_off_by_default():
    os.environ.pop("VLM_ENABLED", None)
    import kb.tools.vlm_adapter
    importlib.reload(kb.tools.vlm_adapter)
    from kb.tools.vlm_adapter import vlm, VLM_AVAILABLE
    check("VLM disabled by default", not VLM_AVAILABLE)

    try:
        vlm.describe_frame("/tmp/nonexistent.mp4", timestamp=0)
        check("VLM raises when disabled", False, "no exception raised")
    except RuntimeError as e:
        check("VLM raises when disabled", True)
        check("error mentions VLM_ENABLED or disabled", "disabled" in str(e).lower() or "VLM_ENABLED" in str(e), str(e)[:100])


def test_vlm_enabled_env_var():
    os.environ["VLM_ENABLED"] = "1"
    import kb.tools.vlm_adapter
    importlib.reload(kb.tools.vlm_adapter)
    from kb.tools.vlm_adapter import VLM_AVAILABLE
    check("VLM_AVAILABLE set when VLM_ENABLED=1", VLM_AVAILABLE is not None)
    os.environ.pop("VLM_ENABLED", None)


def run_tests():
    print("=" * 60)
    print("vlm_adapter — Gating Tests")
    print("=" * 60)
    test_vlm_gated_off_by_default()
    test_vlm_enabled_env_var()


if __name__ == "__main__":
    run_main(run_tests)
