---
name: doctrine-provenance-check
description: Audit every veto, filter, and gate, in code and in spoken framing, against stored doctrine and its provenance before calling a signal invalid or shipping a gate change.
version: 1.0.0
---

# Doctrine Provenance Check

## Purpose
Stored doctrine that is never wired into code or speech is trivia, not knowledge. This skill forces every veto, filter, and gate to carry a provenance and a doctrine check before it blocks anything or is described as invalidating anything.

## Workflow
1. Inventory the item: name every veto, filter, gate, and framing label in scope (code paths plus alert/brief wording such as `CONFLICT-VETO`).
2. Record provenance for each: user ruling (with date/handle), a named study, the sleeve's own SPEC, an inherited convention from a port or predecessor system, or defensive-with-no-basis. Inherited and no-basis are findings, not authority.
3. Check against stored doctrine before judging: read the relevant entries in `~/MEMORY.md`, the decision register, and the user's own recorded words on the question. A signal is only valid or invalid in the regime/context where its edge was measured — verify that match explicitly.
4. Grade each item: consistent, suspect (thin or anecdotal basis), or contradicts doctrine. Judge each strategy family against its own family doctrine, not another family's.
5. Speech check: before telling the user a signal is invalid, vetoed, or 'not the validated form', state which doctrine item makes it so and cite it. If none can be cited, report the signal neutrally with its context instead.
6. Surface contradictions and suspects to the user as rulings to make; never silently keep, remove, or propagate a gate. When a user ruling removes or changes a gate, grep for every other place that gate bundle was copied to and propagate the change in the same pass.

## Output Contract
A table with one row per item: name, where it lives, provenance, doctrine citation, grade, and the ruling or action taken. Any spoken invalidation of a signal cites its doctrine item inline.

## Operating Rules
1. Route failure is not doctrine: a predecessor system's convention (for example an inherited conflict flag) never outranks a recorded user ruling or decision-register entry.
2. Never generalize from an adjacent flag: a warning marker, a regime read, and a hard veto are three different things — check which one the code actually implements.
3. Exit-side and entry-side uses of the same signal are separate items with separate provenance; a ruling on one does not silently change the other.
4. When evidence is contradictory, stop and present both sides rather than defending the current gate.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
