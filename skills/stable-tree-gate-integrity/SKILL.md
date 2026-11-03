---
name: stable-tree-gate-integrity
description: Keep verification gates, commits, and dry-runs honest on a tree that background loops rewrite continuously: freeze before gating, stage only owned files, and never let a dry-run touch live state.
version: 1.0.0
---

# Stable-Tree Gate Integrity

## Why this skill exists

The default: Running a gate on a tree that is still being written.
The cost: A verdict computed over a moving tree belongs to no version at all, and a commit staged from it sweeps in work nobody reviewed.
The replacement: Freeze, stage only owned files by explicit path, and discard any verdict the tree invalidated by moving.

## Purpose
On this desk, background loops rewrite tracked files continuously and scheduled jobs commit on their own. A gate run over a moving tree, a bare commit, or a dry-run that writes live state each silently destroy work or produce verdicts nobody can trust.

## Workflow
1. Freeze before gating: before running a full regression gate whose verdict will justify a commit, confirm no fix program, worker, or edit pass is still writing the tree. If anything is mid-edit, wait or re-run — a gate over a concurrently-edited tree is contaminated and its verdict is void.
2. Commit only on a clean gate: one full gate pass on the final, stable tree after the last change. If a gate was contaminated, say so, discard the verdict, and re-run; never commit on a partial or tail-truncated gate log.
3. Never bare-commit from automation: any scheduled job or script that commits stages only the files it owns, by explicit path, and if it must bypass a hook it uses `--no-verify` only with the gate-pass evidence in hand and the reason recorded in the commit body. A bare `git commit` can trigger park/restore machinery that reverts unrelated unstaged work.
4. Dry-runs are read-only against live state: a dry-run, research pass, or verification sweep must never write live ledgers, staging queues, or gate queues. Route experimental stagings to a segregated research store that production release sweeps cannot see, and add a regression blocker that fails if a dry-run path touches a live store.
5. After any hook, restore, or park incident, diff the working tree against the preserved patch before continuing, and recover selectively — never assume the tree still holds the work you wrote.

## Output Contract
Every gate-backed commit names: the gate result on the final tree, whether the tree was stable during the run, the exact files staged, and any bypass used with its evidence. Any contaminated gate is reported as UNVERIFIED, never as pass or fail.

## Operating Rules
1. A worker's or hook's completion report is a claim, not proof: verify the tested artifact is the delivered artifact.
2. Test suites must not write fixtures into production-shaped paths (fake ledger rows at repo root pollute real attribution); isolate test state.
3. When the same contamination class recurs, the fix is incomplete until a gate-wired regression blocker would have caught it.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
