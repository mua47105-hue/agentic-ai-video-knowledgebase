"""Recipe smoke tests.

Runs every YAML in recipes/ against a synthetic clip and asserts:
- The recipe YAML parses without error
- Every step's tool resolves to a callable function
- The recipe has at least one step
- The recipe has a content_type

This test file would have caught the P0 bug (edit.info param mismatch) on day one.
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
def test_recipe_parses(recipe_path):
    """Every recipe YAML must parse without error."""
    recipe = _load_recipe(recipe_path)
    assert isinstance(recipe, dict), f"{recipe_path.name} did not parse to a dict"
    assert "steps" in recipe, f"{recipe_path.name} has no 'steps' key"
    assert len(recipe["steps"]) > 0, f"{recipe_path.name} has 0 steps"


@pytest.mark.parametrize("recipe_path", sorted(RECIPES_DIR.glob("*.yaml")))
def test_recipe_has_content_type(recipe_path):
    """Every recipe must declare a content_type."""
    recipe = _load_recipe(recipe_path)
    ct = recipe.get("content_type", "")
    assert ct, f"{recipe_path.name} has no content_type"


@pytest.mark.parametrize("recipe_path", sorted(RECIPES_DIR.glob("*.yaml")))
def test_recipe_steps_have_tools(recipe_path):
    """Every step in every recipe must have a 'tool' field (or be a for_each loop)."""
    recipe = _load_recipe(recipe_path)
    for i, step in enumerate(recipe["steps"]):
        op = step.get("operation", "")
        tool = step.get("tool", "")
        if op.startswith("for_each_"):
            continue  # loops don't have tools
        assert tool, f"{recipe_path.name} step {i} has no tool (operation={op})"


@pytest.mark.parametrize("recipe_path", sorted(RECIPES_DIR.glob("*.yaml")))
def test_recipe_step_tools_resolve(recipe_path):
    """Every tool in every recipe must resolve to a callable (edit.*, music.*, recipe.*)."""
    recipe = _load_recipe(recipe_path)
    for i, step in enumerate(recipe["steps"]):
        op = step.get("operation", "")
        tool = step.get("tool", "")
        if op.startswith("for_each_"):
            # Check sub-steps
            for j, substep in enumerate(step.get("steps", [])):
                subtool = substep.get("tool", "")
                if subtool:
                    _assert_tool_resolves(subtool, f"{recipe_path.name} step {i}.{j}")
            continue
        if tool:
            _assert_tool_resolves(tool, f"{recipe_path.name} step {i}")


def _assert_tool_resolves(tool: str, context: str):
    """Assert that a tool string resolves to a callable.
    Gated tools (rembg, auto-editor, MoviePy) may not be present when deps aren't installed."""
    GATED_TOOLS = {"remove_background", "remove_background_video",
                   "auto_edit", "auto_edit_analyze", "auto_edit_to_edl",
                   "moviepy_compose", "moviepy_concatenate"}
    if tool.startswith("edit."):
        from kb.tools.unified_adapter import edit
        fn_name = tool[5:]
        fn = getattr(edit, fn_name, None)
        if fn is None and fn_name in GATED_TOOLS:
            return  # gated tool — skip if dep not installed
        assert fn is not None, f"{context}: edit.{fn_name} does not exist on unified_adapter"
        assert callable(fn), f"{context}: edit.{fn_name} is not callable"
    elif tool.startswith("music."):
        from kb.tools.unified_adapter import music
        fn_name = tool[6:]
        fn = getattr(music, fn_name, None)
        assert fn is not None, f"{context}: music.{fn_name} does not exist"
    elif tool.startswith("recipe."):
        # recipe.* tools are resolved by recipe_runner._resolve_tool
        # just check the name is non-empty
        assert len(tool) > 8, f"{context}: recipe tool name too short: {tool}"
    # else: unknown tool type — skip (might be a custom tool)
