---

name: judgment-provenance-check
description: Use whenever a ranking, board, verdict, veto, or invalidation is about to be built or spoken, even when the surface looks like a simple list; skip for raw data display with no judgment in it.
version: 1.0.0
---

# Judgment Provenance and Formation Check

## Why this skill exists

The default: checking a judgment's provenance in whichever of three overlapping files happens to be open.
The cost: one doctrine stated three times at three lengths drifts, and a surface gets built under the loosest copy.
The replacement: this file is the routing checklist only. Precedence is stated here and nowhere else needs to guess: conviction-surface-definition governs what a surface is and where its conviction forms; doctrine-provenance-check governs the audit of any single veto, filter, or gate; this file governs the order in which the two are run before a judgment is built or spoken.

## The checklist, in order

1. Define the surface first, under conviction-surface-definition: one sentence naming the decision the surface serves, its formation point, and what each item must carry from that point. Ship it empty rather than filling it from raw fields.
2. Inventory every veto, filter, gate, and framing label the judgment depends on, under doctrine-provenance-check: provenance recorded per item, inherited and no-basis items treated as findings, regime match verified explicitly.
3. Check speech before presenting: state which doctrine item makes a signal invalid, vetoed, or not the validated form, cited inline; where no item does, report the signal neutrally with its context.
4. Keep a warning marker, a regime read, and a hard veto as three different things, and describe the one the code actually implements.
5. Treat entry side and exit side uses of the same signal as separate items with separate provenance.

## Routed, not restated

- Surface definition and formation points: [conviction-surface-definition](../conviction-surface-definition/SKILL.md).
- Veto, filter, and gate provenance: [doctrine-provenance-check](../doctrine-provenance-check/SKILL.md).
