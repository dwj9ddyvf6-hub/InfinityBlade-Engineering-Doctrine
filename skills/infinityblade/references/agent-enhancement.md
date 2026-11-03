# Agent Enhancement: Memory, Initiative, and Self-Improvement

Disciplines for the systems around the work: what the agent remembers, when it
acts unasked, how it writes and adopts its own playbooks, and how it grades
itself. The core skill governs a task; this reference governs the machinery
that makes the agent better at tasks over time.

Distilled from an inspected sweep of public agent-enhancement work (memory
systems, skill frameworks, proactivity research, prompting disciplines),
2026-10-31. Every discipline below was adopted because it adds a mechanism
this doctrine did not already have. Ideas the doctrine already covers
(spec-first work, test-driven fixes, proof before claiming, review of
delegated work) are not restated here. A second pass the same day read the
source artifacts in full, corrected several first-pass accounts of how these
mechanisms actually work, and added disciplines 11 and 12; the corrections
are itemised in the changelog for 2.6.0, not smoothed over here. A third
pass then read the layers the first two skipped (issue trackers, release
notes, test corpora, fork networks, the official vendor layer, the
benchmark literature) and graded every discipline against what it found:
2 confirmed, 8 qualified, 1 warned, 1 with no contact. Its corrections
are itemised in the changelog for 2.7.0, and each discipline below
carries its standing where the pass produced one.

A fifth pass (2026-11-02) read the source code of every repo on the list at file and line level and added disciplines 17 and 18 plus the round-5 concretions recorded at the end of the discipline list. Its account is in the changelog (2.9.0). The provenance limits on that claim are stated in the Round 5 section.

A fourth pass (2026-11-01) distilled a teardown of one harness system,
deepseek-ai/dsh-superagent-prototype at commit 6337fc8, read statically at the pinned commit. Of its eleven import
mechanisms, four were genuinely new disciplines (13 to 16 below) and
seven were mechanisms that attach to existing disciplines; those are
folded in as dated round-4 mechanism notes rather than inflating the
count. The teardown's Avoid list is recorded as round-4 cautions after
the Backlog. Round-4 provenance is stated per discipline.

## The eighteen disciplines

**Ship status (added 2026-11-02).** Each discipline below carries a ship status line directly under its heading, in one of two kinds. *Mechanism-shipped* means a skill folder in this package ships the mechanism, and the label names it. *Specification-only* means this reference states the mechanism precisely and the host must implement it; reading the specification installs nothing, and a discipline that needs code in the host (a queue, a gate inside a send path, a ledger, a cap enforced at validation time) is UNVERIFIED as a mechanism in any host that has not built it. Summary: disciplines 3 and 8 are mechanism-shipped as installable skills; the other sixteen are specification-only.

| Discipline | Ship status |
|---|---|
| 1. Price every proactive lane | Specification-only |
| 2. Keep instincts: a confidence-scored procedural memory | Specification-only |
| 3. Audit the gates for false greens | Mechanism-shipped: skills/gate-test-integrity/, skills/hermetic-test-isolation/ |
| 4. Run memory as a profile plus a graph | Specification-only |
| 5. Make recall honest and maintenance governed | Specification-only |
| 6. Test skills the way blockers test code | Specification-only |
| 7. Gate what enters the library, and grade reliability | Specification-only |
| 8. Mechanise the completion claim | Mechanism-shipped: skills/proof-before-green/, skills/claim-verification-ledger/ |
| 9. Treat compaction and delegation as authority boundaries | Specification-only |
| 10. Run a bounded hidden-rubric pass on ungated prose | Specification-only |
| 11. Record the why, not just the what | Specification-only |
| 12. Keep every fact timeless, dated, or a pointer | Specification-only |
| 13. Gate outbound messages by purpose, receipt, and hard cap | Specification-only |
| 14. Give every event, decision, and delivery a deterministic ID | Specification-only |
| 15. Queue side effects durably, and never confuse waiting with failure | Specification-only |
| 16. Route follow-ups to their owner, and reserve slots by discipline | Specification-only |
| 17. Keep a near-miss ledger | Specification-only |
| 18. Approvals are content-bound, expiring, and generation-scoped | Specification-only |

### 1. Price every proactive lane

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** nothing interrupts for free, and the price is proven before the
lane speaks. Every scheduled job, hook, or monitor that can surface unasked
is scored offline against logged timelines, gated at fire time by a judge
that is not the generator, and graded on what it delivered. A lane that
cannot state its cost defaults to silent logging.

- **Score the policy before deploying it.** Log timelines and label
  windows: MUST (acting averts a failure, benefit 4), MAY (acting is
  welcome, benefit 2), MUST-NOT (acting is a violation, cost 4); any other
  fire costs 1. Benefit is credited once per window, MUST before MAY; cost
  is charged per fire, independently, so a violation is charged even on a
  fire that also earned a benefit. Report fires, MUST recall, violation
  rate, and benefit minus lambda times cost at lambda in
  {0.25, 0.5, 1, 2, 4}. Deploy only at the lambda that prices the lane's
  real interruption cost; if silence wins at that lambda, silence is the
  policy.
- **Gate at fire time with a separate judge.** A cheap pass over
  (observations, proposed action-or-null) returns a first-person thought
  and judgement. A rejection feeds the thought back for a bounded number
  of *different* retries; exhaustion is silence, and a proposal of nothing
  is judged by the same gate. The gate is on by default: in the source
  system it is opt-in, its feedback policy is one sentence in a prompt,
  and ungated proposals publish. Adopt the opposite defaults. The
  threshold the gate applies is a calibrated probability of acceptance
  against a per-context price set by the scorer, not a number copied from
  any paper.
- **The gate must block, not merely observe.** Vendor guardrails
  commonly run in parallel with the tools they watch and can let an
  action execute before a tripwire fires. Where effects matter, the
  gate is blocking or enforced per tool. "There is a gate" is not
  evidence anything was prevented.
- **Expectation-set the gate.** Gate quality is a data pipeline, not a
  prompt: majority-vote labels, a unanimity-preferred test set,
  label-conditioned rationales, a consistency filter, and a human-scored
  holdout the gate never trains on. Until that pipeline exists, expect
  general-model accuracy (the source's general-model judge scores F1
  0.67; its headline 0.918 is a fine-tuning result on a 120-row test set,
  and its "false alarm" is defined as 1 minus precision).
- **Grade delivery in two stages.** First the target: was this the right
  thing to surface, scored against a locally written per-domain example
  bank; the published rubric lives in its examples, and its four-line
  prompt alone does not reproduce it. Then the delivery: start at 10 and
  deduct 2 to 4 per failed criterion across five (goal progression,
  personalisation, proactive tone, brevity, no metadata leakage).
- **Graduate the action.** Silent log, then digest, then direct message.
  Escalation is a cost decision, made by the gate.
- **Log the feedback.** Accepted, dismissed, snoozed, followed through,
  and the long-term signal of the lane being disabled. Adapt each lane's
  per-context threshold from that log before attempting any learned
  policy.

- **Round 4 (2026-11-01): record-only mode with a would-accept
  ledger.** An unasked lane starts in `observe`: when it infers it would
  act, it does not act; it records a `would_accept` entry (lane, trigger,
  priced cost) and stays silent. Promotion to `auto` is a human
  configuration change, confined to named narrow rules, never a lane's
  own decision. This is the mechanism this discipline's pricing lacked.
  Source: deepseek-ai/dsh-superagent-prototype at commit 6337fc8, `src/policy.ts:84` (mode defaults to `observe`) and
  `src/policy.ts:57` (inferred accept downgraded to `would_accept`).
- **Round 4: host-validated assessment shape.** Any judgement that can
  start work is schema-checked by the host, not trusted as prose: every
  enabled rule is judged exactly once, an accept requires at least one
  matched rule plus non-empty recorded evidence, and an incomplete
  assessment is refused. A judge that can silently skip a rule is not a
  gate. Source: deepseek-ai/dsh-superagent-prototype at commit 6337fc8, `src/policy.ts:40-60`.
- **Round 4: structured single-question attention.** Asking for human
  attention carries exactly one open question in one field; a reply is
  accepted only when it matches the current open question exactly, so a
  stale question cannot be answered by accident. Source: deepseek-ai/dsh-superagent-prototype at commit 6337fc8,
  `src/app/tools/executor.ts:80-81` and `src/core/replies.ts:75-77`.

*Why:* ungated proactivity measurably degenerates to about half false
alarms, and the ultimate negative reward is the user switching proactivity
off entirely. Pricing converts restraint from a personality trait into a
scored, self-tuning system. The first version of this discipline described
the source pilot as a ready-made threshold gate; the artifact contains no
threshold at all. It is an evaluation scorer. The gate half is designed
here, deliberately, and the correction is recorded in the changelog.
Sources: tao-hpu/awesome-proactive-agents (the pilot scorer),
thunlp/ProactiveAgent (sensing, the judge prompt shape, the labelling
pipeline), liutj9/ProactiveEval (the two-stage rubric; rubric adopted,
code not), and the calibrated-threshold gate design cited inside the list
(PRISM).

*Standing after the third pass: QUALIFIED, with the warned component
above. Three independent 2026 papers in the survey list converge on
the same cheap-gate / expensive-actor shape, and a practitioner
product's deterministic script-watchers corroborate the deterministic
variant. But the reward model's headline numbers could not be
reproduced from the published recipe by an independent trainer
(per-category 0.54 to 0.74 against the paper's figures, the thread
closed unexplained): no lane may budget for the fine-tuned figure,
and the gate needs a local holdout before any lane relies on it.*

### 2. Keep instincts: a confidence-scored procedural memory

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** corrections, error resolutions, and repeated workflows are raw
material, not noise. Distil them into atomic trigger-to-action units
("instincts"), each with a domain tag, evidence links, and a confidence
score earned on a stated table, and let behaviour change only as
confidence earns it.

- Extract on a schedule (nightly, beside memory synthesis) with a cheap
  observer pass, never in the hot path. The source system ships disabled
  by default; enabling extraction is a deliberate act, not an accident of
  installation.
- The capture layer is part of the spec, not plumbing: dual secret
  redaction, anti-self-observation layers (the observer must not observe
  itself), truncation, rotation, and purge. Project identity is a
  credential-stripped, normalised remote hash, with worktrees collapsed
  into their project and legacy layouts migrated, never guessed.
- The extraction prompt is the real artifact: observations are marked as
  untrusted data, and the pass ends on an exact-final-line completion
  contract; the run is archived only on verified completion.
- Confidence is earned by count on the observation path: 3 to 5
  observations, 0.5; 6 to 10, 0.7; 11 or more, 0.85, which is the cap.
  Higher, to 0.9, comes only from a stronger source, such as direct
  analysis of the work itself. Adjustments over time (reward, penalty,
  weekly decay) exist in the source as instructions to the extracting
  model, not as enforced code; treat them as recorded judgement calls,
  not as mechanism.
- Scope defaults to the narrower bucket at every decision point. Promote
  an instinct to global on cross-context repetition (two or more
  contexts) plus average confidence of at least 0.8. The source's
  documentation names a third promotion condition its own CLI does not
  enforce; code wins, and this discipline follows the code.
- Session-start injection is a local design decision, openly. The source
  ships no injection mechanism, no ranking, and no budget; the first
  version of this discipline cited a field-tested injection parameter
  that does not exist. Design selection, ranking, and a hard budget cap
  here, and record the choice and its rationale (discipline 11).
- When a cluster of mature instincts covers one procedure, cluster by
  overlap rather than loose similarity, and propose the cluster as a
  skill draft. A human gates promotion; nothing self-installs.
- Pending instincts carry a 30-day TTL. Instincts accepted from any
  external source pass import hardening first: SSRF check, size cap,
  system-path blocklist, inherited-only landing.
- Storage stays in the one memory of record. No second store, ever.

*Why:* long-term memory in most stacks holds facts; the procedural layer,
what to *do* differently next time, is the type that compounds. Confidence
scoring keeps half-formed lessons from steering real work. Source:
affaan-m/ECC, its continuous-learning-v2 skill (build spec adopted
natively, corrected at artifact level on the second pass; the framework
itself not installed).

*Standing after the third pass: QUALIFIED. Session-start injection is
still unbuilt upstream; it exists only as an open, unmerged proposal
for tool-use enforcement, and the observer's event scoping carries
live bugs under active repair, so the capture layer above is a design
to harden, not a reference implementation to trust. A major framework
independently shipping procedural memory as a first-class type
confirms the direction, with a boundary warning: that framework
updates procedural memory by automatic prompt rewriting with no
scored evidence gate. The landed form keeps promotion human-gated and
must not drift toward the automatic form.*

### 3. Audit the gates for false greens

**Ship status (2026-11-02):** mechanism-shipped, as the installable skills `skills/gate-test-integrity/` and `skills/hermetic-test-isolation/`, which carry the gate-audit and test-isolation procedures. Host-side mutation harnesses and fuzz runners specified under this discipline remain specification-only.

**Rule:** a passing test is a claim, and claims need independent expected
values. Periodically audit gate-wired tests with a six-judgement protocol:

| # | Judgement: does the test... |
|---|---|
| J1 | borrow its expected value from the code under test? |
| J2 | assert a mock's output back to itself? |
| J3 | contain assertions at all? |
| J4 | exercise the behaviour, or only the wiring? |
| J5 | cover the failure it was written to block? |
| J6 | fail when the guarded defect is reintroduced? |

- Run the audit as a periodic inspection step, not a per-commit gate.
- Review every finding by hand; model judgement errs both ways.
- Fix a confirmed false green so the test asserts an independently
  computed expected value.
- Before trusting the audit itself, prove it catches at least one known
  bad mutation. An auditor that has never failed anything is unverified.
- **Close every fix with the F7 contract.** A strengthened test is
  accepted only when it passes on a clean replica and fails on a mutated
  replica that reintroduces the bug class. Every other combination
  rejects the fix, and a test that fails both ways is itself a J6
  finding.
- **Author new gate tests oracle-first (Mode B).** Elicit the independent
  oracle, capture a language-neutral spec, generate the test, then run
  the six judgements on the generated test until clean. Unchecked
  generated output is labelled FAILED or UNVERIFIED, never presented as
  verified.
> **Warning: do not run the source's Mode C executor as shipped.**
> The F7 contract stands, but the shipped `fix` executor runs
> model-generated tests with the full ambient process environment
> inherited, credentials included, with absolute-path writes and open
> network. The defect is self-disclosed in the source's own tracker
> and unfixed. Mode C may only be adopted behind an environment
> allowlist and a jailed working directory, or with a locally
> controlled executor.

- **Name the Break before writing the test:** state the production change
  that would make this test fail. If you cannot name one, the test is
  wrong. Exercise the real thing; never mock the behaviour under test.
- **Keep the audit precise.** Severity is a ceiling, and classifying
  intent can only lower it. The gravest finding class stands only with a
  cited independent oracle plus a failed adversarial refutation.
- **Two named risks in model-era suites:** S14, a recorded model output
  used as the oracle; S21, a live self-judging model used as the oracle.
  Both manufacture agreement. Both are findings on sight.
- **The semantic codes are unproven until each carries a firing
  example and a look-alike.** By the author's own filed issue, 19 of
  the 24 semantic (S-series) codes ship with neither, and the
  S-series load path was silently broken for two releases for exactly
  this reason. The structural codes and the J-protocol stand; S-code
  detection, S14 and S21 included, is a hypothesis until then. Hence
  the general rule for any audit catalog: every code ships with one
  firing example and one look-alike, gate-checked.
- **Oracle staleness is a named false-green class.** A test whose
  traced specification changed since it was written is suspect even
  while green; pair the audit with a spec-change check.
- **Per fix, the cheap form of F7:** revert the fix, confirm the test
  goes red, restore. Mechanical, and it proves the fail direction on the
  actual change.

*Why:* the blocker law proves tests pass on fixed code. Nothing in it
proves they would fail on broken code. One false-green blocker silently
un-guards a past bug. This extends the regression-blocker law; it does not
replace it. Sources: vinicq/falsegreen-skill (the J1 to J6 protocol, the
full 125-code catalog, the authoring and fix modes, and the F7 contract,
all in the one repo; the one code adoption in this set, reviewed before
use; Mode C's shipped executor is not adopted, see the warning above), obra/superpowers (Name the Break), RooAGI/red-green-proof (the
revert-proof as a named step).

*Standing after the third pass: QUALIFIED, with one warned component
(the Mode C executor, above). The source repo's own release gate,
planted-defect probes at 9 of 9 detection parity, independently
confirms the mutation-first half of this discipline, and the vendor
layer confirms its premise: official eval doctrine grades outcomes
over transcripts and treats removing or editing tests as
unacceptable.*

### 4. Run memory as a profile plus a graph

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** split memory into a small static profile and a dynamic recent
layer, type every relationship between facts, and govern how facts enter,
age, and leave.

- The static profile holds standing facts and preferences that must colour
  every answer. It is always loaded, kept small (the source caps its
  always-on profile at 8 static plus 8 dynamic facts), and maintained
  separately from recent context, which stays search-led.
- Partition by topic as well as by age. Buckets (preferences, goals, work)
  are a third axis, independent of the longevity split, add-only at
  namespace level, with bucket descriptions steering classification.
- Label every supersession in synthesis with exactly one edge type:
  **updates** (replaces), **extends** (adds to), or **derives** (inferred,
  not stated). Derived facts are marked inferred wherever they surface.
  Record supersession bi-temporally: true-from, true-until, and
  learned-on, not just the edge label; when a fact stopped being true and
  when the memory learned it are different facts.
- Specify extraction; do not improvise it. The adopted spec is evidence-
  bound, echo- and contamination-aware, transition-preserving, and
  date-grounded against an observation date distinct from today; entries
  are self-contained at 15 to 80 words with proper nouns preserved.
  Existing memories are shown to the extractor integer-remapped, never by
  real ID; success is reported only on store confirmation; loud failure
  is distinguished from normal emptiness. If hybrid ranking is built, the
  published fusion is the spec: semantic-gated additive scoring, sigmoid
  BM25 with length-adaptive parameters, an entity boost capped at 0.5 and
  penalised for hubs, and 4x over-fetch to 60. Copy the extraction prompt
  by its constant name (V3): the same source file ships a legacy
  ADD/UPDATE/DELETE/NONE prompt, and copying "the prompt" unnamed copies
  the wrong generation half the time.
- Derived facts wait for review. An inferred fact carries its inference
  flag until a human approves it (flag cleared), declines it (fact
  forgotten), or undoes it. The review queue is ranked by support count,
  so the most-relied-on inferences are judged first.
- **Audit the stored corpus for junk, on a schedule.** Extraction at
  volume rots. A production audit of one unreviewed ADD-only
  accumulation (10,134 entries after 32 days) found 97.8% junk; of
  the 224 survivors only 38 were clean enough to keep as-is, and one
  failure cluster was 668 copies of a single feedback-loop
  hallucination, the agent re-extracting its own prior output. The
  review queue above is therefore load-bearing, not a refinement.
  The audit method: hash dedup, near-duplicate clustering, a full
  read of survivors, classification as clean / duplicate /
  hallucinated / malformed / feedback-loop, and the junk rate
  reported.
- **Interim, until write-time supersession fully lands: present
  memories date-ordered.** A controlled result moved a
  knowledge-update set from 59/76 to 68/76 by date-sorting the same
  memories before answering, with no deletion or rewrite. Cheap, and
  it mitigates the stale-fact failure the shipped fusion formula
  (which has no temporal term) cannot.
- Forgetting is four contracts, not one mechanism: forget-by-ID (check
  the per-ID result; a success response does not prove every ID changed);
  semantic forget-matching (a dry-run is mandatory, and the delete is
  bound to the previewed IDs, because re-running the match drifts);
  decline-as-forget (above); and time expiry for temporary facts, which
  the maintenance pass actively applies. Outranking is not forgetting.
  The source publishes no expiry algorithm or TTL curve; these contracts
  are what can be adopted, and they are enough.
- Keep a small fixed evaluation set for memory itself (knowledge-update,
  temporal, and preference questions) and run it against synthesis output,
  so recall regressions are detected, not anecdoted. Score the pipeline's
  operations separately, not only end-to-end answers: extraction
  precision and false-memory rate, and update correct / hallucination /
  omission rates. A benchmark scoring exactly these three operations
  exists (MemTensor/HaluMem) and is the shape to copy.

- Per-item control: a memory can opt out of the search index and
  select which of its fields are indexed. Privacy and noise control
  live at item level, not only at store level.

*Why:* search-led recall fails precisely on standing preferences, which
are rarely semantically similar to the query that needs them. Typed edges
make contradiction handling and provenance audits mechanical. Sources:
supermemoryai/supermemory (profile split, buckets, edge types, review
queue, forgetting contracts; mechanisms adopted, hosted product not, and
its extraction engine is closed, so only its published contracts are
adopted), mem0ai/mem0 (the V3 extraction spec and fusion formula, named by
constant), getzep/graphiti (bi-temporal validity windows).

*Standing after the third pass: WARNED. Production reports contradict
three properties this discipline's sources describe as specifications:
success is not store-confirmed only (partial embedding failures drop
silently; a neighbouring false-success path was real enough to be
release-noted as fixed); the shipped fusion formula has no temporal
term, so contradiction-resolving retrieval cannot be assumed and
stale facts surface; and extraction at volume rots (the junk audit
above). The source vendor's own shipped build also currently
violates its expiry contract and silently writes non-ASCII memories
that can never be searched. None of this weakens the adopted designs
(the integrity block, the review queue, bi-temporal supersession);
it shows they are load-bearing, and that no behaviour may be assumed
from "the source does it this way": every adopted property needs its
own local test. By contrast, the official layer confirms the
sophistication here is not duplicated upstream: the vendor's shipped
memory is plain client-side file CRUD, and the official MCP
reference memory server has no supersession, provenance, or temporal
validity at all. The benchmark evidence behind this discipline is
also downgraded: LoCoMo ranks are retired as supporting evidence (an
independent audit finds 99 of its 1,540 questions, 6.4%, with wrong
golden answers), and one source's "#1 on three benchmarks" claim
reduces to a single published Recall@15 figure.*

### 5. Make recall honest and maintenance governed

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** a memory lookup reports what it actually found, and a deletion
is not done until every derived copy is clean.

- Search results carry an explicit tier: **supported** (a real match),
  **closest-only** (at most 3 related previews of 240 characters, over a
  stated related bar; not claimed relevant), or **not present**. A
  nonsense query gets its own bar and its own answer. Never build on a
  closest-only result as if it were supported. Distinguish "warming up"
  (index incomplete) from "empty", and degraded from abstaining: a
  degraded index still answers, with tiers labelled; abstention is
  reserved for when the record itself cannot be read.
- Injected context declares its own omissions. When context is
  injected under a budget, the injection states what was left out, so
  a truncated picture is never mistaken for a complete one.
- Corrections are a reviewed two-phase lifecycle, never a silent replace.
  A correction creates an immutable successor plus a profile-scoped
  proposed case; the predecessor stays current until a reviewer applies
  the case against its expected version. Recall excludes unapplied
  successors, admission is enforced twice (before fusion and after
  expansion), and if the lifecycle record cannot be read, recall fails
  closed and abstains.
- **Unchecked is not rejected.** A candidate a deadline left
  unexamined stays unchecked: it never enters the accepted set, and
  a state counts as explored only after its evidence is accepted, so
  one failed attempt cannot suppress a later valid path.
- Maintenance is layered. Enrichment passes are addition-only. Zone
  movement (active, warm, cold, archived, driven by decay) is autonomous
  but bounded and protection-gated: maintenance never archives a memory
  that is in use. Corrections are never machine-applied. Erasure is a
  dedicated workflow, never a maintenance side effect. Every maintenance
  fix is reversible.
- Migration fixtures gate any memory-store migration: fixtures seeded
  with real prior-format data must remain retrievable after the
  upgrade. An emergency patch whose upgrade silently wiped search
  vectors is the cautionary case.
- Forgetting follows a completion definition: summaries, caches, indexes,
  and derived syntheses are cleaned too; the erasure writes a receipt and
  a projection tombstone, so downstream copies can prove the deletion
  reached them; corrections are undoable.
- Under load, wait bounded, then refuse explicitly. A memory service that
  cannot answer within its bound returns a retryable refusal, never a
  degraded guess presented as an answer.
- Session lessons cross into permanent memory through a named, auditable
  promotion step, and only accepted lessons cross. Nothing drifts from
  working memory into the permanent record by accumulation.
- Measure the tier boundary. Keep a small held-out set of known-answer
  recall probes, score whether the returned tier matches the known
  answer, and review the calibration monthly. A tier system nobody
  measures is a labelling ritual.
- **Gate recall depth on confidence.** A cheap first recall scores
  its own confidence: above 0.8, return directly; below 0.5, spend a
  bounded number of deeper exploration rounds (default exactly 1);
  short queries are exempt from the analysis. If a composite score is
  needed, start from the simple shipped weighting (semantic 0.5,
  recency 0.3 with a 30-day half-life, importance 0.2,
  consolidation-on-save at 0.85 similarity) and justify added
  complexity, including discipline 4's fuller fusion, against
  measured need rather than adopting it as the baseline.
- Edit memory by principles, not by accreting narrow rules: provenance
  lives in the commit, not the file; a contrastive example teaches more
  than an added rule; store analysis, not logs; after every add, trace
  the index to confirm the new entry is reachable; and place each item by
  test (core, deferred, skill, or do not store). Reference sizing from
  the source's current generation: 20,000 characters per file, 65,536
  total core. Those limits describe the current letta-code generation
  only: the V1 server line deprecated and removed block-limit
  enforcement in its 0.16.7 release, so they must not be cited as
  enforced V1 behaviour.

*Why:* this is Route Failure ≠ Task Impossibility applied to memory: a
failed lookup proves the lookup failed, not that the fact does not exist,
and no claim of absence may rest on it. The erasure standard matches
proof-before-GREEN: done means demonstrated, in every copy. Sources:
qualixar/superlocalmemory (recall tiers with their constants, the
correction lifecycle, the erasure completion definition; ideas adopted,
code not, on licence grounds), michielhdoteth/squish-memory (calibration
measurement), topoteretes/cognee (the session-to-permanent promotion
gate), letta-ai/letta in its current letta-code generation (editing
doctrine and reference sizing).

*Standing after the third pass: CONFIRMED, by counterexample. A
production delete-all cleaned memories and entity records but never
touched the raw-message store, so deleted content was fed back to
the model and re-extracted: exactly the derived-copy failure the
receipt and tombstone design exists to prevent. A
silent-non-indexing report is the write-then-unrecallable failure
tiered recall exists to surface. One caution attaches at the
margins: a stored profile's hard part is downstream application, not
recall accuracy, so a recall-only eval overstates profile quality.*

### 6. Test skills the way blockers test code

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** a playbook that has never been pressure-tested is a draft, and
its guidance must be written in the form its failures take.

- **Match the form to the failure** before writing anything:

  | Baseline failure | Right form | Wrong form |
  |---|---|---|
  | Skips or violates a rule under pressure | Prohibition + rationalization table + red flags | Soft guidance ("prefer...", "consider...") |
  | Complies, but the output has the wrong shape | Positive recipe or contract: state what the output is, its parts, in order | Prohibition list ("don't restate", "never narrate") |
  | Omits a required element | A required structural slot in the template being filled | Prose reminders near the template |
  | Behaviour depends on a condition | A conditional keyed to an observable predicate | Unconditional rule + exemption clauses |

- **Two prohibitions on the prohibitions.** No nuance clauses: "don't X
  unless it matters" reopens the negotiation, and one nuance clause
  degraded a winning recipe from consistent to noisy in the source's own
  wording tests. Express a real exception as its own conditional.
  Exemption clauses do not scope: "this limit doesn't apply to code
  blocks" still suppresses code blocks. If part of the output must be
  exempt, restructure so the rule cannot reach it.
- **Micro-test the wording before the full pressure run:** one
  fresh-context sample per call inside the realistic system context,
  always with a no-guidance control (if the control shows no failure,
  there is nothing to fix; stop), five or more reps per variant, every
  flagged match read by hand, and variance treated as a metric. Five
  different interpretations across five reps means the wording is not
  binding; tighten the form before adding words. Micro-tests verify
  wording; they do not replace pressure scenarios.
- **Gate skill changes on planted defects.** Before a revised skill
  ships, run it against tasks with known planted defects and require
  detection parity with the prior version. The false-green source
  repo runs exactly this gate on its own releases (9 of 9 detection
  parity); a detection regression blocks the ship the way a failing
  eval does (discipline 7).
- For any new or materially revised high-stakes skill, run pressure
  scenarios with subagents *without* the skill and record the exact
  rationalizations used to break the rule. Write the minimal skill
  against those specific violations, re-test, and plug new loopholes as
  they appear.
- Add Thought/Reality rationalization tables to the highest-stakes
  playbooks: the excuse in one column, the fact in the other. Tables are
  the discipline-failure form; the first row of the table above decides
  where they belong.
- Skill descriptions state triggers and the negative boundary only,
  and are written assertively. Models systematically undertrigger,
  so a merely accurate description under-fires; all trigger context
  belongs in the description itself. (The second pass read this rule
  as triggers-only minimalism; the vendor's own guidance is pushier,
  and this text now matches it.) A description that summarises the
  workflow gets skipped or mis-triggered; lint the library against
  this standard periodically. One structural limit: a one-step task
  may never trigger a skill however good the description is, so
  skills wrapping one-step jobs are structurally unreliable and must
  not be gated as if triggering were under the author's control.
- **Test descriptions at vendor numbers.** Build a balanced 20-query
  trigger set (should-trigger plus near-miss should-not), split
  60/40 train/validation, select the wording on the validation score,
  and benchmark with-skill against without-skill in fresh subagents.
  (Wording corrected 2026-11-02: the set that selects the wording is
  validation data, whatever it is called; see the untouched-final-test
  rule below.)
- **Untouched final test (2026-11-02).** Any set used to select a
  wording, revise it, or feed failure feedback into the next revision
  is selection data. A change selected on such a set must also reserve
  a final test set that is never used for selection, revision, or
  feedback, and is run once, at the end, to report the result. A score
  from a selecting set is reported as a validation score, never as a
  final test score. This applies to skill wording, trigger evals, and
  doctrine changes alike, including this skill's own eval cases.
  The second pass supplied the method without these numbers; they
  are the vendor skill-creator's shipped defaults.
- Improve playbooks by generation and selection: produce candidate
  wordings, score them on fixed examples, keep the winner. Offload
  deterministic work to code rather than asking the model to simulate it,
  and decompose multi-step work into chained steps with inspectable
  joins; these are the prompting practices that survived evidence grading
  in the source guides.
- Run that improvement as a loop with named roles: an Executor runs
  the skill, an Analyst grades the run against binary criteria, a
  Mutator makes exactly one surgical change per round (add_example,
  add_constraint, restructure, add_edge_case), kept if better,
  reverted if worse. One mutation per round is what makes the
  keep/revert verdict attributable.
- Price the ceremony. The source pipeline's cost is its top user
  complaint (context overhead; a simple plan consuming a full token
  budget). The heavier forms in this discipline carry an explicit
  cost budget, or users will disable them rather than obey them.
- Keep a session-diagnosis pass available, run as a forensic protocol,
  not a chat about the session: case-file intake, a fixed set of report
  dimensions, and a citation-or-discard rule (every finding cites file
  and line; no citation, no finding). It ends in an involvement verdict
  and is forbidden from proposing fixes; repair is a separate act.
- Adopt the source corpus's tested methods, not its current texts
  wholesale: the corpus violates its own description rules in places, and
  its texts will drift again. Re-derive wording locally, and re-check at
  adoption time.

*Why:* skills fail silently, by being skipped or fired on the wrong task,
and nothing downstream notices. Pressure-testing is the only inspected
method that tests a skill the way a blocker tests code. The second pass
qualifies the first version of this discipline, which adopted
rationalization tables unqualified: the prohibition form is correct for
one failure type in four and measurably backfires on the other three,
producing more of the unwanted content than a no-guidance control in the
source's wording tests. Sources: obra/superpowers (writing-skills,
including the form table and micro-testing; verification-before-
completion; the diagnosing protocol), findscripter/everything-skills
(the description rule), dair-ai/Prompt-Engineering-Guide (the surviving
practices, as provenance).

*Standing after the third pass: QUALIFIED, and confirmed in
strengthened form from three directions: the source corpus's
maintainer ran the micro-testing method in public on a real
form-matching failure (a fixed opener template applied regardless of
context), reproduced the failures at 6 of 6 and 24 of 24 runs,
changed the form, and shipped the retune; the platform vendor's own
skill-creator independently prescribes the same run-eval-rewrite loop
and a separate description-triggering optimisation pass; an unrelated
extraction kept the same four domain-neutral skills. The
qualification is the narrowed description rule above.*

### 7. Gate what enters the library, and grade reliability

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** third-party skills, plugins, and connectors are untrusted input
until scanned, and a revised playbook ships only after it passes its eval
set.

- Every important skill carries a small fixed eval set (inputs, expected
  properties, a rubric grader) run before a revision ships. Regressions
  block the ship. Define the evals before the code they grade.
- **Selection data is not test data (2026-11-02).** Where an eval set
  is used to select or revise what ships, the ship decision also
  reports the untouched final test from discipline 6, run once at the
  end. A set that picked the winner cannot also certify it.
- Every eval set carries a reference solution proving the task is
  solvable, balanced should/should-not cases, and isolated trials so
  prior-trial artifacts cannot leak. Model judges get an explicit
  "Unknown" exit. A 0% pass rate across many trials is treated first
  as a broken-task signal, not a model failure.
- Grade agent reliability across skill or doctrine changes with pass@k
  (can it succeed) and pass^k (does it succeed every time), against
  declared thresholds: capability pass@3 of at least 0.90; regression
  pass^k of 1.00 on release-critical paths. The second number is the one
  that matters for trusted work.
- Record consequential actions as evidence capsules. Every recorded
  action declares an effect class: SE0 read-only evaluation; SE1
  reversible local writes; SE2 process or filesystem mutation; SE3
  append-only remote publication, never replayed; SE4 economic or
  secret-handling effects, never replayed, and forbidden in record mode
  unless a trusted caller allows. Capsules are append-only and
  hash-chained; verification fails at the exact entry, with stable codes.
- Replay fails closed. Each tool declares its determinism and effect
  class; fixtures are content-addressed; a missing fixture fails the
  replay rather than improvising; SE3 and above are refused in replay.
  Receipts are verifiable offline by a party that does not trust the
  producer. Held-out tasks and a named reward-hack variant belong in the
  example set from the start.
- Never present evidence as stronger than it is. A receipt is not
  containment; a static warning is not a run. The source harness executes
  no candidates on any platform and says so in its own receipts; match
  that refusal posture, and do not claim promotion evidence the mechanism
  cannot produce.
- Every reported metric distinguishes measured-this-run from
  replayed. A headline metric that silently replays a prior run's
  cached measurement overstates what was observed.
- Audit the configuration surface against a concrete checklist: secrets
  (10 rules over a 25-pattern table), permissions (17), hooks (40), MCP
  configuration (49 across four modules), and prompt-defense posture:
  one rule carrying twelve OWASP-mapped checks for missing defences in
  instruction files, the single highest-value item for a stack whose
  control surface is largely prompt and skill text. The full taxonomy is
  268 rules in 15 modules; mirror it selectively, by name.
- Prefer structural parsing over pattern lists for command rules. A
  production bypass of a regex-based destructive-command rule at an
  operand seam, inside the audit vendor's own sibling product, is
  the standing warning; every regex rule carries a seam-case
  regression set.
- Score the audit honestly: per category first (each bucket starts at
  100, floored at 0; the overall score is their plain average, so one
  catastrophic category costs at most 20 points), deductions weighted by
  runtime confidence from 0.25x for template and documentation examples
  to 1.0x for active runtime, except secrets, which always score at full
  weight. Template-inventory deductions are capped per category-file.
  Recognised defences are listed in every report and never raise the
  score.
- For high-stakes audits, run the deep shape: red team, blue team, and
  auditor as three structured-output perspectives under a fixed auditor
  contract. Keep an injection corpus as a CI gate (the source ships 70
  payloads in 12 categories). Record the audit's own limits with it: it
  reads configuration text, not live connections; skill-file prompt text
  is under-covered; baseline fingerprints break on line shifts.
- Anything third-party entering the library gets a scan first, scored on
  the published rubric shape (HCS-28: adapter weights across review
  status, publisher binding, commit and manifest integrity, domain
  proof, metadata quality, taxonomy, provenance, and conditional health
  and scanner signals), with two aggregation rules copied exactly: a
  missing universal component scores 0, so an unscanned item is
  penalised, not excused; and conditional components enter the
  denominator only when they emit scores. A scanner configuration that
  lives in the repository being scanned takes effect only under an
  explicit trust flag; nothing grades itself. The score attaches to the
  item's library entry; "unreviewed" is the honest default state.
- Guard the third boundary: the commit. Public writes and adoption-time
  scans have gates; add a staged-lines scan at commit time. Agents may
  not pass the flag that disables the guard, and its
  infrastructure-failure mode is a named, documented setting, not a
  silent pass.
- Closure claims are mechanically checked. No issue or defect is
  closed citing a pull request or a release without a mechanical
  check that the PR merged or the release exists. A verified
  contributor audit of one source repo found closures citing
  unmerged PRs and a release that did not exist at the time;
  evidence discipline covers tracker and closure claims, not only
  eval artifacts.
- Unchecked is not rejected here either: candidates a deadline left
  unexamined never enter the accepted cache, and a state is marked
  explored only after its evidence is accepted (the same rule as
  discipline 5, applied to the library and its gates).
- Periodically grade a sample of real deliverables (research, reports)
  the way a trading record is graded, not just the code artifacts.
- Keep the self-audit instruments, with the local design work done first:
  a five-queue checklist and an improve queue that is never allowed to be
  empty; a failure taxonomy whose repair mapping is completed locally
  (the source names 13 classes and only 8 repairs; missing permission,
  context overload, poor model routing, and bad human requirements have
  none); and the operating ratios (memory reuse, proactive versus
  reactive share, intervention rate, repeat-run stability) adopted only
  together with locally written counting definitions, because the source
  names them and defines none of them.

- **Every directory self-describes at two compression levels.** A
  generated one-sentence abstract (L0), then an overview (L1), read
  before full content (L2). Index discipline generalises from
  "maintain a root index" to "every directory self-describes",
  across the library and the memory store alike.
- Report eval and benchmark results as deltas: same harness, native
  versus augmented, models named, reproduction scripts kept with
  the results. A bare score without its harness is marketing.
- Tool descriptions are eval-tested artifacts, like skill
  descriptions (discipline 6), including measured namespacing
  choices.
- A release gate must live in files you own. Hosted eval definitions
  are not fully exportable, so a gate defined only inside a hosted
  tool is a gate you do not hold.
- Derived per-person representations carry explicit observed-by /
  knows-about scoping: what a representation may claim is bounded
  by who observed it and what it is about.

*Why:* the blocker law covers code. The configuration surface (skills,
hooks, connector configs, permissions) is where an agent can be quietly
rewired, and it had no gate. Sources: promptfoo/promptfoo (declarative
eval shape), openai/plugins (plugin-eval), affaan-m/ECC (the eval
harness and its evidence layer), affaan-m/agentshield (the audit
taxonomy and scoring honesty), hashgraph-online/hol-guard (the HCS-28
scan rubric), JeongJaeSoon/agent-guard (the commit-boundary guard),
fainir/most-capable-agent-system-prompt (the self-audit instruments,
completed locally), volcengine/OpenViking (directory
self-description and delta-style reporting; product not adopted),
plastic-labs/honcho (perspective scoping; service not adopted).
Patterns adopted; tools not installed this pass.

*Standing after the third pass: QUALIFIED, confirmed from four
directions: neither the Agent Skills specification, its validator,
nor the official MCP Registry carries any safety, provenance, or
vetting signal, so scan-before-list fills a gap the official layer
leaves open rather than duplicating it; the two largest community
skill collections ship at scale with no scan or eval evidence; a
third independent implementation of commit-boundary gating exists in
a widely starred fork. The qualifications are the process-level ones
landed above: tracker and closure hygiene, and
measured-versus-replayed provenance.*

### 8. Mechanise the completion claim

**Ship status (2026-11-02):** mechanism-shipped, as the installable skill `skills/proof-before-green/` (with `skills/claim-verification-ledger/`), which ships the agent-side proof procedure. The blocking completion gate and the stop hook also specified under this discipline are specification-only; no host gate ships in this package.

**Rule:** convert proof-before-GREEN from a habit into a mechanism that
fires when the habit slips.

- A completion claim with no evidence produced *in this message* (test
  result, exit code, command output, read-back) is blocked once and
  downgraded to UNVERIFIED, never looped. Satisfaction words are claims
  too. An agent's report that something succeeded is not evidence; the
  diff, the output, and the read-back are.
- Scope bounds the deliverable, not the verification. The full check runs
  even when the task named one file, and any failure it shows, including
  one this change did not cause, is named in the report. A red result
  scrolled past and unmentioned makes the report false by omission.
- Long-running work keeps an authoritative requirements file (the SCOPE,
  in file form) that is re-injected on compaction or resume. Completion
  claims are validated against the recorded evidence log, not against
  whatever context survived; after compaction, the ledger and the commit
  log outrank recollection.
- **Capture evidence runner-aware.** The automated evidence field
  records a named pass/fail token emitted by the runner, never "the
  last log line": the source's per-plan ledger script records the
  last non-blank log line as the test result and has ledgered a
  duration line as an outcome. A duration is not a result. State
  the plan list in JSON with only the status field editable; models
  overwrite JSON less inappropriately than Markdown.
- The mechanism checks that evidence exists. Whether the evidence
  supports the claim remains a judgement, and review mode still applies.
- **Enforcement honesty (2026-11-02).** The enforcement mechanisms
  this repository actually ships check wording, not truth. The stop
  hook pattern-matches a STATUS label and nothing after it; a bare
  label with no evidence passes it. The README prompt checker tests a
  fixed, hardcoded phrase list and never opens SKILL.md, so it passes
  even if the skill's rules have moved on. Both are floors, not
  verification, and no report may cite a hook or checker pass as
  evidence for a claim. Specification for any conforming
  implementation: a STATUS check counts a reply as complete only when
  the label is followed by an evidence pointer (the artifact, file,
  command output, or read-back behind the claim), and a prompt
  checker either derives its required phrases from SKILL.md at run
  time or is documented, in its own output, as a fixed-list floor
  check.
- **Enforce user-thrown gates mechanically.** At plan authoring,
  tag any task whose brief contains gate language, under a strict
  definition: user gates, agent gates, and the grey zone are all
  tagged; over-tag and let the execution hook filter, rather than
  interrogating mid-plan. At task close, require evidence in a named
  form per criterion; where the verification method itself is
  unspecified, run a specify-the-HOW protocol at close time
  (observable outcome, proof mechanism, scope, failure policy)
  instead of letting the agent invent a method. The field failure
  this stops is documented by the source fork: an agent inventing a
  cheap verification method at execution time and closing the gate
  with an inline shortcut. One element of that fork is explicitly
  not carried over: its hooks fail open; local gates fail closed.
  [The blanket form of that last clause is superseded, 2026-11-02, by
  the governing statement in the next bullet.]
- **Gate failure behavior, governing statement (2026-11-02).** Two
  scopes, kept separate. (a) A gate's verdict on the work it judges
  fails closed: a local gate that cannot evaluate the work must not
  pass it. (b) The completion gate specified in the Round 5
  concretions is the one named exception at the process level: if
  that gate's own code crashes, it fails open and logs, so a broken
  gate cannot silently block all work forever, while its
  configuration errors fail closed. The earlier blanket sentence
  "local gates fail closed" is superseded in its unscoped form by
  this statement; it survives as scope (a) only.
- **Audit scope mechanically: diff against intent.** A
  standard-library-only, no-network, read-only check compares a
  finished diff against the brief's one-line stated intent and
  flags unrelated paths, new dependencies, public API renames,
  config/CI edits, oversized hunks, formatting-only files, and
  subsystem spread, emitting a keep / split / justify report.
  Discipline 3 audits tests; nothing else adopted audits scope, and
  minimum-sufficient-change otherwise rests on self-report. For
  delegated work the mapping is direct: the intent line goes in the
  brief, the scope report attaches to the handback.
- Cap the fix loop at five rounds per task. Rounds 1 to 3 resume the
  original implementer with the findings verbatim; rounds 4 to 5 dispatch
  a fresh implementer on a more capable model. Every round ends with a
  scoped re-review and one ledger line. Silent discards are forbidden.
- Adjudicate only at the cap. Conflicts and plan defects met mid-loop are
  decided and ledgered as rulings ("Ruling: what was decided, why, what
  it costs if wrong"), not treated as stalls. Only four stop conditions
  interrupt the loop: an irreversible or destructive step, a
  security-sensitive step, a side effect outside the worktree that norms
  say to ask about first, or a plan so broken every path is a guess.
- Three failed fixes is a stop, not a streak: question the architecture
  instead of attempting a fourth fix on the same hypothesis.
- At verdict points, vote before concluding: at the root-cause and
  completion moments, take 3 to 5 deliberately different starts,
  treat disagreement as strong evidence and agreement as weak, and
  deny the vote proof status. The test or the command still proves
  the answer.
- Protect the gate from the worker. Any gated workflow carries a
  `forbid:` list: paths the worker may never write because the gate reads
  them. Bounds are declared as a file (iterations, no-progress window,
  wall-clock, token budget) with a kill switch checked before every lap.
  Every gate ships a negative control: an ungated run demonstrating the
  failure the gate exists to catch. Configured is not active: an
  integration counts as installed only when a fresh session produces a
  receipt of it working. Every gate's deny
  message names the narrowest scoped disable for the specific gate
  that fired: a gate whose scoped escape knob appears in no deny
  message or documentation trains users to take the global
  off-switch, and the gate dies entirely.
- Loop guards start from stated defaults and are tuned by evidence:
  pull-based claiming every 30 seconds, a hard task timeout near 30
  minutes, delegation depth near 5, retry once, then change strategy or
  escalate.

- Scale delegation effort numerically: state the effort budget in
  the delegation prompt itself, as a number, so the delegate's
  depth is a decision rather than a mood.

*Why:* this doctrine's own history includes a fabricated completion
report. A rule an agent believes it satisfied is weaker than a check that
fires when it did not. This mechanises section 4 of the core skill; it
adds no new standard. Sources: kuroudo-ai/done-gate (the block-once
evidence check), GreenLv/codex-context-guard (requirement checklists),
obra/superpowers (the execution arithmetic, the freshness unit, the
scope-versus-verification split), qualixar/bounded-loops (declared
bounds, forbid lists, negative controls), TerminallyLazy/
tree-ring-memory-codex-plugin (configured is not active),
fainir/most-capable-agent-system-prompt (loop-guard defaults),
pcvelz/superpowers (user-thrown gate enforcement and the
specify-the-HOW protocol; its fail-open hooks not carried over),
Shubhamsaboo/awesome-llm-apps (the scope-creep detector); all
reimplemented natively, none installed.

*Standing after the third pass: QUALIFIED. An actively maintained
fork independently implements per-task evidence-at-close hooks and a
pre-commit task gate, and documents the precise circumvention the
specify-the-HOW protocol above exists to stop. The vendor's own
long-running harness (initializer/coding split, progress file,
get-bearings ritual) confirms the shape. The qualification is the
ledger defect corrected above: the format stands, its automated
capture does not.*

### 9. Treat compaction and delegation as authority boundaries

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** summaries carry context, never authority.

1. Capability is minted per turn and expires with it. Internal handles are
   never exposed to the model; tools are limited to those advertised for
   the active turn.
2. After any compaction or resume, authority is re-proven from the
   canonical record (approvals, files of record), never inherited from a
   summary. A synthesis is memory, not authorisation.
3. At the highest-risk bridges, keep a human-send boundary: the agent
   drafts, the human sends. Do not automate across a trust boundary
   because a lane exists.
4. No silent fallback identities or budgets. A mismatch is rejected
   explicitly, fail-closed.
5. Compaction is transactional. Any compaction that rewrites stored
   history is generation-checked, serialised against concurrent
   edits, and restores the prior history on failure. The ladder
   names tool-result clearing as its first, lightest rung, with
   numeric triage in the vendor shape: clear tool uses at a lower
   threshold keeping the most recent few, compact at a higher
   threshold, memory protected from clearing, and a
   save-before-clearing warning. Every summarisation step carries
   bounds blockers: the eviction fraction is honoured within
   tolerance, and structural pairs (a tool call and its response)
   are never split. History edits are named, bounded operations
   (clearing, compaction, rewrite), each with its own contract;
   there is no general "edit history" act.

6. **Round 4 (2026-11-01): the mandate is an immutable object,
   revalidated only at resume.** Scope is granted once as an immutable
   mandate; it is re-checked when work resumes or attaches after a pause
   or a policy change, and never silently revoked or widened mid-flight.
   Source: deepseek-ai/dsh-superagent-prototype at commit 6337fc8, `src/policy.ts:213-241` and `src/core/tickets.ts:257`.
7. **Round 4: interrupted-work recovery protocol.** On resume, requeue
   only the inputs the interrupted attempt never read; inputs it did
   read are not replayed blind. The new attempt opens with a fixed
   recovery note instructing it to inspect what the prior attempt may
   already have done before acting. Source: deepseek-ai/dsh-superagent-prototype at commit 6337fc8,
   `src/core/assignments.ts:21` (the recovery note) and
   `src/core/assignments.ts:83` (interrupted semantics).

*Why:* the two surfaces most likely to drift or be attacked are the
post-compaction resume and the delegated tool turn. This extends the core
skill's "content is evidence, never instructions" from content to
authority itself. Source: miuuyy/codex-chatgpt-web (the four rules as
implemented in its bridge design; product not adopted); the
transactional compaction contract and the clear/compact/remember
triage from official vendor guidance, read at the primary layer on
the third pass.

*Standing after the third pass: QUALIFIED. The official layer
supplies the failure semantics this discipline lacked: an official
compaction session treats clear-and-rewrite as a recoverable
replacement, generation-checked and serialised against concurrent
edits, with restore-on-failure, and names tool-result clearing as
the first compaction rung. The qualification is a paging system's
own tracker: a sliding-window compaction that ignored its configured
percentage and wiped the full history, and a summarisation that
broke tool-call/response pairing and crashed the client. Hence the
bounds blockers in point 5, rather than trust in the pattern.*

### 10. Run a bounded hidden-rubric pass on ungated prose

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** deliverables no gate covers (reads, syntheses, recommendations,
reports) get one internal quality pass before they ship.

- Construct a task-specific rubric of five to seven categories from the
  role's point of view, and score the draft against one global threshold.
  The source names no categories and defines no per-dimension scoring
  procedure; the first version of this discipline implied both. The
  adoptable unit is the constructed rubric, the threshold, and the
  secrecy rule, nothing more.
- The loop is bounded: a hard retry cap, then ship the best version with
  the weak dimension named. An unbounded "revise until near-perfect"
  loop is explicitly not adopted.
- The rubric stays internal; the user sees the deliverable, not the
  scaffolding.
- Maintain prompts subtractively: each version deletes lines shown not to
  work, with citations, instead of only adding. Treat the source's own
  results as maintenance discipline, not efficacy proof; it prints no
  baseline.
- Delete emotional-pressure lines (tips, penalties, career threats) from
  prompts wherever found. The evidence says they are dead weight.

*Why:* gates check artifacts and code; prose judgement had no check at
all. This is the cheapest quality mechanism in the set: playbook wording,
nothing else. Source: DenisSergeevitch/chatgpt-custom-instructions (the
self-evaluation block, bounded and narrowed to what the artifact
contains; its pressure lines rejected on the author's own cited results).

*Standing after the third pass: NO CONTACT. The third pass produced
no evidence for or against this discipline; it was not contradicted
and is not confirmed by it. Its evidence base remains exactly what
the second pass left: a narrowed adoption resting on maintenance
discipline, with no baseline printed in the source. Recorded as
untested by the pass, not upgraded to a confirmation.*

### 11. Record the why, not just the what

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** every decision that closes a path is stored with the path it
closed. A rationale entry records the decision, the rejected alternatives
and why they lost, the reason the winner won, an evidence grade, and the
trigger that should reopen it.

- Identity is a stable UUID, never a heading. Headings get reworded and
  files split; references must survive both, across repositories too.
- Required fields: Decision/behaviour; Rejected alternative(s), with why
  each lost; Reason; Type (decision / workaround / incident / constraint
  / undefined, with the reason it is undefined); Status (active /
  superseded / open / needs-review / pending-confirmation); Evidence
  (confirmed / inferred / unknown); Source; Revisit when (a concrete
  trigger); See (locator, Id, as-of date); and, on superseded entries,
  Superseded by (the successor's Id, or "none" with why nothing replaced
  it).
- Unattended capture writes the entry flagged pending-confirmation. It
  does not drop the finding, and it does not ask into the void.
- Superseded entries are never injected as current context: an
  overturned decision reads as current. (A fork implements exactly
  this rule; the third pass confirms it at the margins.)
- Keep episodic exemplars beside the rationale entries: a curated
  collection per recurring task class holding situation, approach,
  and why it worked, retrieved as few-shot exemplars at task time.
  Instincts (discipline 2) store the distilled rule; exemplars are
  their retrieval-side twin, the worked example the rule came from.
- Address reusable context by content hash. Research corpora,
  teardown bundles, and chart packs are stored once under the
  SHA256 of their content and attached to many prompts by hash,
  through an open loader namespace; the hash doubles as the
  provenance stamp this discipline's See field wants.
- Grade this memory with an experience-memory eval shape (static
  and dynamic state, workflow knowledge, environment gotchas,
  premise awareness, scored over logged trajectories). The older
  QA benchmarks cannot grade this knowledge class at all.
- Structure is enforced mechanically (an entry without an Id is an
  error, checked in the existing gate). Whether the rationale is true
  stays human judgement, and the schema says so.

*Why:* instincts (discipline 2) capture what to do differently; memory
(disciplines 4 and 5) captures what is true and what replaced it. Neither
captures why a path was rejected, which is the knowledge whose absence
makes an agent re-propose a dead design with fresh confidence. Source:
oliver-zehentleitner/keep-the-why (schema and invariants adopted
natively; the structural half of its linter folded into the existing
gate, the tool itself not imported), simonw/llm
(content-addressed fragments), the LangMem conceptual guide
(episodic exemplars), xiaowu0162/LongMemEval-V2 (the
experience-memory eval shape).

*Standing after the third pass: CONFIRMED. A peer-track benchmark
independently defines workflow knowledge, environment gotchas, and
premise awareness over logged trajectories as graded memory
abilities, which is exactly the knowledge class rationale entries
store; neither of the older QA benchmarks can grade it at all. The
vendor's lead-agent pattern of saving its plan to memory to survive
context limits is adjacent practice, a weak confirmation only.*

### 12. Keep every fact timeless, dated, or a pointer

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** every stored fact must be timeless, dated, or a pointer.
Nothing may claim to be current without a stamp.

- Timeless facts need no date and do not decay. Snapshots live inside a
  dated note or under a dated heading, and are history from then on.
  Pointers name where the truth lives, plus a last-observed value with
  its as-of date.
- The one illegal form: a present-tense claim about a fast fact (volatile
  within about 7 days: counts, balances, statuses, open items) with no
  date, outside a dated container. That is the sentence that becomes a
  lie next week while still reading as truth.
- The nightly pass checks heuristically: an unstamped quantitative
  present-tense claim about a volatile noun outside a dated container is
  an error; a stamp older than the freshness window (default 7 days) is
  a warning; a pointer must resolve.
- Refresh-on-read is a named option: a dated fact or pointer may
  refresh its stamp when read and found still true, as a declared
  store contract, never an assumed behaviour. Production systems
  ship time-to-live purely as configuration; there is no algorithm
  to copy, only contracts to state.
- Every aged line gets exactly one of three answers: re-observe it,
  convert it to a pointer, or retire it into a dated note. There is no
  fourth answer called leaving it.

*Why:* the first version of this reference governed temporary facts
through expiry, but nothing governed unstamped fast facts written as if
current, which is the commonest way a memory file silently rots. The rule
is cheap: an authoring law plus a heuristic check. Sources:
eugeniughelbur/obsidian-second-brain and its OKM freshness spec (the rule
adopted; the linter reimplemented rather than imported, as it is tuned to
its own vault), corroborated independently by ReARCLabs/bilinc
(last-confirmed stamping with a review window).

*Standing after the third pass: QUALIFIED, supported at the margins
and never directly tested. An independent fork frames stale state
as possibly stale rather than as a resume instruction; a second,
unrelated framework ships expiry purely as store configuration,
consistent with this discipline's contracts-only posture; and
operation-level update scoring (discipline 4) extends its
measurement side. No pass exercised the freshness lint or the
refresh loop itself; the discipline stands uncontradicted and
lightly evidenced.*

### 13. Gate outbound messages by purpose, receipt, and hard cap

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** a message an agent sends unasked or on a principal's behalf
leaves only through a send path that checks its purpose, records a
permanent receipt, and enforces its length cap in code.

- **Purpose-gated sends.** Each purpose has an exact condition: a result
  message requires a ready or completed outcome behind it, an attention
  message requires the exact current open question, an answer requires a
  reported answer. A send whose purpose condition is not met is refused
  at the send path, not discouraged in a prompt.
- **One acknowledgement per origin event, first text wins.** Duplicate
  acknowledgements of the same trigger are suppressed by a permanent
  receipt store that survives restarts; a re-delivered trigger finds its
  receipt and sends nothing.
- **Caps throw.** Per-surface word and length caps are constants enforced
  by a function that throws over the limit at send time; routing notes
  and short-form messages carry their own smaller caps. A style
  instruction to be brief is not a cap.

*Why:* attention discipline enforced only in prose fails exactly when
the agent is busiest. The send path is the one place every message must
pass, so it is where the gate belongs. Source: deepseek-ai/dsh-superagent-prototype at commit 6337fc8,
`src/core/replies.ts:56` (one acknowledgement, first text wins),
`src/core/replies.ts:69-82` (purpose gates), receipts in
`src/app/store.ts`, and `src/infra/text.ts:3,14` (the throwing cap;
routing-note cap at `src/app/tools/main.ts:18`).

### 14. Give every event, decision, and delivery a deterministic ID

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** identity is derived from content, not assigned by arrival
order, and deduplication is layered so the same thing cannot enter
twice under two names.

- **Deterministic content-hash IDs.** An ID is a truncated hash of the
  canonical serialisation of the item's defining parts. The same content
  re-presented produces the same ID, on any run, in any process.
- **Layered dedup.** Deduplication runs at each layer independently:
  intake (the same event presented twice), creation (the same work
  requested twice), delivery (the same message sent twice), and effects
  (the same side effect queued twice, discipline 15). One layer catching
  a duplicate does not excuse the next layer skipping its check.
- **Edits are new events by design, and say so.** Where an ID includes a
  revision stamp, an edited item is a new event; that choice is stated,
  not discovered after a double delivery.

*Why:* duplicate deliveries and duplicate records are usually cleaned up
after the fact, at the layer where they were noticed. Deriving identity
from content prevents the class at the layer where it starts. Source:
deepseek-ai/dsh-superagent-prototype at commit 6337fc8, `src/core/ids.ts:4` (deterministic IDs), `src/core/intake.ts:23`
(intake dedup), and `src/core/evals.ts:311` (ticket ID derivation).

### 15. Queue side effects durably, and never confuse waiting with failure

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** an intended side effect is a durable queue row before it is an
action, retried under a stated policy, and deleted only by the attempt
that owns its current generation.

- **Upsert by (kind, key) with a generation guard.** Re-queueing the same
  effect increments its generation; a completing attempt deletes the row
  only if its sequence and generation still match, so a stale attempt
  cannot delete a re-queued row.
- **Later is not failure.** A `Later` outcome (a dependency is not ready)
  does not increment the attempt count and is not recorded as a failure;
  only an actual failure backs off.
- **Uncapped exponential backoff for failures,** with the delay capped:
  base times two to the attempt count (bounded exponent), never a fixed
  tight retry loop and never silent abandonment after a small cap.
  [Superseded for generic failures, 2026-11-02, by the governing
  statement below and the second form in the Round 5 concretions. The
  uncapped rule survives only for rate-limit pauses.]
- **Governing retry policy (2026-11-02).** The effect queue second
  form governs. Rate-limit (429) pauses are unbounded, exponential to
  a cap, honor Retry-After past the cap, and never increment the
  attempt count. Generic failures are bounded; when the bound is
  exhausted the item lands in a named skipped list, which is a visible
  terminal state reported by name, not silent abandonment.
- **A retry must be safe to fire.** Before re-firing an effect after
  an uncertain response, the attempt carries an idempotency key the
  receiver honors, or the receiver dedupes on the effect's
  deterministic ID (discipline 14), or the attempt first reconciles by
  reading the receiver's state. An effect whose receiver offers none
  of these is at-least-once and must be designed safe under
  duplication.

*Why:* ad hoc retry loops lose effects on restart, double-fire them on
recovery, and report waiting as failure. A durable, generation-guarded
queue makes every intended effect accounted for exactly once in the
queue's own ledger: no row lost on restart, no row settled twice, no
waiting reported as failure. That is a ledger guarantee, not an
external one. After an uncertain response, where the external call
may have succeeded while its response or the queue settlement was
lost, the queue alone cannot prevent a second firing; the
idempotency, dedup, or reconciliation requirement in the rules above
is what earns a stronger claim, and without it an effect is
at-least-once. Source:
deepseek-ai/dsh-superagent-prototype at commit 6337fc8, `src/app/effects.ts:141` (backoff) and the effect-queue semantics
recorded in the teardown's execution account (upsert, generation guard,
Later distinct from failure).

### 16. Route follow-ups to their owner, and reserve slots by discipline

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

**Rule:** work that already has a live owner is routed straight to that
owner without re-triage, and concurrency is a reserved-slot discipline
that a human follow-up can always break into by exactly one.

- **Subscription pass-through.** A follow-up on owned work goes directly
  to its owner; the triage or routing layer runs only when no live owner
  exists. The router is removed from the path it adds nothing to.
- **Authorisation is not bypassed with the triage.** The pass-through
  skips re-evaluation of the work, never the sender and authorisation
  check on the message. (The source system delivers subscribed follow-ups
  with no sender check; that form is rejected, see the round-4 cautions.)
- **Slot discipline with a plus-one human slot.** Concurrent workers are
  capped by a stated limit with slots reserved synchronously before work
  starts. A principal's follow-up may exceed the limit by exactly one
  slot, so a person never queues behind new launches of their own work.

*Why:* re-triaging every follow-up taxes exactly the messages that need
the least judgement, and an uncapped fan-out starves the principal's own
next instruction. Both are routing economy, bought with mechanism rather
than hope. Source: deepseek-ai/dsh-superagent-prototype at commit 6337fc8, `src/core/intake.ts:58` (fan-out first, triage
only if unowned), `src/policy.ts:93` (worker cap), and the slot
semantics recorded in the teardown's execution account.

## Round 5 (2026-11-02): disciplines 17 and 18, and the mechanical concretions

A fifth pass read the source code (not the docs) of every repo on the
enhancement list, graded at file and line level against disciplines 1 to
16. Two mechanisms were large enough to be new disciplines; the rest are
mechanical concretions folded into the disciplines they deepen. The
synthesis record for this round is truncated at its item 43 in the local
archive; items after that point are an open row there, not silently
absent here: only what the record states is adopted below.

**Provenance note (2026-11-02).** Citations in this reference are
provenance, not re-verification. Each pass verified what it states, at
the depth it states, for the sources it names; no pass independently
rechecked every project cited anywhere in this file. Round 5's
file-and-line claim covers the named enhancement list only, and it
cannot be audited from this repository: the synthesis record it rests
on is truncated at item 43 and lives in a local archive the reader
cannot inspect. Anything the full record contained after item 43 is
absent from this doctrine for reasons of record loss, not judgment,
and stays an open row until the record is recovered.

### 17. Keep a near-miss ledger

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

Proposals that matched a gate but were not admitted are recorded in a
bounded, diagnostics-only ledger: at most 4,096 laws, 512 reported, 4
samples per law, 400 characters per text; the reason is classified into
coarse gates and the failed premise is stored as a parameter-erased
skeleton. Two-sided non-authority rule: a record does not establish that
the class can never apply, an absent record establishes nothing, and the
ledger never feeds ranking, selection, or rejection counts. First users:
the false-green audit (discipline 3) and the memory junk audit
(discipline 5). Source: siliconjungle/ink-planner `near_misses.py`.

### 18. Approvals are content-bound, expiring, and generation-scoped

**Ship status (2026-11-02):** specification-only. No folder in this package ships this mechanism; a host implements it from this text.

An approval or authorisation binds a stated action once to its resolved
target identity fields and to the hash of the content it was granted
over; any post-trust edit invalidates the record; approvals carry an
expiry (30 days by default) and can be revoked; a generation counter
voids bindings made before a compaction. Evaluation before any outward
or irreversible action returns one of five verdicts:
authorized_unique / requires_selection / authorization_invalid /
drifted / out_of_scope. No implication crosses actions: publish implies
nothing toward unpublish. An approval bound to a name or a summary is
not an approval. Sources: GreenLv/codex-context-guard `cg_authority.py`;
qualixar/bounded-loops `trust_store.py`.

### Round-5 concretions, by discipline

- Discipline 1: the fire threshold is the closed form
  tau(p_need) = C_FA / (C_FA + p_need * C_FN); fire iff estimated
  p_accept >= tau; slow mode only within a declared margin of the
  boundary, its cost charged to the same ledger entry; costs and margin
  live in per-lane config read by the gate, never in the generator
  prompt; deadline-driven lanes declare C_FN as a function of
  time-to-deadline (PRISM). A lane is gated only if the gate executes
  inside that lane's own send path; a gate living in an offline harness
  is UNVERIFIED for that lane (correction: ProactiveAgent's shipped demo
  contains no reward gate). Feedback is a structured logged event
  (accept / reject / ignore-timeout, carrying the fire's deterministic
  ID); the timeout event is written by the lane's own code, never
  inferred from prose. Per-lane min_interval and max_fires_per_window
  are enforced in code at validation time, fail-closed. Every would-fire
  entry carries class: horizontal | vertical; a vertical fire names the
  evidence it will fetch first; evidence already in current state
  reclassifies it horizontal at the lower price. Each lane declares an
  explicit ask outcome, distinct from staying silent and from error.
- Discipline 2: the local instincts build starts from the ECC runtime
  parameters now located in source (threshold 0.7, cap 6 injected
  instincts, 220-char summary cap, 8,000-char total injection budget
  with an explicit truncation marker; relevance is an additive ranking
  boost only, +0.25 project-scoped and +0.20 stack-matching, not
  configurable). A learned unit influences inference only above a
  minimum success rate; near-duplicates merge on a maintenance interval;
  hard per-type cap. A new extraction submission for a scope with a
  pending extraction cancels and replaces the pending one.
- Discipline 3: any local execution of model-generated code runs under a
  deadline and memory cap, an allowlisted host surface and an
  allowlisted environment (never the ambient environment wholesale), on
  copy-on-write state, and commits only on success. Every local
  mechanical gate carries a named mutation list that neuters its core
  checks, run in its own test suite, with zero mutants survived;
  stateful tools also get seeded-fuzz or model-differential tests whose
  pass line prints cases= and seed=.
- Discipline 4: future-assertion temporal normalisation is a
  deterministic post-extraction rule, not an extractor promise: a
  future-tense fact (plan, promise, schedule, intention) is true-from
  the date it was stated; its deadline is never its true-until;
  true-until is set only by an event that ends the fact. The nightly
  pass lists which stored facts retrieval actually returned in the
  trailing 14 days; a standing fact with zero retrievals is a demotion
  candidate, named for review, never silently dropped.
- Discipline 5: a gate-wired checker enforces the memory store's
  write boundary at commit time (root index presence, per-file and
  total character budgets, frontmatter validity, a read-only list for
  ruled files); unattended memory workers run fail-closed in the
  narrowest filesystem scope, and where no scoping mechanism exists the
  pass is read-only. Nightly synthesis ranks candidate material by
  surprisal against the existing corpus, consolidates highest first,
  names what its budget did not reach, and is due-gated (no new dated
  material means one log line, not a full pass). A store-to-index
  reconciliation loop heals in bounded batches and names any item
  failing three consecutive runs. Reflection is a triggered pass
  (step-count, compaction-event, manual), never ambient; a compaction
  event queues a pass over the compaction delta with a bounded snapshot.
  A failed synthesis keeps the old synthesis live, records an error
  state, and does not advance its watermark. Seeded defaults record
  applied seed ids in a ledger separate from the items, so a user
  deletion survives re-seeding. Use strengthens a memory only through
  confirmed usefulness, never retrieval: delta capped, repeats inside a
  cooldown do not stack, a contradiction freezes strengthening; any
  decay table is stated per fact kind as configuration, and an unstated
  decay is no decay. A status figure whose source could not be read is
  reported UNMEASURED with the source named, never as 0, empty, or OK.
  An extraction or summarisation step that fails returns an error state,
  never an empty success.
- Disciplines 6 and 7 (the skill gate suite): a SKILL.md at or over
  20,000 bytes loses its tail silently after compaction, so size is a
  gate, and oversized skills split body plus references. Trigger evals
  use positive plus negative queries, 3 runs per query, a 0.5 threshold,
  a stratified train/test split, winner selected on the validation score, the
  improver fed only failures plus attempt history with a do-not-repeat
  instruction; old-vs-new comparison is blind, and every change record
  carries a benchmark delta line. (Corrected 2026-11-02: a set that
  selects the winner is validation data, whatever it is named; final
  measurement uses the untouched final test in discipline 6, run once
  at the end.) Skill lint floor: six allowed
  frontmatter properties, kebab-case name max 64 chars, description max
  1,024 chars with no angle brackets, compatibility max 500 chars. Token
  costs are banded separately (trigger 48/92/150, invoke 220/480/900,
  deferred 180/520/1,200 tokens); explicit-only skills are excluded from
  implicit cost and reported separately; a skill entering the heavy
  implicit band fails review until made explicit-only or split.
  Agent-behaviour skills carry at least one trajectory fixture (tool
  sequence in order, forbidden tools by absence, partial arg checks);
  assertions support weight 0 = record-only, so a new grader runs one
  cycle record-only before it may gate; redteam generators are named
  (memoryPoisoning, crossSessionLeak, excessiveAgency). Revision loop: a
  failed fixture produces score plus one-paragraph textual feedback; the
  revision edits only the section the feedback implicates, then re-runs
  the set or reverts; few-shot examples enter a playbook only if the
  teacher output passed the playbook's own eval metric, with metric and
  threshold recorded beside the example. Any locally generated index
  ships with a regeneration-diff check. A library entry must declare
  read / write / external-send capabilities explicitly; no declaration
  is a rejection, never an inference. A path confinement check counts
  only if it resolves symlinks and compares on a separator boundary; a
  prefix-only guard is a named scan defect. Shared prompt fragments are
  referenced by name plus pinned hash, never copy-pasted, and a lint
  flags drift; every eval result records the fixture-set version/hash
  it ran against and is keyed by the deterministic ID of (run,
  assertion name, occurrence). A verifier verdict carries the shape
  {valid: bool, reason: string} and a false verdict's reason feeds the
  worker's next attempt (discipline 8 note).
- Discipline 8: a completion gate blocks only on machine-verifiable
  facts (mtimes, counts, exit codes, disk); pattern heuristics warn,
  never block; complexity is measured by tool-call counts; claim
  detection is sentence-scoped, quote- and code-stripped, with a
  not-claim filter and a fire plus no-fire fixture pair per phrase;
  evidence is turn-scoped and failure traces count as evidence;
  block-once is a sha256 fingerprint of (hook, session, text); config
  errors fail closed, gate crashes fail open and log; interruptions are
  budgeted, feedback is size-bounded (pending count, reason, next step),
  and exhaustion degrades to a named UNVERIFIED. (Governing scope,
  2026-11-02: the crash rule in this sentence governs the completion
  gate's own process failure only; a local gate's verdict on work it
  cannot evaluate still fails closed. See the governing statement in
  discipline 8.) Completion additionally
  requires a unique-candidate cover of obligations by evidence records.
  A plan whose budget can be fully consumed by production, leaving
  proof unfunded, is invalid at authoring time: verification budget is
  reserved in the plan itself.
- Discipline 9: a compaction handoff gets its own one-shot capability
  store, structurally outside the tool registry (token plus separate
  handoff id, TTL-bound, exactly one waiter, second submission rejected,
  empty summary rejected, consumed on delivery); a handoff token can
  deliver a summary and can never invoke a tool. Checkpoints follow a
  declared schema with per-field and total bounds (objective / state /
  evidence / decisions / pending); an over-budget checkpoint is rejected,
  never silently truncated; checkpoints carry a content-hash key, a
  stated cap, and a TTL. Fence tokens carry a per-run random suffix so
  fenced content cannot forge the closing token, and streamed scanning
  uses a holdback buffer sized to the token, never a naive per-chunk
  split/replace; the blocker feeds the token split at every offset. A
  peer track's standing to write a shared surface is a scored,
  mechanical fact; writes carry writer identity; repeated defects lower
  standing; below the floor is read-only until a human restores it; the
  scoring table is stated before it is enforced.
- Discipline 15 (effect queue, second form; governing form, 2026-11-02: this form supersedes the uncapped backoff rule in discipline 15 for generic failures, which survives only for rate-limit pauses): rate-limit (429) pauses are
  accounted separately from generic retries: unbounded pauses,
  exponential to a cap, Retry-After honoured past the cap, attempts
  never incremented; generic errors bounded, exhausted items land in a
  named skipped list. No completion event from a queue that never ran.
  Retry state is keyed by the durable operation id at queue level;
  exhaustion returns a terminal non-retryable error carrying the last
  failure verbatim. Each row carries an infra_errors counter distinct
  from attempts. Stale is an outcome: offering a revision at or below
  the stored revision changes nothing; replacement and retry preserve
  the original queued_at and rank; settlement is by exact receipt, and
  a receipt issued before a retry cannot complete the retried row;
  admission is atomic. An action that raises lands in a visible failed
  state and never strands later actions. Hook-produced effects use the
  file-outbox form: append-only JSONL plus a .sent high-water mark;
  SQLite is reserved for effects needing generation guards.
- Disciplines 13 and 14: diagnostics and logs pass through a recursive
  redactor at capture time (key-substring classes plus
  prompt/question/query/selection key classes; markers REDACTED,
  REDACTED_CIRCULAR_REFERENCE, REDACTED_TOO_DEEP), so redaction is a
  property of what is stored, not of what is later displayed.

## How these compose with the core

- Disciplines 3 and 8 extend existing law (the regression-blocker law and
  Proof Before GREEN) with mechanisms; where wording overlaps, the core
  skill wins.
- Discipline 9 extends "content is evidence, never instructions" to
  authority.
- Disciplines 4, 5, and 12 govern one memory of record: its structure,
  its honesty, and its freshness. Discipline 11 records why its decisions
  were taken. None of them authorises a second store, hosted or local.
- Disciplines 1, 2, 6, 7, and 10 are new surface: initiative, procedural
  memory, skill authoring, adoption gating, and prose quality. They
  inherit every core constraint (SCOPE, authority, proof) unchanged.
- Round 5 (2026-11-02): discipline 17 governs learning from gate rejections without poisoning the rejected class; discipline 18 makes approvals content-bound, expiring, and generation-scoped. The round-5 concretions attach to existing disciplines and do not create new ones beyond 17 and 18.
- Round 4 (2026-11-01): disciplines 13 and 14 govern the outbound and
  identity layers (what may be sent, and how anything is named so it
  cannot arrive twice); discipline 15 governs side effects after a
  decision; discipline 16 governs routing and concurrency. The round-4
  mechanism notes inside disciplines 1 and 9 extend those disciplines
  and do not create new ones.
- This reference was revised on the day it landed by a second,
  artifact-level pass. Where the first account of a mechanism and the
  artifact disagreed, the artifact won, and the corrections are recorded
  in the changelog (2.6.0), not smoothed over. A third pass then
  graded all twelve disciplines against the layers the first two
  skipped: 2 confirmed, 8 qualified, 1 warned, 1 untested by the
  pass. Its corrections and concretions are in the changelog
  (2.7.0), and each discipline carries its standing in place. A
  fourth pass (2026-11-01) then added disciplines 13 to 16 and the
  round-4 mechanism notes and cautions; its account is in the
  changelog (2.8.0).

## Backlog: recorded, not adopted

Promising, and deliberately deferred. Each waits for its trigger, not for
enthusiasm.

| Item | Source | Trigger to revisit |
|---|---|---|
| ADD-only raw layer under the curated memory, with multi-signal retrieval (the extraction spec and fusion formula are adopted in discipline 4; temporal ranking is a hosted-platform feature, absent from the open-source build, and is not part of this item) | mem0ai/mem0 | If recall misses persist after disciplines 4 and 5 land |
| Typed skill relationships (requires / related / combines_with / supersedes) with separate quality facets | findscripter/everything-skills | With the discipline 6 description lint |
| Count-triggered summarisation triggers inside nightly synthesis | siliconjungle/ambient-ai-chat | If synthesis cost or drift becomes measurable |
| Gated skill-crystallisation counts (a procedure must recur N times before it may become a skill) | MemTensor/MemOS | Largely inside discipline 2; revisit if instinct promotion proves noisy |
| Explicit-versus-background context split for always-on surfaces | openai/mcp-extensions | When an always-on surface is actually built |
| A named context-filter step in research workflows | assafelovic/gpt-researcher | Next research-workflow revision |
| Tree-of-thoughts discipline for named combinatorial problem classes | kyegomez/tree-of-thoughts (paper, not code) | When a problem class is named that fits it |
| Best-of-N with a verifier, and principle extraction from past successes and failures (LEAP) | algorithmicsuperintelligence/optillm | For high-stakes single answers |
| The catalog-as-skill pattern for the next large local index | hashgraph-online/awesome-ai-plugins | When an index outgrows its file |
| Multi-format export contract for any transcript exporter | pionxzh/chatgpt-exporter | When an exporter is built |


## Round-4 cautions: recorded, not adopted

Boundaries learned from the same teardown (deepseek-ai/dsh-superagent-prototype at commit 6337fc8). Each is an
anti-pattern this doctrine rejects by name; none is adopted in any form.

| Anti-pattern | Why it is rejected |
|---|---|
| Workers running with full operating-system access as the operator, with name-shim blocked-command lists treated as a boundary (`src/app/sessions.ts:152`) | A name shim is bypassed by an absolute path, and some tools can never be blocked; approval gates exist precisely because this posture is the fatal-flaw class. |
| Subscription fan-out delivered to an executing worker with no sender check, and subscriptions with no expiry (`src/core/intake.ts:38-51`) | Any participant, bots and automation included, reaches execution; discipline 16 adopts the routing economy only with the authorisation check retained. |
| Prompt-only scope for admitted work, including no mandate text at all for explicitly admitted work (`src/executor/dsh.ts:91-95`) | Prose scope is not enforcement; discipline 9's round-4 mandate is an immutable object, revalidated at resume. |
| Bot-versus-human decided by prompt naming, because code counts ordinary-account bots as human (`src/sources/github-trigger.ts:43-47`) | Identity class is a code fact or it is nothing; a prompt label does not change what a sender is. |
| Policy writable through an agent tool origin, with only some fields panel-only (`src/app/settings.ts:45,51,143`) | The governed system must not be able to rewrite its own governing policy through its work surface. |
| A documents-only periodic prompt offered as a watchdog substitute | A prompt that describes checking is not a check; a watchdog is a mechanism that detects and acts, or the gap is named as uncovered. |
| Per-source identity non-mapping as a general principle (`src/policy.ts:1-4`) | Correct for that system's threat model; fatal to cross-channel continuity, which disciplines 4 and 5 are built on. It is not imported. |
| Unimplemented designs and unmeasured benchmarks cited as features | Designs admitted as future work and numbers with no artefact behind them are UNVERIFIABLE and are never adopted as evidence. |

## Round 6 (2026-11-02): the total-harvest landing

This round lands no new discipline. It lands the registers of a total
harvest: an outside sweep of public agent systems (206 roster rows, 72
audited in depth, 10 unreachable with reasons named in the local record)
and a full inventory of one working system's own hard-won knowledge
(324 entries: 299 codified, 25 tacit, 11 superseded elements carried
inside codified entries), each judged against the eighteen disciplines
and the core skill. The three standings stay visibly distinct, in three
different forms, and no row migrates between them silently.

### Coverage note: standing 1, already in force

The harvest's implemented mechanisms (54 outside entries, plus 6
second-brain packages, plus 18 already-have cross-references counted
once) were checked against the disciplines and found already carried:
memory and recall by disciplines 4, 5, and 12; skills, gates, and
verification by disciplines 2, 3, 6, 7, 8, 9, 11, 17, and 18 and the core
skill's proof and report sections; proactivity by disciplines 1, 13, 15,
and 16; prompting and execution by disciplines 6 and 10; platform and
workspace surface by disciplines 7, 9, 14, 15, and 17 and the playbooks
reference. The homegrown codified entries are the local codification of
this same doctrine: the core skill, the eighteen disciplines, the
playbooks truth gates, review mode, the lessons patterns, and the
standing laws those entries cite as their homes. None of it is restated
here. Restating it would duplicate the single source of truth, which the
doctrine forbids. The proof of coverage lives in the local harvest
record, not in this file.

Of the 25 homegrown tacit entries (proven in practice, never properly
codified), one names a doctrine file as its proposed home and lands in
the Backlog extension below. The remaining 24 name local homes (local
skills, local tools, local charters and standards) and do not land in
this repository; they are counted here so the number is honest. Several
of their generalized technique cores land separately as lessons patterns,
where the lessons file is their genre.

This round also adds a skills library to the repository (see
skills/INDEX.md at the repository root of the skills tree): 19 complete
skill folders a reader can install as-is. A skill landing in the library
is not a promotion of any register row, and a register row is not a
summary of any library skill. The library is installable craft that
exists and is in use; the Backlog below remains mechanisms not yet
adopted as doctrine.

### Backlog register extension (Round 6): standing 2, candidates

Candidates, not doctrine. Each row carries its adoption test in the
trigger column: the observable result that would settle adoption. A
candidate is adopted only by a dated round note that records the test
passing.

| Item | Would extend | Adoption test |
|---|---|---|
| A-1 Context Doctor as a named skill | Disciplines 4, 5 | The packaged audit runs on demand against the live store and returns the same findings as the scheduled audit, including a proven no-edit-needed outcome on a clean fixture |
| A-2 Schema-version fence on memory writes | Discipline 4 | A write from a mismatched schema version is refused in a test, and a matched write passes; the refusal names the version gap |
| A-3 Operation-level scorer over memory changes | Discipline 4 | The scorer grades a recorded set of add, update, and delete operations and its grades match human grades on the calibration set at the stated rate |
| A-4 Thread-following recall | Discipline 5 | On a fixed query set with known linked chains, thread-following returns facts ranked recall misses, with no precision loss on the control queries |
| A-5 Entity-match boost in search ranking | Discipline 5 | Ranking with the boost beats ranking without it on the fixed memory eval set, measured, not argued |
| A-6 Native session-diagnosis skill | Disciplines 6, 8 | The skill runs the forensic protocol end to end on a recorded session and every claim in its report carries a citation that resolves |
| A-7 Self-configuration scan, native subset | Discipline 7 | The scan finds planted misconfigurations in a fixture harness and scores from findings only, with a pure line shift producing no new finding |
| A-8 Typed skill relationships plus quality facets | Disciplines 6, 7 | The catalog carries typed edges and facet records for every skill, with unreviewed as the default state, and the lint enforces both |
| A-9 User-gate tagging at authoring time | Discipline 8 | A planted invented-verification case is caught by the tag check at close, and a clean case passes |
| A-10 Omission-named budgeted injection | Discipline 9 | An injected context that omits material names the omissions inside the injection, proven on a fixture with a known omission |
| A-11 Bounded multi-start check at verdict points | Discipline 8 | At a root-cause and a completion verdict, the bounded check runs, disagreement is logged as signal, and the vote is nowhere recorded as proof |
| A-12 One standing improvement queue | Discipline 8 | Improvement notes from two consecutive inspection cycles land in the single queue and none are found only in reports |
| A-13 Executor, Analyst, Mutator role split | Discipline 6 | A skill revision cycle runs with the analyst pass naming one of the four mutation strategies per change in the change log |
| A-14 Content-addressed fragment registry | Discipline 11 | A large context bundle is stored once, cited by hash from two runs, and a changed bundle produces a new hash with no silent overwrite |
| A-15 Commit-boundary secret guard | Discipline 7 | A planted secret at the commit boundary is blocked, the agent cannot pass the disabling flag, and an infra failure reads as infra failure, not as a policy block |
| A-16 Single-source multi-harness skill export | Discipline 6 | Built only when an export target exists; the test is one canonical source generating adapters whose behavior matches on the trigger eval |
| A-17 Admission strength on every handoff | Discipline 9 | Handoff records carry explicit, inferred, or not admitted, and inferred work is visibly weaker in the receiving record |
| A-18 Mechanical worker-slot cap | Discipline 16 | The scheduler refuses a spawn beyond the cap in a test; until the runtime supports it, this row stays a candidate by its own terms |
| A-19 Edited-comment rule in event IDs | Discipline 14 | An edited source comment produces a new event ID and a redelivery of the unedited comment does not, both proven in a fixture |
| A-20 Audit the silent verdicts | Discipline 1 | A review cycle samples silent gate verdicts alongside fires and scores missed needs; a rejection triggers at most one reformulation that names what changed |
| A-21 Pre-send delivery-form checklist | Disciplines 1, 13 | The five-check scoring runs on drafts before the gate and its deductions match the source rubric on a labelled draft set |
| A-22 Per-partition sharing rule line; deadline-varying cost | Disciplines 4, 1 | Each workspace carries its one sharing-rule line, and one deadline-driven lane declares cost as a function of time remaining, read by its gate from config |
| A-23 Local lane-scorer kit | Discipline 1 | If a lane scorer is built, it implements the window-labelling recipe, the timing shape, and gap-dependent cases together, proven against recorded lane history |
| A-24 Judge calibration set | Disciplines 1, 7 | If a model judge is added, its calibration set is a small human-labelled local set with a consistency filter, and the judge's agreement rate on it is recorded before it gates anything |
| A-25 Grounding recorded separately from success | Discipline 8 | In any expanded GUI or browser lane, each action record carries a landed-on-target field distinct from task completion, from the first run |
| A-26 Record-only metric mode, trajectory fixtures, metric provenance | Discipline 7 | The eval harness runs one cycle with a weight-0 grader before it may gate, one trajectory fixture type exists, and every reported metric row states measured or replayed |
| A-27 Scored research filter with replay fixture | Playbooks (comprehensive searches) | The filter step emits per-chunk scores, drops sub-threshold chunks, and its replay fixture passes as a regression blocker |
| A-28 Reflective revision loop for skills with eval sets | Discipline 6 | A failed fixture produces a score plus a paragraph naming the failure, the revision edits only skill text, and harvested examples come only from outputs that passed the skill's own metric |
| A-29 Validation-error reask contract | Discipline 8 | A structured-output step retries only on schema or parse failure with the error fed back verbatim, under attempt and budget caps, and the result states attempts and cost |
| A-30 Offline grammar testing with a mock model | Discipline 7 | Each recurring machine-consumed output carries positive and negative example strings as a local test that fails deterministically on a malformed sample |
| Homegrown tacit: mechanism proof is not outcome proof, and scope contracts must be written as outcomes | Review mode reference | The technique is written into review-mode.md in generalized form, an eval case exercises a mechanism-defined scope contract being rejected, and the entry's standing flips from tacit to codified in the local record |

Conditional defers from the second-brain sweep (K1 to K24). Neither
adopted nor rejected. Each waits for its named activation trigger, kept
visually separate from the candidates above because the standings differ.

| Item | Activation trigger |
|---|---|
| K1 The second-brain surface and dialect itself | An app for that surface actually runs in the adopting system |
| K2 Wholesale vault adoption | A vault becomes the working surface by an explicit owner ruling (its wholesale form is also refused in the rejected register) |
| K3 Third-party skill and plugin installs | An install candidate passes the library adoption gate in discipline 7 |
| K4 Session hooks and background memory writers | A host with session hooks exists and a governed writer design passes the memory write boundary |
| K5 Vault MCP servers | A vault surface is in use (see K1) and a server passes the adoption gate |
| K6 Egress research profiles | A research lane needs a named, bounded egress profile |
| K7 A local BM25 plus rerank stack | Ranked recall measurably misses on the fixed eval set after disciplines 4 and 5 |
| K8 Clean web extraction | A recurring extraction need that the current routes fail on, measured |
| K9 Query-defined index views | An index outgrows its file and views are demanded by real queries |
| K10 Tiered query read budgets | Query cost becomes measurable enough to budget against |
| K11 Extractive log fold rollups | Log volume makes fold rollups cheaper than direct reads, measured |
| K12 Stable page addresses | A surface is published whose readers cite pages across revisions |
| K13 Methodology modes | A named methodology is adopted for a real workflow |
| K14 Per-operation git checkpoints | Checkpoint cost is proven lower than the recovery cost it replaces |
| K15 Bi-temporal people-page timelines | The page owner rules the change; people pages are runtime-owned and skipped on authority until then |
| K16 Per-layer token budgets | A layer's token spend is measured and a budget binds it |
| K17 Proactive save reminders | A save lane exists whose misses a reminder would have caught |
| K18 Typed-link vocabulary | The link graph grows past what untyped links can audit |
| K19 Link-graph health series and access-log pruning | The graph is large enough that health must be trended, not spot-checked |
| K20 Universal hub routing lines | More than one hub surface exists to route between |
| K21 External AI history export ingest | The owner supplies an export to ingest |
| K22 Minor output formats | A consumer requires a format the current set lacks |
| K23 Non-memory tooling from the sweep | A named tooling gap the current tools do not cover |
| K24 Generic reasoning rituals and author production claims | Never an adoption trigger: these stay deferred unless a mechanism is extracted and tested on its own (claims are not mechanisms) |

### Rejected register: recorded, refused

Standing 3. A rejected design stays rejected instead of being
re-proposed: discipline 11's rationale memory, applied to the doctrine
itself. An ingesting reader must not re-derive these as fresh ideas.
Each row carries its reason.

| Item | Why it is rejected |
|---|---|
| R-1 Hosted or parallel memory engines and platforms as products | The local file memory is the single source of truth; a second store forks it or moves facts off the owner's machine. Mechanisms were extracted; products were not adopted. |
| R-2 Forks and mirrors with no mechanism delta over their parent | No delta, no entry. |
| R-3 Vendor benchmark claims as adoption evidence | Numbers are not mechanisms, and headline figures repeatedly failed artifact-level checks in rounds 2 and 3. |
| R-4 Self-modifying and self-configuring agents | The governed system does not rewrite its own governing files, skills, hooks, or permissions. |
| R-5 Ungated sensing and capture surfaces (continuous activity, screen, input, or page capture) | Disproportionate capture for the benefit. |
| R-6 GUI-agent products as products | Their transferable discipline was extracted; no product adopted. |
| R-7 The round-4 cautions' source core | Already landed as the Round-4 cautions above; cross-referenced here, not duplicated. |
| R-8 Installing any vendor system wholesale | Mechanisms are reimplemented natively; an installed foreign system imports its own governance and update channel. |
| R-9 Leaked-prompt corpora and persona anthologies as mechanism sources | Not evidence, and not a source class this doctrine learns from. |
| R-10 Frameworks adopted as frameworks where the local system already has the infrastructure | Procedures extracted, platforms refused. |
| R-11 Self-grading machinery: model-assigned float scores as evidence, unbounded self-iteration as a stopping rule, snapshots treated as truth | A grade the system assigns itself is not proof about itself. |
| R-12 Prompt folklore and unenforced prompt forms | What was mechanical was extracted; the rest does not survive a gate. |
| R-13 Weak platform and extension products: claims without source, subscription-shaped workarounds, catalogs valued for mining rather than as artifacts | No artifact behind the claim means nothing to adopt. |
| R-14 Substrate and dataset adoptions (sync substrates, triple-store fact logs, queue and retry implementations, dataset files) | Substrates are not mechanisms in a file-first system; their design lessons were extracted. |
| R-15 Screened-out sets with recorded reasons | No mechanism was claimed at screening; the classes are recorded so they are not re-screened from scratch. |
| R-16 Research artifacts as products (benchmarks, datasets, simulated-user rigs) | They informed metrics; the products do not fit a single-user, file-first, gate-first system. |
| R-17 Distribution scale and catalog size as vetting evidence | Size is not a scan and a star count is not a proof. |
| O-R1 Secrets in memory, in any form | Memory is read by agents and tools; a secret stored there is a secret distributed. |
| O-R2 Standing instructions downloaded from a mutable third-party source | An unpinned external file read as standing orders is a supply-chain and prompt-injection exposure. |
| O-R3 An unattended background agent writing the memory of record with permissions skipped | Incompatible with the memory write boundary: unattended memory workers run in the narrowest scope or read-only. |
| O-R4 Auto-rewriting memory on ingest and auto-reconciling contradictions | Contradictory evidence is a stop signal; both readings are carried dated and unresolved until evidence or a ruling settles them. |
| O-R5 Broad-permission channel patterns as an intake route | The permission breadth is disproportionate and duplicates safer existing access. |
| O-R6 Sending memory content to third-party APIs to fill gaps | Memory content leaving the machine as gap-fill queries is exfiltration by design in this system. |
| Superseded: the unqualified claim that background work survives process restarts | Replaced by the proven rule: background work dies with its process; long work runs detached and checkpointed, supervised by effects. |
| Superseded: the belief that a requested timeout is the enforced timeout | Replaced by the measured platform cap and resume-by-design: phases are commit-sized and a stopped run is relaunched from its record. |
| Superseded: a watchdog scheduled in a different session than the work it watches | Replaced by supervision in the session that launched the work; a watcher that cannot see its runs reports an empty world, not a healthy one. |
| Superseded: an earlier memory-extraction prompt generation, and benchmark rankings as supporting evidence | Replaced by the current extraction generation and artifact-level evidence; one widely cited benchmark's rank was retired as evidence after an independent audit of its answers and judge. |
| Superseded: first-generation effect-queue semantics | Replaced by effect-queue v2 semantics in discipline 15 (waiting distinct from failure, settlement by exact receipt). |
| Superseded: printing a composite headline as the cure for a weak summary surface | Replaced by letting the component measures speak for themselves; the composite is still computed and recorded, as presentation machinery only. |
| Superseded: a standalone indicator claim carried as an edge | Replaced by the frozen-method rule: a claim survives only inside a tested method with logged reads, never as a lone pattern assertion. |
| Superseded: a permanently-corrupt-data framing for a feed whose defect was bounded | Replaced by per-source trap registers: each source carries its named revision, staleness, unit, and identity traps beside its consumer, and verdicts are scoped to the proven defect. |
| Superseded: a recovered-notes archive treated as a knowledge source | Replaced by verified skills: unverified recovered notes are an archive to compare against, never a source to act from. |
| Superseded: retired standalone skills as the carriers of their techniques | Replaced by the consolidated skills in this repository's library, each complete and installable as-is. |
| Superseded: reporting a failed route as an absent thing, as a live failure pattern | Replaced by its own codification: route failure is never impossibility, and absence is proven separately with a coverage ledger, in the core skill and in the absence-proof skill in this library. The pattern survives only as the founding example of the cure. |
