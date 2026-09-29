# Lessons from the field: turning repeated failures into doctrine

This guide supplements the core InfinityBlade skill. It distills recurring failure patterns from real agent work across software changes, research pipelines, generated artifacts, browser workflows, publishing, and backups. Examples are anonymized without discarding useful technical substance. Exclude personal names or contact details that are not intended for publication, account identifiers, credentials, private conversations, and machine-specific paths. Retain workload measurements when they explain the diagnosis; describe their scope so readers do not mistake them for universal benchmarks.

Before sharing a revision, scan current files, every reachable ref, and commit metadata. After rewriting history, also test known old commit/blob URLs through the host's API and raw-file routes, and check cached views and pull-request/fork references where accessible. A clean branch does not prove that old objects are inaccessible. Request the host's sensitive-data removal process when eligible, and report any copies or caches that remain outside the verified scope.

The central lesson is simple: **when a failure repeats, improve the system’s memory and proof—not merely the next prompt.** Convert each incident into a precise invariant, a discriminating check, and a durable place where the next agent will find it.

## Failure patterns and durable countermeasures

### 1. A plausible artifact can still be the wrong artifact

**Failure pattern:** A chart, build, document, or model output looks reasonable, but came from a different renderer, branch, configuration, data cutoff, or release than the workflow requires. Names such as latest, final, and corrected do not establish lineage.

**Countermeasure:** Record the authoritative repository/ref, commit or release, entry point, configuration, input identity, and expected output form before producing anything. Hash critical inputs and outputs when byte identity matters. Compare at least one known-good example from the same path. Keep research/intermediate artifacts distinct from user-facing deliverables and prove the final artifact came through the intended path.

### 2. Similar labels can hide different semantics

**Failure pattern:** An agent confuses signals, timeframes, environments, accounts, or similarly named entities. A result can be numerically valid yet answer a different question.

**Countermeasure:** Resolve names to an authoritative source definition. Carry identity, date, unit, timeframe, and version beside every row. Test known positive and negative cases; assert coverage and uniqueness; do not substitute a nearby name or infer identity from visual proximity. Keep labels derived from the same versioned source as the behavior they describe.

### 3. A success message is not durable state

**Failure pattern:** A command exits successfully, a toast appears, a queue count changes, or an editor briefly looks correct, while the destination has not saved the intended object—or has saved only part of it.

**Countermeasure:** Define the success boundary before acting. After each consequential mutation, wait for the interface or service to settle, read back the exact durable row, refresh when appropriate, and reconcile source against destination. Distinguish draft, queued, published, delivered, and remotely synchronized states. Historical screenshots and earlier receipts prove only their timestamped state.

### 4. Rich UI objects can be damaged by text-only edits

**Failure pattern:** Replacing visible text in a media-bearing card, document, or form leaves stale blocks, duplicates, or detached attachments even though the editor looks plausible.

**Countermeasure:** Use the product’s supported semantic editing path and preserve the structured object. Do not use raw contenteditable replacement, select-all, or other text-only shortcuts on rich objects unless the product guarantees attachment preservation. If a safe edit path is unavailable, stop and rebuild from the authoritative structured source. Re-read the saved object and its media after every edit.

### 5. Batch work magnifies small identity errors

**Failure pattern:** Missing rows, duplicates, wrong pairings, stale text, or changes to unrelated items accumulate because the agent relies on nearby names, a queue preview, or an assumed starting state.

**Countermeasure:** Freeze a manifest before mutation. Give each target a stable identity and idempotency key; include the exact input and output references and the expected final state. Reconcile existing records first. Preserve non-targets. Stop the batch on the first failed row, record expected versus observed state, repair one item at a time, and rerun the complete manifest gate. Never hide a failed published item by deleting or reposting it without specific authorization.

### 6. Repeated user corrections are evidence, not friction

**Failure pattern:** The agent repeats the same explanation or action after the user has identified a concrete contradiction. The work grows noisier while the original defect remains.

**Countermeasure:** Treat a specific correction as a falsification test. State what prior assumption it disproves, reproduce the exact route, identity, artifact, and state the user named, and inspect for a second implementation, stale cache, wrong version, or environment mismatch. Change the hypothesis before acting again. Do not ask for a decision the user has already made; ask only when a material choice or authority is genuinely missing.

### 7. Tool failure and security boundaries are different things

**Failure pattern:** A UI automation route fails and the agent concludes the task is impossible—or tries an unsupported browser, hidden control, broader desktop takeover, or security workaround.

**Countermeasure:** Classify the failure: implementation, wrong hypothesis, transport, provider capability, missing dependency, account state, or permission boundary. Use the requested app and narrowest supported surface. Check tool documentation and exact live state before switching routes. Treat the installed tool, its cached package, its source manifest, and effective configuration as potentially different states; compare them and test the original user-facing route, because a config parser passing does not prove the requested workflow resumes. When a browser permission or authentication step belongs to the user, explain the precise manual step and stop at that boundary; never bypass the control or handle one-time authentication codes on the user’s behalf.

### 8. Generated analysis and prose can drift apart

**Failure pattern:** The calculation is correct but the explanation misstates direction, thresholds, units, geometry, horizon, or source. Templates may omit a meaningful condition or produce repetitive filler. Current-event claims may be invented to make every item look complete.

**Countermeasure:** Treat each sentence as a claim with a source. Validate narrative fields independently against the canonical measurements and definitions, including change-versus-level semantics and configured thresholds. Check coverage, grammar, uniqueness, and identity across the full batch. For factual updates, use verifiable sources; include only relevant confirmed developments, and omit the line rather than inventing or padding when nothing qualifies. Variation in wording must never weaken factual consistency.

### 9. A copied backup is not proof of recoverability

**Failure pattern:** Files exist in a sync folder but uploads remain pending, locked files were skipped, the cloud listing is incomplete, or a “complete” status file is stale. Removing the local source too early can turn a partial copy into data loss.

**Countermeasure:** Measure free-space headroom and active jobs before a large copy. Use resumable incremental passes and bounded status reporting. Preserve source data while transfer is pending. Verify the remote destination independently with file counts, sizes, checksums, or the provider’s authoritative sync state; check locked-file exceptions explicitly. Then restore representative data into an isolated clean location and verify that it is usable. A remote listing or matching hash proves transfer, not recovery. Only reclaim or offload the source after both transfer and restore checks pass.

### 10. Knowledge in chat does not reliably survive a handoff

**Failure pattern:** A later run chooses the wrong version, repeats browser setup failures, or cannot reproduce the work because the procedure lived only in conversation or local machine state.

**Countermeasure:** Put the durable operating contract beside the project: version-pinned runbook, exact entry points, manifests, hashes where important, required permissions, safe recovery actions, known failure modes, verification gates, and a dated receipt. Test the handoff from a fresh checkout or machine when portability is claimed. Keep secrets, cookies, browser profiles, authentication state, and unnecessary raw conversation dumps out of shareable repositories; archive only what is needed and safe to preserve.

### 11. Efficiency breakthroughs must preserve the evidence contract

**Failure pattern:** A pipeline appears asynchronous or batched but is still serialized at its real bottleneck, overwhelms a downstream service, retains native memory between jobs, or serves only process-local cached state. A superficial fix can then hide the issue by shrinking the workload, weakening completeness rules, or treating synthetic load as production proof.

**Countermeasure:** Instrument each boundary and distinguish queue delay from execution, I/O from CPU, batching from concurrency limits, heap from process/native high-water memory, and local cache from durable evidence. Use real bounded CPU workers for synchronous computation, but measure their lifecycle and recycle them in bounded groups when native allocations accumulate. Bound fan-out independently of batch size, make retries due-time- and deadline-aware, coalesce same-identity in-flight reads, and let latency-sensitive lanes outrank bulk work. Persist only complete, identity-verified evidence; serve stale evidence only under an explicit retryable-failure policy, never across identity or integrity conflicts. Keep a single authoritative writer when calculation is parallelized. Separate the immutable fact identity (instrument, source, interval, completed boundary, calculation version, and payload) from the changing audience, entitlement, or observer relationship; reuse a fact only after exact normalized equality and record authorized observations separately. Change acquisition windows or data volume only after a representative provider probe proves the new input still satisfies the original analytical warm-up and coverage contract.

**Anonymized pipeline case:** The following workload details are retained because they make the diagnosis concrete. They describe specific probes, not a personal profile or a promised service level.

#### Queue delay and CPU execution

In one market-data analytics system, adding asynchronous queue slots did not parallelize synchronous calculations: a close cycle still showed roughly 90 seconds of calculation delay. Bounded calculation workers, read-only database connections, one parent writer, hot-lane priority, and timestamps taken after queue wait addressed the actual execution path. After the repair, an observed first completed-bar signal was persisted about three seconds after its boundary and the bounded batch drained in the observation window; this is not a claim that every symbol is sub-second. A separate aggregation repair replaced five higher-frame history acquisitions with two canonical source tapes while preserving five evaluation lanes and their event identities; parity fixtures covered missing source hours, shortened session tails, open-week withholding, and warm-up scheduling.

#### Worker lifetime and memory

Separate probes exposed worker-retained native memory. Bounded worker batches and worker exit reduced high-water allocation in controlled probes: a recycled 500-symbol run completed under the 25-second gate with peak worker RSS of about 325 MB, and a repeat peaked around 622 MB. Earlier long-lived-worker probes on a different 411-symbol workload peaked around 1.21–2.09 GB. Those workloads differ, so the figures demonstrate the diagnosed memory-retention pattern, not a precise apples-to-apples speedup. On the live host, a separate repair combined the exact rebuilt release, explicit memory ceilings, negative caching for invalid venue lookups, and a shorter provider warm request proven by a representative probe; the existing minimum verified-history requirement remained unchanged.

#### Downstream fan-out and duplicate work

The other hidden bottlenecks were at boundaries: 1,000 warm dashboard reads had launched 1,000 unnecessary producer jobs; request batches of 30 still allowed 17 concurrent downstream relays; and a 500-request same-identity chart burst caused avoidable duplicate provider pressure. The repaired patterns were zero producer jobs for read-only refreshes, an independent three-relay concurrency cap, and single-flight coalescing that reduced the same-key burst to one cold upstream load. A synthetic 1,000-recipient persistence/drain test used 20 batches of 50, completed all rows without duplicate replay, and capped transport concurrency at three. Unique source identities, not the number of users or associations alone, determine acquisition capacity. These are workload-specific receipts, not universal limits or a claim of an external 1,000-user soak; keep those proof categories distinct.

#### Immutable facts and observer scope

An identity audit also found that one global event key had been fingerprinted with the roster that first observed it. That made observer scope look like part of the market fact and caused valid cross-roster reuse to collide. The repair compares a normalized immutable fact tuple (instrument, provider, interval, completed bar, price, and marker), preserves the first stored fact, rejects conflicting values, and records each authorized roster observation separately. Delivery eligibility is checked against the matching authorized observation, not inferred from whichever observer wrote first. This removed a false conflict without weakening price, provider, or audience checks.

#### Durable evidence and cold starts

**Durability and data-quality lesson:** A verified chart tape held only in an ephemeral edge cache vanished on a cold process. The durable path stored only complete, identity-checked, conflict-free evidence and allowed a bounded stale response only for retryable upstream failures; identity/integrity failures still failed closed. For cold misses, same-key refreshes joined in-flight work and a complete verified tape was made durable before the cold response depended on it; warm advisory persistence could move off the response path. In another measured provider probe, reducing an hourly bootstrap request from 120 to 60 days brought 67 symbols within the provider's page budget and returned 7,196 verified bars. The pre-existing 200-bar minimum warm-up remained intact. The lesson is to remove redundant acquisition, not analytical authority. Lease claims were also moved to immediately before serialized delivery so work could not expire while waiting in a queue; propagation and expiry clocks were never renewed by retries.

#### Report measurements honestly

**Proof discipline:** Report the exact workload, concurrency, environment, completion count, latency/memory measure, and whether evidence is synthetic, source-level, deployed, or externally observed. Do not compare unlike probes as a precise speedup, infer a live host state from a source test, or claim customer-scale capacity from a fixture. Add a regression test for the invariant and rerun the original workload after the final change.

### 12. A comprehensive search needs a coverage ledger

**Failure pattern:** An agent searches the sources it can see, receives an empty result from one index, or stops at an inaccessible repository, then reports that it searched “everything.” Missing access or incomplete pagination is mistaken for absence.

**Countermeasure:** Define the corpus before searching: source systems, repositories and refs, relevant time ranges, search terms or file classes, and pagination boundaries. Record each source as searched, excluded, unavailable, or not yet checked. Reconcile the ledger before making an exhaustive claim; say “no matches in the sources checked” when that is all the evidence supports.

## The incident-to-doctrine loop

Use this loop whenever the same class of failure returns, or whenever a workflow spans multiple tools or durable states:

1. **Capture the contract:** requested outcome, authorized scope, protected state, identity, version, environment, and the observable success boundary.
2. **Record the contradiction:** exact expected state, exact observed state, and the artifact or transition where they first diverged.
3. **Find the first failed boundary:** trace upstream from the symptom; do not patch a downstream display if the source or transport is wrong.
4. **Choose a discriminating check:** each attempt must test a hypothesis and reduce uncertainty. Do not repeat an equivalent action without new evidence.
5. **Repair the invariant:** make the smallest structural change that prevents the failure class, not just the one example.
6. **Add a regression guard:** a test, manifest assertion, checksum, UI read-back, or operational gate that would have caught the original failure.
7. **Replay the original path:** after the last change, rerun the same route, identity, input shape, and environment at the boundary the claim names.
8. **Persist the lesson:** update the shared runbook or skill, preserve a concise receipt, and carry unresolved states forward without upgrading them to PASS.

If no action can be named that will either solve the problem or distinguish competing explanations, pause and re-scope before touching more state.

## Compact incident receipt

~~~text
Outcome and authorized scope:
Protected state:
Authoritative inputs / version / hashes:
Search coverage (when comprehensive discovery is requested): searched / excluded / unavailable / pagination:
Target identities and idempotency key (if batched):
Expected state:
Observed state:
First failed boundary:
Hypothesis and discriminating check:
Root cause:
Minimum repair and regression guard:
Final artifact / environment / commit:
Post-change proof and preserved invariants:
Status: PASS | FAIL | REPAIRED | BLOCKED | NOT TESTED
Remaining uncertainty:
Portable lesson added at:
~~~

## One-line rule

**Do not trust resemblance, intent, or success copy: bind the right identity to the right source, change state through a supported route, read it back at the real boundary, and save the proof where the next agent can use it.**
