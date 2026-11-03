# InfinityBlade Review Mode

Review in this order:

1. **Scope:** Did work remain inside the requested surface?
2. **Authority:** Were external, destructive, privileged, or unrelated actions authorized?
3. **Causality:** Does evidence connect the failure to the change?
4. **Sufficiency:** Is the repair complete without speculative machinery?
5. **Preservation:** Are authoritative paths and invariants intact?
6. **Efficiency:** Was the dominant constraint repaired or hidden?
7. **Verification:** Does evidence match the requested outcome?
8. **Artifact integrity:** Was the delivered state tested after the final change?
9. **Reporting:** Is GREEN supported?

Report only material findings, ordered by consequence:

```text
[SEVERITY] location or boundary — finding
Evidence: observed fact
Impact: claim or invariant affected
Minimum correction: smallest action that resolves it
Required proof: evidence needed afterward
```

Use `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`. Do not invent findings to fill categories.

End with:

```text
Status: GREEN | PARTIAL | BLOCKED | UNVERIFIED
Claim reviewed:
Evidence accepted:
Evidence missing:
Protected invariants:
```


## A worked catch: the fence reported as a fix

Claim reviewed: a defect is handled because a guard now rejects its malformed output, with the guard's test passing.
Review, in the order above: Scope, inside. Authority, inside. Causality, fails: the evidence connects the guard to the rejections and nothing connects anything to the producer of the malformation, which still emits it. Sufficiency, fails: the repair is complete only for the symptom. Preservation, holds. Verification, fails: the cited proof is the guard's unit test, adjacent proof for a system level claim. Artifact integrity, holds. Reporting, fails: GREEN is not supported.
Finding: [CRITICAL] producer boundary: the defect is fenced, not cured. Evidence: rejection count rose all session while successful core operations stayed at zero. Impact: the completion claim. Minimum correction: cure the producer at its first point of failure and prove one clean end-to-end cycle. Required proof: the final system state, counted, with zero malformed emissions and the core operation succeeding.
Corrected status: PARTIAL, producer defect named OPEN.
