"""Content type consistency tests.

Asserts every content_type value in every recipe YAML is a member of the
ContentType enum. This turns the "short_form vs social-short" mismatch
from a silent runtime remap into a hard CI failure at PR time.
"""
import pathlib
import pytest
import yaml

from kb.tools.content_types import ContentType

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RECIPES_DIR = REPO_ROOT / "recipes"


def _load_recipe(path: pathlib.Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


@pytest.mark.parametrize("recipe_path", sorted(RECIPES_DIR.glob("*.yaml")))
def test_recipe_content_type_is_valid(recipe_path):
    """Every recipe's content_type must be a valid ContentType value."""
    recipe = _load_recipe(recipe_path)
    ct = recipe.get("content_type", "")
    assert ct, f"{recipe_path.name} has no content_type field"
    assert ContentType.is_valid(ct), (
        f"{recipe_path.name} has content_type='{ct}' which is not in {ContentType.all_values()}. "
        f"Use ContentType enum values only."
    )


def test_content_type_enum_has_10_types():
    """The enum should have exactly 10 content types (plus short_form alias = 11 entries)."""
    values = ContentType.all_values()
    assert len(values) >= 10, f"Expected at least 10 content types, got {len(values)}: {values}"


def test_normalize_short_form():
    """short_form should normalize to social-short."""
    assert ContentType.normalize("short_form") == "social-short"


def test_normalize_unknown_falls_back_to_vlog():
    """Unknown content types should fall back to vlog (safe default)."""
    assert ContentType.normalize("nonexistent") == "vlog"


def test_normalize_valid_passthrough():
    """Valid content types should pass through unchanged."""
    assert ContentType.normalize("podcast") == "podcast"
    assert ContentType.normalize("cinematic") == "cinematic"
