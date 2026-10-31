# Changelog

## 2.5.0 (2026-10-31)

- Mandatory full read: the README and this skill now open with an explicit instruction to any AI agent or language model to read the entire repository in full before applying any part of it, to state its coverage explicitly, and to stop rather than proceed on partial coverage. The doctrine is a single system whose parts qualify and correct each other; the note exists because a fragment applied confidently is the failure the doctrine most reliably produces in new readers.

## 2.4.0 (2026-10-31)

- New reference: agent enhancement. Ten disciplines distilled from an inspected sweep of public memory, skill-framework and proactivity work, each adopted only where it adds a mechanism the doctrine lacked: priced proactive lanes (benefit-minus-cost threshold, cheap gate, feedback scoring), a confidence-scored procedural memory ("instincts"), false-green audits of gate tests, memory profile and graph discipline with honest recall tiers and a governed erasure standard, pressure-testing for skills, an adoption and eval gate for the skill library, mechanised completion-claim checks, authority hygiene across compaction and delegation, and a bounded hidden-rubric pass for ungated prose.
- The same reference carries a recorded backlog of deferred items, each with its revisit trigger, and notes where the new material extends existing law instead of duplicating it.

## 2.3.0 (2026-10-26)

- Addressed to the agent: an opening that makes the case for following the skill (trust, speed, reach), and a one-line *why* on every section. Agents follow rules they understand better than rules they are given.

## 2.2.0 (2026-10-26)

Aimed at the main failure: agents skipping most of the skill.

- **Non-skippable minimum:** every task shows a `SCOPE:` line at the start and a `STATUS:` line at the end.
- **Tripwires:** rules that fire on what the agent is about to say or do ("done", "impossible", repeating an attempt, adding a workaround, acting on embedded instructions).
- **Enforcement:** `hooks/require-status.sh`, a Claude Code Stop hook that blocks finishing without a STATUS line.
- README prompt and drift check carry the two lines and the tripwires.

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
