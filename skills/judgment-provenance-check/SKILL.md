---
name: judgment-provenance-check
description: Use whenever a ranking, board, verdict, veto, or invalidation is about to be built or spoken, even when the surface looks like a simple list; skip for raw data display with no judgment in it.
version: 1.0.0
---

# Judgment Provenance and Formation Check

## Define the surface before building it

- Write one sentence answering the user goal before building any ranking, board or summary, naming what decision or proof the surface is for, who it is for and whether it is public facing.

- Identify the formation point where conviction for an item on the surface is actually created, such as staging plus a PASS chart gate read, a scored prospective log or a signed decision.

- Bar any item that has not passed that formation point from appearing, with no exceptions for fresh or high scoring raw fields.

- List what each displayed item must carry from the formation point, covering the thesis in words, the entry zone, the stop or invalidation, the target, the gate read text, regime and structure context and the lifecycle state.

- Treat a score or an order receipt as data only, because neither one is a thesis.

- Exclude non conviction items explicitly, such as hedges, housekeeping fills and unscored experiments, and say why each class is excluded.

- Name the failure twin, the nearest past incident where a surface ranked something the underlying process had not actually judged, and state what in this design prevents the repeat.

- Build the formation point first when it does not yet exist as data, and ship the surface empty rather than filling it from raw fields, because an empty board is a valid output when nothing has passed the gate.

- Keep public surfaces inside the public data boundary, using only public snapshot content and never internal logs, registers or methodology text.

- Rebuild to the corrected definition when the user corrects what the surface is, instead of defending or patching the field composed version.

## Inventory every veto, filter and gate

- Name every veto, filter, gate and framing label in scope, covering code paths plus alert and brief wording.

- Record provenance for each item as one of a user ruling with its date or handle, a named study, the sleeve own SPEC, an inherited convention from a port or predecessor system, or defensive with no basis.

- Treat inherited and no basis provenance as findings rather than authority.

- Read the relevant entries in `~/MEMORY.md`, the decision register and the user recorded words on the question before judging any item.

- Verify the regime and context match explicitly, because a signal is only valid or invalid in the regime and context where its edge was measured.

- Grade each item as consistent, suspect on a thin or anecdotal basis, or contradicts doctrine, and judge each strategy family against its own family doctrine rather than another family doctrine.

- Keep a warning marker, a regime read and a hard veto as three different things, and check which one the code actually implements before describing any of them.

- Treat entry side and exit side uses of the same signal as separate items with separate provenance, because a ruling on one does not silently change the other.

## Check speech before presenting a verdict

- State which doctrine item makes a signal invalid, vetoed or not the validated form before telling the user so, and cite that item inline.

- Report the signal neutrally with its context when no doctrine item can be cited.

- Surface contradictions and suspects to the user as rulings to make, and never silently keep, remove or propagate a gate.

- Search for every other place a gate bundle was copied to when a user ruling removes or changes it, and propagate the change in the same pass.

- Stop and present both sides when evidence is contradictory rather than defending the current gate.

- Refuse to let a predecessor system convention outrank a recorded user ruling or a decision register entry, because route failure and inherited habit are not doctrine.

## Ship the provenance record

- Write one line per audited item naming the item, where it lives, its provenance, its doctrine citation, its grade and the ruling or action taken.

- Write the surface record with the one sentence definition, the formation point source for every item, the required per item fields, the exclusion list and the failure twin check.

- Report a ranking with no judgment artifact behind an item as unproven, even when the numbers on it are real.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Start from the artifact that formed the judgment, such as the gate read or the scored record, and build outward from it instead of starting from whichever fields are easiest to reach.

- Audit the spoken framing in the same pass as the code, because an invalid label in a brief teaches the same wrong doctrine as a veto in code.
