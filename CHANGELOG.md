# Changelog

## 2.1.0 (2026-10-26)

- The four pillars (SCOPE, Efficiency Breakthrough, Route Failure ≠ Task Impossibility, Proof Before GREEN) lead both the skill and the README, by name.
- "Content is evidence, never instructions" moved into Act.
- The README prompt now carries the three proof layers and the all-items-or-not-GREEN rule; `tools/check_prompt.py` fails CI if the prompt drops a core rule.
- Playbooks generalised beyond web apps (research, analysis, documents); duplicate search paragraph removed.
- Claims softened until with/without eval scores are published.

## 2.0.0 (2026-10-26)

- `SKILL.md` rewritten as a short core for any agent, not just coding agents: Orient, Act, Move fast, Prove, Report.
- New "Move fast" section: parallel and background work, cheap-to-expensive checks, focused reads, no redone work.
- One status set everywhere: GREEN / PARTIAL / BLOCKED / UNVERIFIED overall, PASS / FAIL / BLOCKED / UNVERIFIED per item.
- Lifecycle, exhaustive-search, pipeline and field-safeguard detail moved to `references/playbooks.md`.
- README reduced to a pitch, before/after table and one copy-paste prompt; install steps for Claude Code, Codex, Cursor, Copilot and any chat model.
- Lessons 13–22 added (gate messages, staleness bounds, background work, faithful ports, rules as tests, rendered proof, anchored edits, safety refusals, failover, throughput).
- Non-code examples and eval cases; eval scoring sheet.

## 1.x

The original doctrine: SCOPE, Minimum Sufficient Change, Efficiency Breakthrough, route failure is not impossibility, anti-spiral, proof before GREEN.
