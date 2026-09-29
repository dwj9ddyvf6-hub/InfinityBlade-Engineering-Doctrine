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

