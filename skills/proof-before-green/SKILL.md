---
name: proof-before-green
description: Use whenever a regression gate, blocker test, suite result, dry run, or commit is about to be trusted or reported, and whenever a system is about to be called working, live, or proven, with the verdict proven on the final tree and the final live state.
version: 1.0.0
---

# Proof Before Green

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

## Prove the gate verdict three ways

- Run each new or repaired blocker alone, in the full suite in gate order and in a clean export with no live state directory present.

- Prove the fail direction in the clean environment by showing the test fails on the pre fix code and passes on the fixed code.

- Get the full failure list before judging a gate and treat a truncated or tail limited gate log as invalid for verdict purposes.

## Define the live path first

- Name the full path from real input to real effect before auditing any part of it, including who creates the state the later steps consume.

- List every handoff in that path where an intent, record or order can be silently discarded, skipped or left empty.

- Build the audit roster from the system registry or live configuration, never from a generic name list written from memory.

## Count outcomes at the final state

- Count submitted, filled, rejected and skipped rows in the ledger and at the broker for the audit window and report every count, including zero counts.

- Treat a step that only evaluated, staged or emitted an intent as unproven until a submission or its named discard appears in the final record.

- Verify claimed results by tracing at least one real item end to end from input through submission to fill or named rejection.

- Refuse a GREEN verdict for any acceptance row whose only evidence is a unit test, a fake broker run or a hand built state fixture.

## Prove the system creates its own state

- Check that the book, queue or store the dispatch step enforces is re derived from confirmed real events, not only written at submit time or tied out once at cutover.

- Compare the enforced store against the external truth and report unowned, overstated and missing entries by count before judging any downstream step.

- Read records at the consumer in the shape the consumer reads them and fail the audit on hollow records such as empty reasons, missing state records or a known flag set from a partial return.

## Isolate failures and prove single running

- Require proof that overlapping scheduled invocations cannot run the same pass at once, such as a live single instance lock plus a duplicate count of zero for the window.

- Check that one bad intent, symbol or record is rejected on its own and cannot abort the whole pass for every later item.

- Count duplicate submissions by their natural key for the window and name any group found rather than netting it away.

## Report with named opens

- Report GREEN only for rows proven on the final tree and the final live state, and name every unproven row as PARTIAL, BLOCKED or UNVERIFIED with its missing proof.

- Report every gate backed commit with the gate result on the final tree, whether the tree was stable, the exact files staged and any bypass used with its evidence.

- Have a checker who did not do the work re count the headline numbers from the broker and ledger before the verdict is delivered.

- State plainly when a claimed fix left no trace in the audit record, and carry that row as UNVERIFIED into the next audit instead of closing it.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Re run the gate on the final tree after the last change instead of extending a verdict from an earlier tree.

- Run the live proof during a real session window when fills actually occur instead of reconstructing the path afterwards from reports.

- Shrink the audit to the order path alone and prove it completely rather than covering more surface with fixture level evidence.

- Split a gate that mixes unrelated programs so a contaminated section does not void the verdicts of stable sections.
