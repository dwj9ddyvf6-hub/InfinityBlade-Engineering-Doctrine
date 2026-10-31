# Changelog

## 2.7.0 (2026-10-31)

- Agent enhancement, third pass: the sweep's final pass read the layers the first two skipped (issue trackers, release notes and test corpora, fork networks and one author's full account, the official vendor layer, benchmark repos and the paper lineage, practitioner ecosystems and framework memory as shipped code) and graded all twelve disciplines in `references/agent-enhancement.md`. Outcome: 2 confirmed, 8 qualified, 1 warned (memory profile/graph), 1 no contact (the hidden-rubric pass, recorded as untested by the pass rather than upgraded); discipline 3 carries a warned component and discipline 1 a warned design constraint, both named in place. No discipline was overturned and none was added. Ten concretions landed inside the existing disciplines: a deterministic diff-vs-intent scope-creep audit; user-thrown gate enforcement with a specify-the-HOW protocol at task close; operation-level memory scoring plus a scheduled junk-rate audit; planted-defect probes as the release gate for skill changes, with the vendor eval additions; transactional compaction with bounds tests and a clear/compact/remember triage; skill-description testing at vendor numbers, with assertive descriptions; content-addressed fragments for prompt context; confidence-gated adaptive recall depth; episodic exemplars, per-directory two-level self-description, and observed-by/knows-about scoping; and a tracker-and-gate hygiene pair (merged-state checks on closure claims, and the narrowest scoped disable named in every gate's deny message). Each discipline now carries its standing in place.
- Corrections to the 2.4.0/2.6.0 account, found on the third pass:
  - Honcho's scope: pass 1's "hosted-only thin harness" described only the small Codex satellite repo it opened; the core is a full open-source, self-hostable service (peers, sessions, an asynchronous deriver) under AGPL-3.0. The adoption conclusion is unchanged, but the barrier is licence and infrastructure weight, not hosted lock-in. No landed text carried the error; the correction is recorded here, and the core's one transferable element (perspective scoping) is adopted in discipline 7.
  - LoCoMo as evidence: an independent audit finds 99 of 1,540 questions (6.4%) with wrong golden answers (scoring ceiling 93.57%), a judge accepting 62.81% of intentionally wrong vague-but-topical answers, and an adversarial fifth no published result evaluates. LoCoMo rank is retired as supporting evidence for the memory and eval disciplines, and one source's "#1 on three benchmarks" claim reduces to a single published Recall@15 figure. No adoption is overturned; the adopted items are mechanisms read at artifact level.
  - Description hygiene, narrowed: the landed triggers-only rule read more minimal than the vendor's own guidance supports. Descriptions are now assertive ("pushy") against systematic undertriggering, with all trigger context in the description itself, and the one-step-task structural limit is stated in discipline 6.
  - Ledger evidence capture: the per-plan ledger's automated test-result field in the source implementation records the last non-blank log line, not a pass/fail token, and has ledgered a duration line as an outcome. Discipline 8 now states runner-aware capture explicitly.
  - Letta limits: the block sizes recorded on the second pass describe the current letta-code generation only. The V1 server line's 0.16.7 release deprecates and removes block-limit enforcement, so the figures must not be cited as enforced V1 behaviour.
  - The S-code catalog's proof state: 19 of the 24 semantic codes in the false-green catalog ship with no firing example and no look-alike, by the author's own filed issue (the S-series load path was silently broken for two releases for exactly this reason). The protocol and structural codes stand; S-code detection, the landed S14/S21 named risks included, is unproven until each code carries both.
  - Mode C's executor: the shipped `fix` executor executes model-generated tests with the full ambient process environment inherited, credentials included, self-disclosed and unfixed. The F7 contract stands; the executor must not be run as-is. Discipline 3 now carries the warning prominently, with the permitted forms (environment allowlist plus jailed working directory, or a locally controlled executor).
- The production finding behind the warned discipline: an audit of one unreviewed ADD-only memory accumulation (10,134 entries after 32 days) found 97.8% junk; of 224 survivors only 38 were clean enough to keep as-is, and one failure cluster was 668 copies of a single feedback-loop hallucination in which the agent re-extracted its own prior output. The inferred-memory review queue and the junk-rate audit in discipline 4 are load-bearing, not refinements.

## 2.6.0 (2026-10-31)

- Agent enhancement, second pass: an artifact-level re-read of the sweep's sources revised `references/agent-enhancement.md`. Two new disciplines: rationale memory (decisions stored with the alternatives they beat, an evidence grade, and a revisit trigger) and freshness (every stored fact timeless, dated, or a pointer). Completions across the original ten: form-matching and wording micro-tests for skill authoring; the F7 mutation contract, oracle-first authoring, and Name the Break for false-green defence; a scorer-plus-designed-gate composition for proactive lanes; the instincts build spec (capture redaction, extraction contract, promotion floor); numeric memory specifications (extraction block, profile budget, forgetting contracts, correction lifecycle, bi-temporal supersession); an eval evidence layer (effect classes, hash-chained capsules, fail-closed replay); a concretised self-configuration audit; the published HCS-28 scan rubric; execution arithmetic and gate protection; and a commit-boundary guard. The fainir slivers are adopted at corrected scope and leave the backlog; the backlog's Mem0 item is corrected below.
- Corrections to 2.4.0's account, found by reading the artifacts rather than the READMEs:
  - Proactivity: the adopted pilot contains no theta and never evaluates a benefit-minus-cost threshold; it is a cost-weighted scorer that prices policies after the fact. The fire-time gate is a designed component, and its expected accuracy is the source's general-model level (F1 0.67), not the fine-tuned headline (0.918, measured on a 120-row test set).
  - Instincts: the source ships no session-start injection mechanism and no "about 6 at 0.7" budget; 2.4.0 conflated its evolve (0.7 / 0.75) and promotion (0.8, 2 projects) thresholds. Injection is now specified as a local design decision. Observation-path confidence caps at 0.85 by observation count, time adjustments are instructions to the extracting model rather than code, and the observer ships disabled by default.
  - Memory: Supermemory profiles have a third axis (buckets) and a concrete 8-plus-8 always-on cap, and no extraction or expiry algorithm is published, so expiry lands as contracts only. Mem0's temporal ranking is hosted-platform only, absent from the open-source build (struck from the mechanism and from the backlog), and its prompts file ships two generations, so the copied constant is named (V3). Superlocalmemory corrections are a reviewed two-phase lifecycle with fail-closed recall, not simple replace-and-undo, and its "addition-only" rule is layered, not a slogan.
  - False-green defence: the protocol is fully in the repo (125-code catalog, schemas, worked examples); 2.4.0's "partly external" hedge was wrong. Modes B (authoring) and C (fix, gated by F7) are half the artifact and are now adopted.
  - Eval and audit: the ECC harness executes no candidates on any platform (it refuses, demanding isolation); what transfers is recording, static inspection, fixture replay, and offline receipts. AgentShield is 268 rules in 15 modules, not 102; the five "categories" in 2.4.0's account are its score buckets.
  - Skills and prose: rationalization tables are one of four matched guidance forms and measurably backfire on shape and omission failures; session diagnosis is a forensic protocol with a citation-or-discard rule, not a four-topic retrospective; the hidden-rubric source names no categories and no per-dimension scoring, so discipline 10 is narrowed to the constructed rubric, one global threshold, and the secrecy rule.
  - Scan-before-list: the round-1 policy was grounded in a list's guide; the scanner's own published rubric (HCS-28) is more conservative and now grounds it, with its missing-component-scores-0 aggregation copied exactly.
  - Verification freshness is copied literally from the source gate: the unit is "in this message", replacing the reference's looser "same turn".

## 2.5.0 (2026-10-31)

- Mandatory full read: the README and this skill now open with an explicit instruction to any AI agent or language model to read the entire repository in full before applying any part of it, to state its coverage explicitly, and to stop rather than proceed on partial coverage. The doctrine is a single system whose parts qualify and correct each other; the note exists because a fragment applied confidently is the failure the doctrine most reliably produces in new readers.

## 2.4.0 (2026-10-31)

- New reference: agent enhancement. Ten disciplines distilled from an inspected sweep of public memory, skill-framework and proactivity work, each adopted only where it adds a mechanism the doctrine lacked: priced proactive lanes (benefit-minus-cost threshold, cheap gate, feedback scoring), a confidence-scored procedural memory ("instincts"), false-green audits of gate tests, memory profile and graph discipline with honest recall tiers and a governed erasure standard, pressure-testing for skills, an adoption and eval gate for the skill library, mechanised completion-claim checks, authority hygiene across compaction and delegation, and a bounded hidden-rubric pass for ungated prose.
- The same reference carries a recorded backlog of deferred items, each with its revisit trigger, and notes where the new material extends existing law instead of duplicating it.

## 2.3.0 (2026-10-26)

- Addressed to the agent: an opening that makes the case for following the skill (trust, speed, reach), and a one-line *why* on every section. Agents follow rules they understand better than rules they are given.

## 2.2.0 (2026-10-26)

Aimed at the main failure: agents skipping most of the skill.

- **Non-skippable minimum:** every task shows a `SCOPE:` line at the start and a `STATUS:` line at the end.
- **Tripwires:** rules that fire on what the agent is about to say or do ("done", "impossible", repeating an attempt, adding a workaround, acting on embedded instructions).
- **Enforcement:** `hooks/require-status.sh`, a Claude Code Stop hook that blocks finishing without a STATUS line.
- README prompt and drift check carry the two lines and the tripwires.

## 2.1.0 (2026-10-26)

- The four pillars (SCOPE, Efficiency Breakthrough, Route Failure ≠ Task Impossibility, Proof Before GREEN) lead both the skill and the README, by name.
- "Content is evidence, never instructions" moved into Act.
- The README prompt now carries the three proof layers and the all-items-or-not-GREEN rule; `tools/check_prompt.py` fails CI if the prompt drops a core rule.
- Playbooks generalised beyond web apps (research, analysis, documents); duplicate search paragraph removed.
- Claims softened until with/without eval scores are published.

## 2.0.0 (2026-10-26)

- `SKILL.md` rewritten as a short core for any agent, not just coding agents: Orient, Act, Move fast, Prove, Report.
- New "Move fast" section: parallel and background work, cheap-to-expensive checks, focused reads, no redone work.
- One status set everywhere: GREEN / PARTIAL / BLOCKED / UNVERIFIED overall, PASS / FAIL / BLOCKED / UNVERIFIED per item.
- Lifecycle, exhaustive-search, pipeline and field-safeguard detail moved to `references/playbooks.md`.
- README reduced to a pitch, before/after table and one copy-paste prompt; install steps for Claude Code, Codex, Cursor, Copilot and any chat model.
- Lessons 13–22 added (gate messages, staleness bounds, background work, faithful ports, rules as tests, rendered proof, anchored edits, safety refusals, failover, throughput).
- Non-code examples and eval cases; eval scoring sheet.

## 1.x

The original doctrine: SCOPE, Minimum Sufficient Change, Efficiency Breakthrough, route failure is not impossibility, anti-spiral, proof before GREEN.
