#!/usr/bin/env python3
"""
Lint the wiki for: orphan pages, broken internal links, missing frontmatter
fields, stale 'updated' dates, and content-type focus leaks (generative
models in active sections).

Writes findings to kb/wiki/backlog.md (overwrites). Run periodically.

Usage:
    python3 scripts/lint_wiki.py
    python3 scripts/lint_wiki.py --json   # machine-readable
"""
from __future__ import annotations

import json
import re
import sys
import pathlib

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from datetime import datetime, timedelta, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
WIKI = REPO / "kb" / "wiki"
TODAY = datetime.now(timezone.utc).date()
STALE_DAYS = 90

GEN_KEYWORDS = ["runway", "pika", "sora", "veo", "kling", "nano banana", "magicroll"]
ALL_WIKI_PAGES = list(WIKI.rglob("*.md"))
EXCLUDE = {"index.md", "log.md", "_template.md", "backlog.md"}
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _is_excluded(p: pathlib.Path) -> bool:
    return p.name in EXCLUDE


def find_orphans() -> list[dict]:
    all_pages: set[str] = set()
    for p in ALL_WIKI_PAGES:
        if _is_excluded(p):
            continue
        rel = p.relative_to(WIKI).with_suffix("").as_posix()
        all_pages.add(rel)

    inbound: dict[str, set[str]] = {p: set() for p in all_pages}

    for p in ALL_WIKI_PAGES:
        if _is_excluded(p):
            continue
        text = p.read_text()
        for m in LINK_RE.finditer(text):
            target = m.group(2)
            if target.startswith("http") or target.startswith("#") or target.startswith("mailto"):
                continue
            target_path = (p.parent / target).resolve()
            try:
                rel = target_path.relative_to(WIKI).with_suffix("").as_posix()
            except ValueError:
                continue
            if rel in inbound:
                src = p.relative_to(WIKI).with_suffix("").as_posix()
                if src not in {"index", "log"}:
                    inbound[rel].add(src)

    return [{"page": p, "inbound_count": len(inbound[p])}
            for p in sorted(all_pages) if len(inbound[p]) == 0]


def find_broken_links() -> list[dict]:
    broken: list[dict] = []
    for p in ALL_WIKI_PAGES:
        if _is_excluded(p):
            continue
        text = p.read_text()
        for m in LINK_RE.finditer(text):
            label, target = m.group(1), m.group(2)
            if target.startswith("http") or target.startswith("#") or target.startswith("mailto"):
                continue
            target_path = (p.parent / target).resolve()
            if not target_path.exists() and not target_path.with_suffix(".md").exists():
                broken.append({
                    "source": str(p.relative_to(WIKI)),
                    "label": label,
                    "target": target,
                })
    return broken


def find_missing_frontmatter() -> list[dict]:
    required = ["title", "type", "tags", "created", "updated"]
    issues: list[dict] = []
    for p in ALL_WIKI_PAGES:
        if _is_excluded(p):
            continue
        text = p.read_text()
        if not text.startswith("---"):
            issues.append({"page": str(p.relative_to(WIKI)), "missing": "all frontmatter"})
            continue
        end = text.find("---", 3)
        if end < 0:
            issues.append({"page": str(p.relative_to(WIKI)), "missing": "closing ---"})
            continue
        if yaml is None:
            continue
        try:
            fm = yaml.safe_load(text[3:end]) or {}
        except yaml.YAMLError as e:
            issues.append({"page": str(p.relative_to(WIKI)), "missing": f"YAML parse error: {e}"})
            continue
        for field in required:
            if field not in fm or fm[field] in (None, "", []):
                issues.append({"page": str(p.relative_to(WIKI)), "missing": field})
    return issues


def find_stale_pages() -> list[dict]:
    stale: list[dict] = []
    cutoff = TODAY - timedelta(days=STALE_DAYS)
    for p in ALL_WIKI_PAGES:
        if _is_excluded(p):
            continue
        text = p.read_text()
        if not text.startswith("---"):
            continue
        end = text.find("---", 3)
        if end < 0:
            continue
        if yaml is None:
            continue
        try:
            fm = yaml.safe_load(text[3:end]) or {}
        except yaml.YAMLError:
            continue
        updated = fm.get("updated")
        if not updated:
            continue
        try:
            upd_date = datetime.strptime(str(updated), "%Y-%m-%d").date()
            if upd_date < cutoff:
                stale.append({
                    "page": str(p.relative_to(WIKI)),
                    "updated": str(updated),
                    "days_old": (TODAY - upd_date).days,
                })
        except ValueError:
            pass
    return stale


def find_focus_leaks() -> list[dict]:
    leaks: list[dict] = []
    for p in ALL_WIKI_PAGES:
        if "archive" in str(p):
            continue
        if _is_excluded(p):
            continue
        text = p.read_text().lower()
        for kw in GEN_KEYWORDS:
            if kw in text:
                idx = text.find(kw)
                ctx = text[max(0, idx - 40):idx + 60]
                leaks.append({
                    "page": str(p.relative_to(WIKI)),
                    "keyword": kw,
                    "context": ctx,
                })
    return leaks


def run_all() -> dict:
    orphans = find_orphans()
    broken = find_broken_links()
    frontmatter = find_missing_frontmatter()
    stale = find_stale_pages()
    leaks = find_focus_leaks()
    return {
        "orphans": orphans,
        "broken_links": broken,
        "missing_frontmatter": frontmatter,
        "stale_pages": stale,
        "focus_leaks": leaks,
        "summary": {
            "orphans": len(orphans),
            "broken_links": len(broken),
            "missing_frontmatter": len(frontmatter),
            "stale_pages": len(stale),
            "focus_leaks": len(leaks),
        },
    }


def write_backlog(findings: dict) -> None:
    lines = [
        "---",
        "title: Wiki Backlog",
        "type: backlog",
        f"created: {TODAY.isoformat()}",
        f"updated: {TODAY.isoformat()}",
        "---",
        "",
        "# Wiki Backlog",
        "",
        f"> Auto-generated by `scripts/lint_wiki.py` on {TODAY.isoformat()}.",
        "> Run `python3 scripts/lint_wiki.py` to regenerate.",
        "",
        "## Summary",
        "",
        "| Issue | Count |",
        "|---|---|",
        f"| Orphan pages (no inbound links) | {findings['summary']['orphans']} |",
        f"| Broken internal links | {findings['summary']['broken_links']} |",
        f"| Missing frontmatter fields | {findings['summary']['missing_frontmatter']} |",
        f"| Stale pages (>{STALE_DAYS} days) | {findings['summary']['stale_pages']} |",
        f"| Focus leaks (generative in active) | {findings['summary']['focus_leaks']} |",
        "",
    ]

    if findings["orphans"]:
        lines += ["## Orphan pages", ""]
        for o in findings["orphans"]:
            lines.append(f"- `{o['page']}`")
        lines.append("")

    if findings["broken_links"]:
        lines += ["## Broken internal links", ""]
        for b in findings["broken_links"]:
            lines.append(f"- `{b['source']}` -> `{b['target']}` (label: {b['label']})")
        lines.append("")

    if findings["missing_frontmatter"]:
        lines += ["## Missing frontmatter fields", ""]
        for m in findings["missing_frontmatter"]:
            lines.append(f"- `{m['page']}`: missing `{m['missing']}`")
        lines.append("")

    if findings["stale_pages"]:
        lines += ["## Stale pages", ""]
        for s in findings["stale_pages"]:
            lines.append(f"- `{s['page']}` (last updated {s['updated']}, {s['days_old']} days ago)")
        lines.append("")

    if findings["focus_leaks"]:
        lines += ["## Focus leaks (generative content in active pages)", ""]
        for f in findings["focus_leaks"]:
            lines.append(f"- `{f['page']}`: keyword '{f['keyword']}' in context: ...{f['context']}...")
        lines.append("")

    backlog = WIKI / "backlog.md"
    backlog.write_text("\n".join(lines))
    print(f"Wrote {backlog}")


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Lint the wiki and persist findings to backlog.md")
    p.add_argument("--json", action="store_true", help="Print JSON instead of writing backlog.md")
    args = p.parse_args()

    findings = run_all()

    if args.json:
        print(json.dumps(findings, indent=2, default=str))
    else:
        write_backlog(findings)
        print(f"\nSummary: {findings['summary']}")


if __name__ == "__main__":
    main()
