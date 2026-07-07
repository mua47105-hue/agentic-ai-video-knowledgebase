---
title: ELLMPEG — Efficient LLM-Powered Video Editing via Natural Language Commands
type: source
tags: [paper, llm, ffmpeg, qwen]
created: 2026-07-08
updated: 2026-07-08
related: [local-llm-setup, ffmpeg-command-reference]
---

# ELLMPEG

## Citation
Zhang et al. "ELLMPEG: Efficient LLM-Powered Video Editing via Natural Language Commands." arXiv:2602.00028, 2026. https://arxiv.org/abs/2602.00028

## Key claims
- **Qwen2.5-Coder 7B achieves 88% FFmpeg command accuracy** in a single pass — the highest among open-weight models tested.
- The paper benchmarks 9 LLMs across 200 natural-language-to-FFmpeg tasks, categorized by complexity: simple (1 flag), moderate (2-3 flags), complex (filter chains, 4+ flags).
- Few-shot prompting improves accuracy by 12-18 percentage points across all models.
- Common failure modes: incorrect flag ordering (especially `-ss` vs `-i`), filter chain syntax errors, missing codec flags in output.
- Open-weight models (Qwen, DeepSeek, LLaMA) approach GPT-4o accuracy on simple tasks but degrade faster on complex filter chains.

## How this connects to the wiki
- **Local LLM Setup**: The `local-llm-setup.md` guide cites ELLMPEG's 88% accuracy figure for Qwen2.5-Coder. This source is the primary citation for that claim.
- **FFmpeg Command Reference**: ELLMPEG's 200-task benchmark taxonomy inspired the wiki's categorization of FFmpeg patterns by complexity.
- **Agent Prompt**: The copy-paste agent prompt uses ELLMPEG's findings to recommend Qwen2.5-Coder 7B for simple tasks and Claude/GPT-4o for complex multi-step editing.

## Contradictions with existing pages
- (none — current wiki citations of the 88% figure are consistent with the paper)

## Notes
- arXiv:2602.00028 was published in early 2026 and has not been peer-reviewed at the time of writing. The 88% figure is from the authors' benchmark, not an independent replication.
- The paper's benchmark includes only English-language prompts. Accuracy on non-English prompts is not reported.
- The 200-task benchmark is available on GitHub (linked in the paper). It can be used as a test suite for evaluating new LLMs for FFmpeg tasks.
