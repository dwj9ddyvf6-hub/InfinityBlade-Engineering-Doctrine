# Agent Enhancement Registers: Backlog, Cautions, Coverage, and Rejected Designs

The companion to [agent-enhancement.md](agent-enhancement.md), split out in 3.1.0. Everything here is recorded, not adopted: deferred ideas wait for their named triggers, cautions name what a source got wrong, and rejected designs stay rejected, with the reason attached, so they are never re-proposed at full price. Nothing in this file is a discipline and nothing here promotes itself.

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
