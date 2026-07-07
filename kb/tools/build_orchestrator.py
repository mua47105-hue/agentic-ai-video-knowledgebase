"""
Build Orchestrator (Phase 5 — Project Montage's per-modality sub-agents).

Organizes BUILD-phase operations into modality-specific sub-agents that can
execute in parallel where independent:
  - cut_agent       — trim, silence-remove, J/L-cuts, merge
  - color_agent     — color_grade, LUT, scopes
  - audio_agent     — loudnorm, ducking, stem processing
  - subtitle_agent  — Whisper → SRT → burn (LAST per HR#12)
  - music_agent     — search, duck, align to sections
  - mogfx_agent     — motion graphics, callouts, overlays

Each sub-agent groups its steps from the EditPlan. Dependencies between
sub-agents are tracked (e.g., subtitle_agent must wait for cut_agent + color_agent).
Within a sub-agent, steps execute sequentially.

This is advisory for v1 — the recipe_runner still executes steps sequentially,
but this module provides the grouping + dependency graph that a future parallel
executor can use, and the manifest records which sub-agent each step belongs to.

Public surface:
  - orchest_build(edit_plan) -> dict
    Returns {"sub_agents": {name: {steps, depends_on, can_parallel}}, "execution_order": [...]}
"""
from __future__ import annotations

import typing as t


# Tool → sub-agent mapping
TOOL_TO_AGENT: dict[str, str] = {
    # cut_agent
    "edit.trim": "cut_agent", "edit.silence_remove": "cut_agent",
    "edit.j_cut": "cut_agent", "edit.l_cut": "cut_agent",
    "edit.merge": "cut_agent", "edit.concat": "cut_agent",
    "edit.detect_scenes": "cut_agent",
    # color_agent
    "edit.color_grade": "color_agent", "edit.ai_color_grade": "color_agent",
    "edit.lut_apply": "color_agent", "edit.scope_analyze": "color_agent",
    # audio_agent
    "edit.loudnorm": "audio_agent", "edit.loudnorm_limited": "audio_agent",
    "edit.add_audio": "audio_agent", "edit.audio_effects": "audio_agent",
    "edit.sidechaincompress": "audio_agent",
    # subtitle_agent
    "edit.text_subtitles": "subtitle_agent", "edit.text_animated": "subtitle_agent",
    "edit.transcribe": "subtitle_agent",  # transcription feeds subtitles
    # music_agent
    "music.search": "music_agent", "music.download": "music_agent",
    "music.describe": "music_agent", "music.rank_by_fit": "music_agent",
    # mogfx_agent
    "edit.layout_pip": "mogfx_agent", "edit.layout_grid": "mogfx_agent",
    "edit.text_animated": "mogfx_agent",
    # probe (read-only, no agent)
    "edit.info": "probe",
    "edit.render": "render",
    "edit.speed": "cut_agent",  # speed changes are part of cut/pacing
}

# Sub-agent execution order + dependencies
AGENT_ORDER: list[str] = [
    "probe",       # read-only, always first
    "cut_agent",   # trim/silence/merge — produces the base edit
    "color_agent", # grade on top of cut
    "audio_agent", # loudnorm/ducking on top of cut
    "music_agent", # music bed on top of audio
    "mogfx_agent", # overlays on top of color
    "subtitle_agent",  # ALWAYS last (HR#12)
    "render",      # final encode
]

AGENT_DEPENDENCIES: dict[str, list[str]] = {
    "probe": [],
    "cut_agent": ["probe"],
    "color_agent": ["cut_agent"],
    "audio_agent": ["cut_agent"],
    "music_agent": ["cut_agent", "audio_agent"],
    "mogfx_agent": ["color_agent"],
    "subtitle_agent": ["cut_agent", "color_agent", "mogfx_agent"],  # LAST before render
    "render": ["cut_agent", "color_agent", "audio_agent", "subtitle_agent"],
}


def orchest_build(edit_plan: dict) -> dict:
    """
    Group EditPlan steps into modality-specific sub-agents with dependency tracking.
    Returns the orchestration plan (advisory — recipe_runner still executes sequentially).
    """
    steps = edit_plan.get("steps", [])
    sub_agents: dict[str, dict] = {}
    for agent in AGENT_ORDER:
        sub_agents[agent] = {"steps": [], "depends_on": AGENT_DEPENDENCIES[agent], "can_parallel": False}

    # Assign each step to a sub-agent
    for i, step in enumerate(steps):
        tool = step.get("tool", "")
        agent = TOOL_TO_AGENT.get(tool, "cut_agent")  # default to cut_agent
        sub_agents[agent]["steps"].append({
            "step_index": i,
            "operation": step.get("operation", ""),
            "tool": tool,
            "params": step.get("params", {}),
            "output": step.get("output", ""),
            "reasoning": step.get("reasoning", ""),
        })

    # Determine which sub-agents can run in parallel
    # (same depth in dependency graph, no mutual dependency)
    for agent, deps in AGENT_DEPENDENCIES.items():
        if not deps or deps == ["probe"]:
            sub_agents[agent]["can_parallel"] = True
        # color_agent and audio_agent both depend only on cut_agent → can parallel
        if agent in ("color_agent", "audio_agent") and deps == ["cut_agent"]:
            sub_agents[agent]["can_parallel"] = True

    # Build execution order (topological)
    execution_order = _topological_sort(AGENT_DEPENDENCIES)

    # Remove empty sub-agents
    sub_agents_active = {
        name: data for name, data in sub_agents.items() if data["steps"]
    }

    return {
        "sub_agents": sub_agents_active,
        "execution_order": [a for a in execution_order if a in sub_agents_active],
        "parallel_groups": _parallel_groups(sub_agents_active, AGENT_DEPENDENCIES),
        "total_steps": sum(len(sa["steps"]) for sa in sub_agents_active.values()),
    }


def _topological_sort(deps: dict[str, list[str]]) -> list[str]:
    """Topological sort of sub-agents by dependency."""
    result: list[str] = []
    visited: set[str] = set()
    temp: set[str] = set()

    def visit(node: str):
        if node in visited:
            return
        if node in temp:
            return  # cycle (shouldn't happen)
        temp.add(node)
        for dep in deps.get(node, []):
            visit(dep)
        temp.discard(node)
        visited.add(node)
        result.append(node)

    for node in deps:
        visit(node)
    return result


def _parallel_groups(sub_agents: dict, deps: dict[str, list[str]]) -> list[list[str]]:
    """Group sub-agents that can execute in the same parallel batch."""
    groups: list[list[str]] = []
    remaining = set(sub_agents.keys())
    completed: set[str] = set()

    while remaining:
        batch = []
        for agent in remaining:
            agent_deps = deps.get(agent, [])
            if all(d in completed or d not in sub_agents for d in agent_deps):
                batch.append(agent)
        if not batch:
            # No progress — add remaining as single batch (shouldn't happen)
            batch = list(remaining)
        groups.append(batch)
        for a in batch:
            remaining.discard(a)
            completed.add(a)
    return groups
