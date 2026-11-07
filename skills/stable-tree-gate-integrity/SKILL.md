---
name: stable-tree-gate-integrity
description: "Keep verification gates, commits, and dry-runs honest on a tree that background loops rewrite continuously: freeze before gating, stage only owned files, and never let a dry-run touch live state."
version: 1.0.2
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
3. Never bare-commit from automation: any scheduled job or script that commits stages only the files it owns, by explicit path, and any redundant workflow-hook bypass requires an explicitly authorized host procedure, equivalent gate-pass evidence on the exact candidate and a recorded reason. `--no-verify` is not authority to disable permission, secret, privacy or safety guards. A bare `git commit` can trigger park/restore machinery that reverts unrelated unstaged work.
4. Dry-runs are read-only against live state: a dry-run, research pass, or verification sweep must never write live ledgers, staging queues, or gate queues. Route experimental stagings to a segregated research store that production release sweeps cannot see, and add a regression blocker that fails if a dry-run path touches a live store.
5. After any hook, restore, or park incident, diff the working tree against the preserved patch before continuing, and recover selectively — never assume the tree still holds the work you wrote.

## Bind the gate to the complete input closure

A stable immutable snapshot is a valid way to freeze the tested tree while unrelated work continues elsewhere. Record the candidate tree, configuration, fixture identities and relevant external input versions. If an input in that closure changes, rerun affected proof; an unrelated worktree edit does not rewrite the immutable snapshot. Verify the delivered artifact is exactly that candidate before using its receipt.

A runner that discovers zero tests, omits an expected test module, skips a required case or hides a nonzero exit has not earned a pass. Record the discovered inventory and explicit skip reasons. Preserve the complete machine log; summarize it for the user without losing its evidence.

## Output Contract
Every gate-backed commit names: the gate result on the final tree, whether the tree was stable during the run, the exact files staged, and any bypass used with its evidence. Any contaminated gate is reported as UNVERIFIED, never as pass or fail.

## Operating Rules
1. A worker's or hook's completion report is a claim, not proof: verify the tested artifact is the delivered artifact.
2. Test suites must not write fixtures into production-shaped paths (fake ledger rows at repo root pollute real attribution); isolate test state.
3. When the same contamination class recurs, the fix is incomplete until a gate-wired regression blocker would have caught it.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.

## Host portability

`muse.*` names above describe the originating host. Discover equivalent advertised search, read, image-view and execution capabilities on the current host; do not call tools that are absent. The historical connector-setup path is not bundled. Use [the portable host contract](../../docs/OPERATING-PATHS.md#establish-a-portable-host-contract), retain the same evidence and authorization boundaries, and name a missing capability rather than pretending the recipe ran. Installing a connector or service still requires the task’s authority.
