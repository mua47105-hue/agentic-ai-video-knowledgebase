"""Tests for facts.yaml consistency + internal link checking.

Suggestion 1: Verify docs match facts.yaml (prevents drift).
Suggestion 2: Walk all .md files and verify internal links resolve.
"""
import pathlib
import re
import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FACTS_PATH = REPO_ROOT / "facts.yaml"


@pytest.fixture(scope="module")
def facts():
    with open(FACTS_PATH) as f:
        return yaml.safe_load(f)


class TestFactsConsistency:
    """Suggestion 1: docs should match facts.yaml."""

    def test_facts_yaml_exists(self):
        assert FACTS_PATH.exists(), "facts.yaml must exist at repo root"

    def test_module_count_matches_filesystem(self, facts):
        actual = len(list((REPO_ROOT / "kb" / "tools").glob("*.py")))
        expected = facts["modules"]["kb_tools_count"]
        assert actual == expected, (
            f"facts.yaml says {expected} kb/tools modules, filesystem has {actual}. "
            f"Update facts.yaml modules.kb_tools_count."
        )

    def test_recipe_count_matches_filesystem(self, facts):
        actual = len(list((REPO_ROOT / "recipes").glob("*.yaml")))
        expected = facts["modules"]["recipes_count"]
        assert actual == expected, (
            f"facts.yaml says {expected} recipes, filesystem has {actual}. "
            f"Update facts.yaml modules.recipes_count."
        )

    def test_setup_script_path_in_facts(self, facts):
        path = REPO_ROOT / facts["files"]["setup_script"]
        assert path.exists(), f"facts.yaml says setup script at {facts['files']['setup_script']}, not found"

    def test_no_scripts_dir_references_in_docs(self):
        """No doc should reference scripts/ — that directory was deleted."""
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "scripts/setup.sh\|scripts/agent-prompt\|scripts/lint_wiki\|scripts/doctor\|scripts/make_synthetic",
             "README.md", "SKILL.md", "AGENTS.md", "CLAUDE.md"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        assert result.stdout.strip() == "", (
            f"Found stale scripts/ references in docs:\n{result.stdout}"
        )


class TestInternalLinks:
    """Suggestion 2: walk all .md files and verify internal links resolve."""

    @pytest.mark.parametrize("md_path", [p for p in sorted(REPO_ROOT.rglob("*.md")) if "_template" not in p.name])
    def test_internal_links_resolve(self, md_path):
        """Every [text](path) link in every .md file should resolve to a real file."""
        content = md_path.read_text(errors="replace")
        # Find all markdown links: [text](path)
        link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
        for match in link_pattern.finditer(content):
            label, target = match.group(1), match.group(2)
            # Skip external links, anchors, and URLs
            if "deleted" in target:
                continue
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            # Strip anchor (#section)
            target_path = target.split("#")[0]
            if not target_path:
                continue  # pure anchor link
            # Resolve relative to the md file's directory
            resolved = (md_path.parent / target_path).resolve()
            if not resolved.exists():
                # Allow .md extension omission (wiki convention)
                if not target_path.endswith(".md") and not target_path.endswith(".png") and not target_path.endswith(".webp"):
                    md_candidate = resolved.with_suffix(".md")
                    if md_candidate.exists():
                        continue
                pytest.fail(
                    f"Broken link in {md_path.relative_to(REPO_ROOT)}: "
                    f"[{label}]({target}) — resolved to {resolved}, which does not exist"
                )
