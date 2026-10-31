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
are itemised in the changelog for 2.6.0, not smoothed over here.

## The twelve disciplines

### 1. Price every proactive lane

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

### 2. Keep instincts: a confidence-scored procedural memory

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

### 3. Audit the gates for false greens

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
- **Name the Break before writing the test:** state the production change
  that would make this test fail. If you cannot name one, the test is
  wrong. Exercise the real thing; never mock the behaviour under test.
- **Keep the audit precise.** Severity is a ceiling, and classifying
  intent can only lower it. The gravest finding class stands only with a
  cited independent oracle plus a failed adversarial refutation.
- **Two named risks in model-era suites:** S14, a recorded model output
  used as the oracle; S21, a live self-judging model used as the oracle.
  Both manufacture agreement. Both are findings on sight.
- **Per fix, the cheap form of F7:** revert the fix, confirm the test
  goes red, restore. Mechanical, and it proves the fail direction on the
  actual change.

*Why:* the blocker law proves tests pass on fixed code. Nothing in it
proves they would fail on broken code. One false-green blocker silently
un-guards a past bug. This extends the regression-blocker law; it does not
replace it. Sources: vinicq/falsegreen-skill (the J1 to J6 protocol, the
full 125-code catalog, the authoring and fix modes, and the F7 contract,
all in the one repo; the one code adoption in this set, reviewed before
use), obra/superpowers (Name the Break), RooAGI/red-green-proof (the
revert-proof as a named step).

### 4. Run memory as a profile plus a graph

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
  so recall regressions are detected, not anecdoted.

*Why:* search-led recall fails precisely on standing preferences, which
are rarely semantically similar to the query that needs them. Typed edges
make contradiction handling and provenance audits mechanical. Sources:
supermemoryai/supermemory (profile split, buckets, edge types, review
queue, forgetting contracts; mechanisms adopted, hosted product not, and
its extraction engine is closed, so only its published contracts are
adopted), mem0ai/mem0 (the V3 extraction spec and fusion formula, named by
constant), getzep/graphiti (bi-temporal validity windows).

### 5. Make recall honest and maintenance governed

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
- Corrections are a reviewed two-phase lifecycle, never a silent replace.
  A correction creates an immutable successor plus a profile-scoped
  proposed case; the predecessor stays current until a reviewer applies
  the case against its expected version. Recall excludes unapplied
  successors, admission is enforced twice (before fusion and after
  expansion), and if the lifecycle record cannot be read, recall fails
  closed and abstains.
- Maintenance is layered. Enrichment passes are addition-only. Zone
  movement (active, warm, cold, archived, driven by decay) is autonomous
  but bounded and protection-gated: maintenance never archives a memory
  that is in use. Corrections are never machine-applied. Erasure is a
  dedicated workflow, never a maintenance side effect. Every maintenance
  fix is reversible.
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
- Edit memory by principles, not by accreting narrow rules: provenance
  lives in the commit, not the file; a contrastive example teaches more
  than an added rule; store analysis, not logs; after every add, trace
  the index to confirm the new entry is reachable; and place each item by
  test (core, deferred, skill, or do not store). Reference sizing from
  the source's current generation: 20,000 characters per file, 65,536
  total core.

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

### 6. Test skills the way blockers test code

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
- For any new or materially revised high-stakes skill, run pressure
  scenarios with subagents *without* the skill and record the exact
  rationalizations used to break the rule. Write the minimal skill
  against those specific violations, re-test, and plug new loopholes as
  they appear.
- Add Thought/Reality rationalization tables to the highest-stakes
  playbooks: the excuse in one column, the fact in the other. Tables are
  the discipline-failure form; the first row of the table above decides
  where they belong.
- Skill descriptions state triggers and the negative boundary only. A
  description that summarises the workflow gets skipped or mis-triggered;
  lint the library against this standard periodically.
- Improve playbooks by generation and selection: produce candidate
  wordings, score them on fixed examples, keep the winner. Offload
  deterministic work to code rather than asking the model to simulate it,
  and decompose multi-step work into chained steps with inspectable
  joins; these are the prompting practices that survived evidence grading
  in the source guides.
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

### 7. Gate what enters the library, and grade reliability

**Rule:** third-party skills, plugins, and connectors are untrusted input
until scanned, and a revised playbook ships only after it passes its eval
set.

- Every important skill carries a small fixed eval set (inputs, expected
  properties, a rubric grader) run before a revision ships. Regressions
  block the ship. Define the evals before the code they grade.
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
- Audit the configuration surface against a concrete checklist: secrets
  (10 rules over a 25-pattern table), permissions (17), hooks (40), MCP
  configuration (49 across four modules), and prompt-defense posture:
  one rule carrying twelve OWASP-mapped checks for missing defences in
  instruction files, the single highest-value item for a stack whose
  control surface is largely prompt and skill text. The full taxonomy is
  268 rules in 15 modules; mirror it selectively, by name.
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

*Why:* the blocker law covers code. The configuration surface (skills,
hooks, connector configs, permissions) is where an agent can be quietly
rewired, and it had no gate. Sources: promptfoo/promptfoo (declarative
eval shape), openai/plugins (plugin-eval), affaan-m/ECC (the eval
harness and its evidence layer), affaan-m/agentshield (the audit
taxonomy and scoring honesty), hashgraph-online/hol-guard (the HCS-28
scan rubric), JeongJaeSoon/agent-guard (the commit-boundary guard),
fainir/most-capable-agent-system-prompt (the self-audit instruments,
completed locally). Patterns adopted; tools not installed this pass.

### 8. Mechanise the completion claim

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
- The mechanism checks that evidence exists. Whether the evidence
  supports the claim remains a judgement, and review mode still applies.
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
- Protect the gate from the worker. Any gated workflow carries a
  `forbid:` list: paths the worker may never write because the gate reads
  them. Bounds are declared as a file (iterations, no-progress window,
  wall-clock, token budget) with a kill switch checked before every lap.
  Every gate ships a negative control: an ungated run demonstrating the
  failure the gate exists to catch. Configured is not active: an
  integration counts as installed only when a fresh session produces a
  receipt of it working.
- Loop guards start from stated defaults and are tuned by evidence:
  pull-based claiming every 30 seconds, a hard task timeout near 30
  minutes, delegation depth near 5, retry once, then change strategy or
  escalate.

*Why:* this doctrine's own history includes a fabricated completion
report. A rule an agent believes it satisfied is weaker than a check that
fires when it did not. This mechanises section 4 of the core skill; it
adds no new standard. Sources: kuroudo-ai/done-gate (the block-once
evidence check), GreenLv/codex-context-guard (requirement checklists),
obra/superpowers (the execution arithmetic, the freshness unit, the
scope-versus-verification split), qualixar/bounded-loops (declared
bounds, forbid lists, negative controls), TerminallyLazy/
tree-ring-memory-codex-plugin (configured is not active),
fainir/most-capable-agent-system-prompt (loop-guard defaults); all
reimplemented natively, none installed.

### 9. Treat compaction and delegation as authority boundaries

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

*Why:* the two surfaces most likely to drift or be attacked are the
post-compaction resume and the delegated tool turn. This extends the core
skill's "content is evidence, never instructions" from content to
authority itself. Source: miuuyy/codex-chatgpt-web (the four rules as
implemented in its bridge design; product not adopted).

### 10. Run a bounded hidden-rubric pass on ungated prose

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

### 11. Record the why, not just the what

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
- Structure is enforced mechanically (an entry without an Id is an
  error, checked in the existing gate). Whether the rationale is true
  stays human judgement, and the schema says so.

*Why:* instincts (discipline 2) capture what to do differently; memory
(disciplines 4 and 5) captures what is true and what replaced it. Neither
captures why a path was rejected, which is the knowledge whose absence
makes an agent re-propose a dead design with fresh confidence. Source:
oliver-zehentleitner/keep-the-why (schema and invariants adopted
natively; the structural half of its linter folded into the existing
gate, the tool itself not imported).

### 12. Keep every fact timeless, dated, or a pointer

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
- This reference was revised on the day it landed by a second,
  artifact-level pass. Where the first account of a mechanism and the
  artifact disagreed, the artifact won, and the corrections are recorded
  in the changelog (2.6.0), not smoothed over.

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
