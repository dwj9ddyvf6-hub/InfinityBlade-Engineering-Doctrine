---
name: agent-enhancement-systems
description: Use when building, wiring, or auditing an agent's proactive lanes, instincts, memory, recall, skill tests, library gates, handoffs, rationale records, freshness, outbound sends, deterministic IDs, effect queues, routing, near-miss learning, or content-bound approvals. Do not use for ordinary one-off work that creates none of those systems.
version: 1.0.1
capabilities: read, write
---

# Agent Enhancement Systems

## Why this skill exists

The default: reading a precise specification and reporting the mechanism as built.
The cost: no gate fires, no queue survives a restart, no ledger exists, and the next agent inherits prose where machinery was promised.
The replacement: this folder ships the machinery. Import the module, wire it at the boundary the discipline names, run the package test, and report the host lane UNVERIFIED until the mechanism fires inside that lane's own path.

## Start here, in order

1. Run the package proof before trusting any module:

   ```bash
   python3 tests/test_agent_enhancement.py
   ```

   Expected result: the runner reports the executed test count and `OK`, with exit status zero. Record the actual count and source revision; the count grows as regressions are added. If the run fails, fix the package or report UNVERIFIED. Do not work around a red package test by copying a module elsewhere.

2. Read the discipline map below and choose the smallest module that owns the surface. Do not import all modules by default.

3. Read the matching procedure in [references/operator-guide.md](references/operator-guide.md). It states the input, the wiring point, the output, and the proof for each discipline.

4. Copy the matching file from `templates/` into the host's own state area. Never store live host state inside this skill folder.

5. Wire the mechanism where the act happens:
   - a proactive gate inside the lane's send path;
   - an outbound gate inside the host's send function;
   - an effect queue before the side effect is attempted;
   - an approval check immediately before the irreversible act;
   - a memory write through the store transaction, never by editing its files casually.

6. Run the package test again after wiring, then run one host-level smoke test with temporary state. A package pass proves the named contracts covered by those tests. A temporary-state host smoke test proves that tested integration; a live claim additionally needs an authorized real-path effect or authoritative receipt. Keep these evidence boundaries separate.

7. Record the decision and the losing route with `bin/why.py` when the integration closes a design path.

8. End with a STATUS line carrying an evidence pointer: the package test output, the host smoke-test output, or the named missing proof.

## Discipline map

| Discipline | Module | First use |
|---|---|---|
| 1. Price every proactive lane | `bin/proactive.py` | `score_timeline`, then `decide_lane` inside the send path |
| 2. Keep instincts | `bin/instincts.py` | `capture_event`, `extract_candidates`, then `build_injection` |
| 4. Memory as profile plus graph | `bin/memory_core.py` | `MemoryStore.initialize`, `add_fact`, `apply_edge` |
| 5. Honest recall and governed maintenance | `bin/memory_core.py` | `recall`, `propose_correction`, `forget_by_id` |
| 6. Test skills like blockers | `bin/skill_lab.py` | `lint_skill_text`, `score_predictions`, `run_final_test` |
| 7. Gate the library and grade reliability | `bin/skill_lab.py`, `bin/reliability.py` | `adoption_scan`, `scan_config`, `EvidenceCapsules` |
| 9. Authority boundaries | `bin/authority.py` | `Mandate.revalidate`, `HandoffStore`, `recovery_plan` |
| 10. Bounded hidden-rubric prose pass | Practice only | Use `references/prose-review.md`; no code is shipped for this discipline |
| 11. Record the why | `bin/why.py` | `new_entry`, `append_entry`, `injection_view` |
| 12. Timeless, dated, or pointer | `bin/freshness.py` | `validate_fact`, then `lint_text` in the host's review pass |
| 13. Outbound purpose, receipt, and cap | `bin/operations.py` | `OutboundGate.send` inside the real send path |
| 14. Deterministic IDs | `bin/operations.py` | `deterministic_id` at intake, creation, delivery, and effects |
| 15. Durable effect queue | `bin/operations.py` | `EffectQueue.enqueue` before attempting the effect |
| 16. Owner routing and slots | `bin/operations.py` | `route_followup` and `SlotGuard.reserve_worker` before work starts |
| 17. Near-miss ledger | `bin/operations.py` | `NearMissLedger.record` at a gate rejection |
| 18. Content-bound approvals | `bin/operations.py` | `ApprovalStore.check` immediately before the act |

Disciplines 3 and 8 are owned by the existing procedure skills `gate-test-integrity`, `hermetic-test-isolation`, `proof-before-green`, and `claim-verification-ledger`. This folder does not duplicate them.

## Non-negotiable wiring rules

- **A script nothing calls is not a live mechanism.** State the caller in the integration record. If no caller exists, the status is PARTIAL, not shipped-in-host.
- **Observe before auto.** A new proactive lane starts in `observe`; promotion to `auto` is a human configuration change for named narrow rules.
- **No second memory store.** `MemoryStore` is the package form for an adopter who has no store yet. An adopter with a memory of record maps these contracts onto that store and does not run two stores in parallel.
- **Derived facts wait.** An inferred fact is `review: pending` until a human approves or declines it. Declining forgets it.
- **The final test stays untouched.** Trigger and eval sets used to select wording are validation data. `run_final_test` refuses a second run for the same candidate and dataset.
- **Approvals bind bytes.** A summary, a filename, or a prior version is not the approved content. Any drift returns `drifted`.
- **Waiting is not failure.** `Later` and rate-limit pauses do not consume generic attempts.
- **A near miss proves nothing about possibility.** The ledger is diagnostics only and never feeds ranking, selection, or rejection counts.
- **Redact at capture.** Diagnostics pass through `operations.redact` before storage, not before display only.

## Practice, not code

Discipline 10 is a writing and review practice. Its value is a task-specific hidden rubric, one bounded revision loop, and naming the weak dimension when the cap is reached. Manufacturing a generic prose scorer would pretend to judge what it cannot judge. Use the procedure in `references/prose-review.md` and grade the result as NOT CODE in any adoption record.

## Failure forms

| Failure | Correction |
|---|---|
| "The package test passes, so our live lane is gated." | Adjacent proof. Run a host smoke test through the lane's real send path. |
| "We copied the module and changed it until it passed." | The package test no longer proves the shipped mechanism. Fix the package source or keep the fork visibly separate. |
| "The queue is durable because the function exists." | Enqueue before the effect, restart, and prove the row survives and settles by generation and receipt. |
| "The approval said yes yesterday." | Re-check action, target, content hash, expiry, revocation, use, and generation at act time. |
| "Recall found something similar." | Report `closest-only`; never build on it as supported. |
| "The skill scored well on the set we tuned it with." | That is a validation score. Run the untouched final set once. |

## Proof standard for this folder

The package proof is `tests/test_agent_enhancement.py`: the current regression cases covering the shipped modules, using only temporary state and the Python standard library. A change to any module re-runs the whole file. A test that passes on a clean replica and fails on a mutant is handled by `skill_lab.f7_check`; use it for strengthened tests.
