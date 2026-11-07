# Operator guide: wiring each mechanism

Read the row for the discipline you are building. Each row states the exact
input, wiring point, output, and proof. "Host" means the system adopting this
package. Keep host state outside this skill folder.

## 1. Proactive lanes (`bin/proactive.py`)

1. Label a logged timeline with MUST, MAY, MUST-NOT, and OTHER windows.
2. Call `score_timeline(windows)`. Its cost is 1 per fire plus an additional 4 for each MUST-NOT fire (total 5 for a violation). Deploy only if benefit minus lambda times
   cost is positive at the lambda that prices the lane's real interruption.
3. Put lane costs in configuration: `C_FA`, `C_FN`, `margin`, `min_interval`,
   `max_fires_per_window`, `mode`, and `class` (`horizontal` or `vertical`).
   Costs, margins, clocks and history stamps must be finite; intervals are
   nonnegative, the rate window positive, and the fire cap a nonnegative integer.
   Invalid numeric configuration cannot silently disable the gate. The pure
   rate check and a later history write are separate operations: a concurrent
   host must serialize decision plus reservation before admitting a send.
4. Start with `mode: "observe"`. A fire becomes `would_accept`; record it in
   `LaneLedger`. Promotion to `auto` is a human configuration change.
5. Inside the send path, call `decide_lane` before delivery. Then grade the
   draft with `grade_delivery`; metadata leakage blocks the send.
6. If a model judgement starts work, validate it with `validate_assessment`:
   every enabled rule exactly once, evidence on every judgement, accept only
   with a matched rule and intent evidence.
7. Record feedback by fire ID: `accept`, `reject`, or `ignore-timeout`.
   Audit silence with `LaneLedger.audit_silence`; silence is a verdict.
8. Calibrate any model judge with `consistency_filter` and `judge_agreement`
   against human-labelled entries. A seed set is not a human holdout.

Proof: package test `ProactiveTests`, plus one host candidate that fires and
one that stays silent through the real lane.

## 2. Instincts (`bin/instincts.py`)

1. Capture observations with `capture_event`. It rejects self-observation,
   redacts secret-shaped fields, and truncates long values.
2. Distil repeated observations with `extract_candidates`, or supply the same
   shape from a model observer pass. Candidates land as `pending`.
3. Confidence is earned by count: 3 to 5 observations, 0.5; 6 to 10, 0.7;
   11 or more, 0.85; a stronger source may earn 0.9.
4. At session start, call `build_injection`. It enforces the 0.7 confidence
   floor, the success-rate floor, contradicted freeze, near-duplicate merge,
   per-type and total caps, summary and budget caps, and named omissions.
5. Promotion to global requires two or more contexts and confidence at least
   0.8, and remains human-gated: `promotion_decision` proposes; it does not
   promote by itself.
6. External units enter only through `import_instinct`: size cap, public
   remote check, system-path block, pending status, inherited-only landing.
7. When mature units cluster, `cluster_skill_candidates` proposes a skill
   draft. Nothing self-installs.

Proof: package test `InstinctTests`, plus one host injection block read back
with its omissions named.

## 4 and 5. Memory (`bin/memory_core.py`)

Store layout: `profile.json`, `facts.jsonl`, `retrievals.jsonl`, and an
`erasure/` folder created by forgetting. Initialize once:

```python
from memory_core import MemoryStore
store = MemoryStore("<host-state>/memory").initialize()
```

1. Profile: `add_profile_fact("static" | "dynamic", bucket, text,
   source_fact_id=None)`. The caps are 8 static and 8 dynamic. Buckets
   partition by topic. Supply a source fact ID for derived profile facts so
   erasure can remove that exact association.
2. Facts: use the extraction spec in `memory-extraction-spec.md`. Every fact
   is self-contained, 15 to 80 words, with entities and validity stamps.
3. Edges: `apply_edge(new_id, target_id, "updates" | "extends" | "derives",
   date)`. `updates` retires the target with `valid_until`; `derives` marks
   the new fact inferred and review-pending. An update takes effect at the
   later of this transition date and the successor's existing `valid_from`;
   it does not extend a predecessor beyond an independently known expiry.
4. Review: `review_queue()` ranks pending inferred facts by support count.
   `review(id, "approve", date)` clears the flag; `"decline"` forgets it.
5. Corrections: `propose_correction` writes a proposed successor and leaves
   the predecessor current. `apply_correction` is the reviewer step.
6. Recall: `recall(query)` returns `supported`, `closest-only`, or
   `not present`. Never build on closest-only as if it were supported.
   Proposed facts never surface. Validity is the half-open interval
   `[valid_from, valid_until)`: expired and future facts do not appear in
   current recall, including through graph expansion. A predecessor remains
   visible until a future replacement takes effect or its separately known
   expiry, whichever comes first. Pass `as_of="YYYY-MM-DD"`
   to `search`, `recall`, or `build_context` for an explicit historical view.
   Unapproved inferred facts are flagged in hits and injected text.
   `build_context` returns every omitted ID in its `omitted` metadata. Forward
   that metadata alongside the text; the bounded text contains only a generic
   footer, and very small budgets may leave no room even for that footer.
7. Future assertions: `normalize_future_fact` sets true-from to the stated
   date and never turns a deadline into true-until.
8. Maintenance: `audit_corpus` reports exact and near duplicates,
   feedback-loop clusters, malformed facts, and the junk rate. It records
   junk skeletons in a near-miss ledger when given one. It never deletes.
9. Forgetting: `forget_by_id` returns a result per ID and writes a receipt
   plus tombstone. Semantic forgetting is two calls by design:
   `semantic_forget_preview` first, then `forget_semantic` with exactly the
   previewed IDs.
10. Promotion and migration: only `promote_session_lesson(..., accepted=True)`
    crosses a session lesson into permanent memory. `MemoryStore.migrate_from`
    copies a consistent prior store, validates it, counts retrievable facts,
    and carries its erasure receipts and tombstones. Existing target tombstones
    are preserved even with `replace=True`; migration cannot revive their IDs.
11. Demotion: `demotion_candidates` names standing facts with no retrievals
    in the window for human review. It never drops them silently.
12. Operation grading: `score_operations` grades add, update, and delete
    separately. No evidence is UNMEASURED, and UNMEASURED is not a pass.

Proof: package test `MemoryTests`, plus a host read-back of one supported,
one closest-only, and one not-present query.

### Memory crash recovery and exact erasure scope

Every public store operation acquires the same local lock and completes any
committed `.pending-transaction.json` before reading or writing. Single-file
edits use atomic replacement. Multi-file initialization, migration and erasure
persist a replacement journal before replacing their files; a crash after that
commit rolls forward on reopening. `store.recover()` invokes the same recovery
explicitly. An interrupted operation may already be committed even when the
caller did not receive success: reopen, recover, and inspect its receipt before
deciding what remains. If recovery reports a corrupt journal or inaccessible
destination, retain the journal and repair that concrete storage fault before
retrying recovery. Deleting the journal would discard the recovery contract.

`forget_by_id(ids, date, index_path=None)` removes exact facts, graph references,
retrieval records, and linked profile entries in one recoverable operation. An
optional index must be a JSON mapping from keys to fact IDs; missing or invalid
indexes fail before commit. Every writer, including correction creation, checks
tombstones. Receipts record index cleanup counts without private index keys.
Use opaque fact IDs: IDs remain in erasure evidence. Semantic preview searches
the current searchable view; inspect `list_facts()` for inactive records when
the intended deletion includes history. Unlinked text, external indexes not
supplied to this operation, backups, and physical media require their own
explicit erasure inventory. These mechanisms do not infer those associations.

The journal and canonical store are trusted host state, outside model-controlled
input. All cooperating processes must use the store API and the same local
filesystem; direct readers can observe a multi-file replacement in progress.
The locks are not distributed coordination. Files are flushed and atomically
replaced; directory entries are also flushed on POSIX. Exact power-loss behavior
still depends on the filesystem and platform. The crash tests exercise process
termination, reopening and recovery rather than certify every storage device.

## 6 and 7. Skill laboratory (`bin/skill_lab.py`, `bin/reliability.py`)

1. Before a skill enters the library, run `lint_skill_text` and `skill_size`.
   At or over 20,000 bytes, split body plus references.
2. Declare capabilities explicitly. No declaration is a rejection, never an
   inference.
3. Estimate cost with `token_cost`. A heavy implicit skill fails review until
   it is explicit-only or split.
4. Scan candidates with `adoption_scan`. Missing universal components score
   zero. Conditional components enter the denominator only when present. A
   scanner configuration inside the scanned repo needs the trust flag.
5. Scan configuration with `scan_config` and staged content with
   `scan_staged_text`. This package ships a named subset of the full audit
   taxonomy; the report states that limit.
6. Build eval sets with a reference solution, balanced should and should-not
   cases, isolated trials, and an explicit judge `Unknown` exit:
   `validate_eval_set`. Isolation and the Unknown exit require actual boolean
   `True`; truthy strings do not establish either contract.
7. Trigger wording: build 20 balanced queries, split validation and final.
   Select with `score_predictions(..., "validation")`. Run
   `run_final_test` once per candidate and dataset. A validation score is
   never reported as a final test score.
8. Grade reliability with `reliability`: capability is pass@3 at least 0.90;
   release-critical regression is pass^k equal to 1.00.
9. Validate agent trajectories with `validate_trajectory`: tool order,
   forbidden tools absent, and partial argument checks.
10. Record consequential actions as evidence capsules. `EvidenceCapsules`
    refuses SE4 in ordinary record mode, verifies the hash chain at the exact
    bad entry, and refuses SE3 and SE4 in replay. Recording and verification
    share a local lock; each new chain is atomically replaced, so a failed write
    preserves the previous complete chain. A locally stored hash chain detects
    inconsistent edits; it does not authenticate a rewritten entire chain or
    establish that an external effect occurred.
11. Check metrics with `metric_record`: every headline number declares
    `measured_this_run` or `replayed`.
12. Check closure claims with `closure_check`: a cited pull request must be
    merged; a cited release must exist.
13. Strengthened tests use `f7_check`: clean passes and mutant fails, or the
    fix is rejected.

Proof: package tests `SkillLabTests` and `ReliabilityTests`, plus the host's
own eval set named in its change record.

## 9. Authority (`bin/authority.py`)

1. Grant scope once as `Mandate.create(scope, granted_by, policy_version)`.
2. At resume, call `Mandate.revalidate`. It refuses policy changes,
   generation mismatches, and any widening. A summary never grants scope.
3. Hand off context through `HandoffStore`, which lives outside any tool
   registry. The token is shown once, stored as a hash, TTL-bound, claimed by
   exactly one waiter, and consumed on delivery. It delivers a summary only.
4. Validate checkpoints with `validate_checkpoint`. Over-budget checkpoints
   are rejected, never silently truncated.
5. On interrupted work, use `recovery_plan`: requeue only unread inputs and
   open with the fixed inspect-before-acting note.
6. For streamed fenced content, use `make_fence_token` and `FenceFilter`.
   The random suffix and holdback buffer stop a split token leaking.
7. Compaction that rewrites history uses `transactional_compact`:
   generation-checked, with the prior history restored on failure.
8. Peer standing is `peer_standing`: repeated defects lower the score; below
   the floor the peer is read-only until a human restores it.

Platform limit, stated plainly: per-turn capability minting, the host's own
tool registry, and its human-send boundary are properties of the runtime.
This package supplies the portable contracts and stores; it cannot mint the
host's capabilities for it.

Proof: package test `AuthorityTests`, plus one host resume that revalidates a
mandate from the record rather than from a summary.

## 11. Rationale (`bin/why.py`)

1. Create entries with `new_entry` or the JSON template. Identity is a UUID.
2. Every entry names the decision, each rejected alternative with why it
   lost, the reason, type, status, evidence grade, source, revisit trigger,
   and a `see` locator.
3. Unattended capture is `pending_confirmation: true`; it neither drops the
   finding nor asks into the void.
4. Append with `append_entry`; invalid entries are refused.
5. Inject only `injection_view`: active entries. Superseded rationale is
   never current context.
6. Keep episodic exemplars beside rationale entries and validate them with
   `validate_exemplar`. Grade experience memory with `evaluate_experience`.
7. Store reusable context once in `FragmentRegistry`; cite it by hash with
   `cite`, and verify objects with `verify`. Concurrent insertions preserve
   existing names. An existing object with the wrong digest is refused instead
   of being silently trusted or overwritten.

Proof: package test `WhyAndFreshnessTests`.

## 12. Freshness (`bin/freshness.py`)

1. Classify every stored fact as `timeless`, `dated`, or `pointer` and check
   it with `validate_fact`.
2. Run `lint_text` in the host's nightly or review pass. FRESH-1 is an
   unstamped quantitative claim about a volatile noun. FRESH-2 is an aged
   stamp, including a stamp inherited from the nearest dated heading. Sibling
   sections stop inheriting dates when their heading scope ends. Bare words
   such as "as of today" do not supply a calendar stamp. FRESH-3 is a pointer
   that does not resolve, and FRESH-4 reports an invalid calendar date.
3. Every aged line gets exactly one disposition, recorded as
   `freshness-action: re-observe`, `convert-to-pointer`, or `retire`.
4. Refresh-on-read happens only where the store contract declares it:
   `refresh_on_read(..., contract_declared=True)`.

Proof: package test `WhyAndFreshnessTests`, plus a host lint report with its
findings answered by disposition.

## 13 to 18. Operations (`bin/operations.py`)

### Outbound (13)

Create `OutboundGate(receipts_path, caps, open_question, transport=...)` and call `send`
inside the host's authorized send function. Purpose conditions are exact: result
needs a ready or completed outcome; attention needs the one current open
question; answer needs a reported answer. Caps throw. Without a transport,
validation returns `status=ready, sent=false`; preparation is not delivery.
An explicit transport callback receives `surface`, `text`, `recipient` and
`idempotency_key`, and must return a mapping with `id` or `receipt_id` before
`sent=true` is recorded. An exception or missing acknowledgement returns
`outcome_unknown`; the origin remains suppressed until receiver-state
reconciliation settles the uncertainty. Repeats return `duplicate_suppressed`.
Each retry receives a distinct local attempt ID while an unchanged intent keeps
its external `idempotency_key`. Resolve the exact attempt with
`gate.reconcile(origin_event, receipt_id, "not_applied", evidence)` to permit a
confirmed non-send retry, or use `"applied"` with a receiver `transport_receipt`
mapping containing an acknowledgement ID to retain delivery deduplication.
Quiesce the old worker and inspect receiver state before declaring non-delivery.
Late results remain in the receipt stream with `superseded_result=true` and
cannot settle another attempt. Evidence strings record the host's observation;
the library cannot authenticate the observer or prove receiver state itself.
Diagnostics are redacted at capture with `redact`. Never send a real message
merely to prove installation; use an authorized test receiver or keep the
host delivery boundary UNVERIFIED.

### Deterministic IDs (14)

Use `deterministic_id(parts)` at intake, creation, delivery, and effects.
Include a revision stamp in the parts when an edit should be a new event;
state that choice where the ID is defined. Audit a JSONL stream with
`check_stream`.

### Effect queue (15)

Enqueue before attempting the effect. Re-queueing increments a persistent
generation and resets attempts/backoff; generations are never reused after
completion, cancellation or reopening under this schema. Existing active rows
are migrated with their generation, revision, payload and state intact. A legacy
database cannot reconstruct generations of already deleted rows; quiesce prior
workers during upgrade so their discarded callbacks cannot cross that boundary.
When a receipt was issued, completion
requires that exact receipt and the current generation. Without one, the
existing caller-acknowledgement API remains available. Local completion is the
host's declaration, not independently verified external success.
`run_next(handler)` atomically claims due pending/later
work as `running`; the handler must explicitly complete or defer it. A running
row after a crash remains reserved until external reconciliation proves what
happened: never blindly replay an uncertain effect. `fail()` retries up to the
configured `max_attempts` and then persists a visible failed row. `stop()`
reports partial while any row remains, and completed only when the queue is empty.
`defer_later` is waiting, not failure. `record_rate_limited` never increments
attempts, honours Retry-After past the cap, and counts infrastructure errors
separately. Generic failures are bounded; exhaustion lands in the queue's
named skipped list. An effect whose receiver offers no idempotency key, no
dedup on the deterministic ID, and no reconciliation read is at-least-once
and must be designed safe under duplication.

`history(kind, key)` retains local transition evidence after completed rows are
removed. Explicit `cancel(kind, key, generation, reason)` removes unclaimed or
terminal failed work; it cannot discard uncertain running work. Delayed
defer/fail/rate-limit callbacks cannot reopen a failed or uncertain generation.
An explicit new enqueue can retry a terminal failed intent under a new
generation. All retry delays and lifetime controls must be finite numbers.

### Routing and slots (16)

Call `route_followup(owner, sender_authorized)` first: a live owner receives
the follow-up without re-triage, and the authorization check still runs.
Reserve with `SlotGuard` before work starts. Workers are capped; the owner's
follow-up may exceed the cap by exactly one human slot.

### Near-miss ledger (17)

At a gate rejection, call `NearMissLedger.record(law_id, coarse_gate,
premise)`. The premise is stored as a parameter-erased skeleton, at most 400
characters. Bounds: 4,096 laws, 512 reported, 4 samples per law. The report
states its non-authority every time.

### Approvals (18)

Record with `ApprovalStore.record(action, target, content_bytes)`. At the
action boundary use `authorize_and_consume(action, candidates, content, now)`
to atomically check exact content, target, expiry, revocation and generation,
and consume one binding. The separate `check`/`consume` APIs remain available
for compatibility but are not an atomic reservation across concurrent workers.
Edited content returns `drifted`; an expired, revoked, used, or prior-generation
record returns `authorization_invalid`; multiple live candidates return
`requires_selection`; no record returns `out_of_scope`. Persist the intended
effect before execution and reconcile an uncertain response. No approval implies
another action. Reconstruct a persistent mandate from its canonical record after
compaction when still valid; do not invent repeat user approval solely because
an executable binding needs renewal.
One atomic consumption has one winner across cooperating workers. Only
`authorized_unique` permits the associated effect; other verdicts are not
permission. TTLs and clocks must be finite, and equality with the expiry time
is expired. Consuming a binding does not prove that its effect subsequently ran.

Proof: package test `OperationsTests`, plus one host restart test for the
effect queue and one authorized host send that leaves an authoritative receiver receipt; a fake transport proves only the local callback contract.

### Queue exceptions and reconciliation

`EffectQueue.run_next(handler)` treats an ordinary handler exception as `outcome_unknown` and retains the item without automatic replay: the handler may have acted before losing its acknowledgement. Only a host-confirmed safe failure may call `fail(...)` explicitly or raise `RetryableEffectError`, which retries up to the stated attempt bound and then persists a terminal failed item. Successful handlers still call `complete(...)` or `defer_later(...)` explicitly. A retained `running` or `outcome_unknown` item requires reconciliation at the actual external boundary; neither a process restart nor a local queue receipt proves the external effect did or did not happen.

Use the recovery API after stopping the old worker and obtaining an
authoritative receiver observation:

```python
row = queue.get("publish", "artifact-event")
result = queue.reconcile(
    row["kind"], row["key"], row["generation"],
    "not_applied", "receiver lookup: absent; prior worker stopped")
if result:
    retry_generation = result["generation"]
    # run_next may now claim the original persisted intent at this generation.
```

`"not_applied"` preserves the payload under a fresh generation, invalidating
callbacks and receipts from the uncertain attempt. `"applied"` removes the row
and records reconciliation evidence. An absent, stale or already settled
generation returns `False`. This is a usable recovery route, not a claim that
the queue can infer an external outcome. Keep the deterministic receiver
idempotency key tied to the intent, not a locally assigned retry generation.

The additional `test_persistence_protocols.py` suite exercises process death
after erasure commit, multiple process writers, queue identity reuse,
reconciliation, delayed callbacks, competing claimants, single-use authority,
temporal recall and interrupted evidence writes. Run all mechanism tests with
`python3 -B -m unittest discover -s skills/agent-enhancement-systems/tests -v`.
