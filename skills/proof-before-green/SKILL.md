---

name: proof-before-green
description: Use whenever a regression gate, blocker test, suite result, dry run, or commit is about to be trusted or reported, and whenever a system is about to be called working, live, or proven, with the verdict proven on the final tree and the final live state.
version: 1.0.0
---

# Proof Before Green

## Why this skill exists

The default: letting a gate verdict, a suite result, or a live claim borrow proof from a neighboring check.
The cost: the same law printed in three places drifts in three directions, and the reader follows the copy that happens to be open while the verdict it certifies was never proven on the final thing.
The replacement: this skill owns one discipline only, the verdict. Gate mechanics route to gate-test-integrity; live-path proof routes to live-execution-proof. Where those files and this one appear to conflict on a verdict, this file governs the verdict and they govern their mechanics.

## The verdict discipline (the whole of this skill)

- A verdict is a claim about a specific final state: a named tree, a named commit, a named live window. A verdict with no state named is a rumor.
- Evidence must come after the last change to that state. Any later change reopens the verdict to the extent it could affect the proof.
- A gate verdict from a tree that moved during the run is UNVERIFIED, never a pass and never a fail.
- GREEN requires every acceptance row proven on the final state. One row proven by a unit test, a fixture, or a neighboring surface caps the whole verdict at PARTIAL, with that row named.
- Report the verdict with its evidence pointer: the artifact, the command output, or the read-back a second reader can open. A bare label proves nothing, including when a hook accepts it.
- When proof is missing, the verdict is UNVERIFIED and the missing proof is named. UNVERIFIED is a work item, not a confession.

## Routed, not restated

- Freezing the tree, staging owned work, hermetic blockers, proving the fail direction, and the three-way gate verdict: [gate-test-integrity](../gate-test-integrity/SKILL.md) and [hermetic-test-isolation](../hermetic-test-isolation/SKILL.md).
- Defining the live path, tracing one real item end to end, and counting outcomes at the final state: [live-execution-proof](../live-execution-proof/SKILL.md).
- Verifying a delegated or reported claim before repeating it: [claim-verification-ledger](../claim-verification-ledger/SKILL.md).
