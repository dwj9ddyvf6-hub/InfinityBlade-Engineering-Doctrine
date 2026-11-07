---
name: gate-test-integrity
description: Use whenever a regression gate, blocker test, suite result, dry run, or commit is run, prepared, or about to be trusted, reported, or acted on, including when the tree moved during the run; skip for writing or debugging an ordinary test on its own merits.
version: 1.0.1
---

# Gate and Test Integrity

## Why this skill exists

The default: Trusting a gate because it printed green.
The cost: A gate that passed on a tree that moved during the run, or on tests that leaked state into each other, certifying code it never actually judged.
The replacement: Freeze the tree, make every blocker hermetic, and prove the verdict alone, in the full suite, and in a clean export.

## Freeze and stage only owned work

- Freeze the tree before running a gate whose verdict will justify a commit and confirm no fix program, worker or edit pass is still writing it.

- Discard a gate verdict from a concurrently edited tree and report it as UNVERIFIED rather than as a pass or a fail.

- Stage only the files the committing job or agent owns, listed by explicit path, and never run a bare commit from automation.

- Use a hook bypass only with gate pass evidence in hand and record the reason in the commit body.

- Diff the working tree against the preserved patch after any hook, restore or park incident before continuing work.

## Keep dry runs out of live state

- Route dry runs, research passes and verification sweeps to a segregated research store that production sweeps cannot see.

- Add a gate wired regression blocker that fails if a dry run path writes a live ledger, staging queue or gate queue.

- Isolate test fixtures in temporary state and never write fake rows into production shaped paths.

## Make every blocker hermetic

- Build every test input inside the test with fixtures, temporary directories and stubbed providers instead of reading live ledgers, caches or generated snapshots.

- Redirect import frozen paths and constants as well as runtime lookups, and check sibling paths for the same captured pattern.

- Record every monkeypatch, stub or module attribute replacement a test installs and restore it in teardown or a finally block, even on failure.

- Treat a failure that appears only in the full suite, or only when a file runs alone, as cross test contamination until the leaking patch or shared state is found.

## Prove the verdict three ways

- Run each new or repaired blocker alone, in the full suite in gate order and in a clean export with no live state directory present.

- Prove the fail direction in the clean environment by showing the test fails on the pre fix code and passes on the fixed code.

- Get the full failure list before judging a gate and treat a truncated or tail limited gate log as invalid for verdict purposes.

- Report every gate backed commit with the gate result on the final tree, whether the tree was stable, the exact files staged and any bypass used with its evidence.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with the host’s connector-setup procedure (historical locator: `/opt/muse/skills/custom-connector-setup/SKILL.md`, an external host dependency; see [portable host setup](../../docs/OPERATING-PATHS.md#establish-a-portable-host-contract)), or build a custom connector.

## Alternatives for better results

- Re run the gate on the final tree after the last change instead of extending a verdict from an earlier tree.

- Split a gate that mixes unrelated programs so a contaminated section does not void the verdicts of stable sections.

## Host portability

`muse.*` names above describe the originating host. Discover equivalent advertised search, read, image-view and execution capabilities on the current host; do not call tools that are absent. The historical connector-setup path is not bundled. Use [the portable host contract](../../docs/OPERATING-PATHS.md#establish-a-portable-host-contract), retain the same evidence and authorization boundaries, and name a missing capability rather than pretending the recipe ran. Installing a connector or service still requires the task’s authority.
