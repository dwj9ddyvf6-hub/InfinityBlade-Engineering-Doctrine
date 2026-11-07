---
name: live-execution-proof
description: Use whenever a trading or automation system is about to be called working, live, or proven, even when its component tests all pass; skip for design review of a system that has never run.
version: 1.0.2
---

# Live Execution Proof

## Why this skill exists

The default: Calling a system working because its components pass.
The cost: A pipeline green in every unit test that never once moved a real item from input to effect on its live path.
The replacement: Define the live path, trace one real item end to end, and count outcomes at the final state, including the zero counts. The examples here speak of a broker and a ledger; read broker as the external system of record in your domain, and ledger as your own.

## Define the live path first

- Name the full path from real input to real effect before auditing any part of it, including who creates the state the later steps consume.

- List every handoff in that path where an intent, record or order can be silently discarded, skipped or left empty.

- Build the audit roster from the system registry or live configuration, never from a generic name list written from memory.

## Count outcomes at the final state

- Count submitted, filled, rejected and skipped rows in the ledger and at the broker for the audit window and report every count, including zero counts.

- Treat a step that only evaluated, staged or emitted an intent as unproven until a submission or its named discard appears in the final record.

- Verify claimed results by tracing at least one real item end to end from input through submission to fill or named rejection.

- Refuse a GREEN verdict for a live-boundary acceptance row whose only evidence is a unit test, a fake broker run or a hand built state fixture. Those checks can close their own local contracts; retain their results without promoting them into external proof. Never create an unauthorized order or message to obtain evidence.

## Prove the system creates its own state

- Check that the book, queue or store the dispatch step enforces is re derived from confirmed real events, not only written at submit time or tied out once at cutover.

- Compare the enforced store against the external truth and report unowned, overstated and missing entries by count before judging any downstream step.

- Read records at the consumer in the shape the consumer reads them and fail the audit on hollow records such as empty reasons, missing state records or a known flag set from a partial return.

## Isolate failures and prove single running

- Require proof that overlapping scheduled invocations cannot run the same pass at once, by observing competing invocations against the actual ownership boundary and checking restart/reconciliation behavior. A single-instance lock plus zero observed duplicates is supporting evidence; zero duplicates alone does not prove exclusion under overlap.

- Check that one bad intent, symbol or record is rejected on its own and cannot abort the whole pass for every later item.

- Count duplicate submissions by their natural key for the window and name any group found rather than netting it away.

## Report with named opens

- Report GREEN only for rows proven on the final live state and name every unproven row as PARTIAL, BLOCKED or UNVERIFIED with its missing proof.

- Have a checker who did not do the work re count the headline numbers from the broker and ledger before the verdict is delivered.

- State plainly when a claimed fix left no trace in the audit record, and carry that row as UNVERIFIED into the next audit instead of closing it.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with the host’s connector-setup procedure (historical locator: `/opt/muse/skills/custom-connector-setup/SKILL.md`, an external host dependency; see [portable host setup](../../docs/OPERATING-PATHS.md#establish-a-portable-host-contract)), or build a custom connector.

## Alternatives for better results

- Run the proof during a real session window when fills actually occur instead of reconstructing the path afterwards from reports.

- Make the order path the first bounded audit phase and prove it completely, then continue through the remaining requested surfaces. Keep every acceptance row visible; a narrower proven phase never shrinks the user’s requested audit or turns unverified rows GREEN.

## Host portability

`muse.*` names above describe the originating host. Discover equivalent advertised search, read, image-view and execution capabilities on the current host; do not call tools that are absent. The historical connector-setup path is not bundled. Use [the portable host contract](../../docs/OPERATING-PATHS.md#establish-a-portable-host-contract), retain the same evidence and authorization boundaries, and name a missing capability rather than pretending the recipe ran. Installing a connector or service still requires the task’s authority.
