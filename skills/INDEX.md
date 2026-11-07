# Skills Library Index

This folder carries installable craft beside the doctrine skill: complete skill folders, taken as they are used, not descriptions of them.

**Install contract, stated honestly:** take any folder as-is. Twenty folders are complete: full SKILL.md text and every supporting file the skill needs to run. Two folders carry named external dependencies, stated in their rows and in their own text: chart-read invokes a render script and a synthesis document that live with the adopter, and its bin/pass_a.py imports `core.ta_battery` from the checkout named by `CHART_READ_TA_REPO` (not bundled), and stock-analysis runs its Pass A from the chart-read folder, so those two install together. A contract that claims completeness its own folders falsify would fail this library's own read-back test, so the exceptions are named here, at the promise, not buried in the folders. Where a skill needs a credential, a path, or a document of yours, it names an environment variable or a placeholder, never a value.

**Start with these three.** proof-before-green (the verdict discipline every other skill reports under), gate-test-integrity (the gate honesty the verdict depends on), and claim-verification-ledger (the ledger that keeps delegated and saved claims honest). Install those first; add the rest when a task names their surface.

The doctrine skill itself lives at [infinityblade/](infinityblade/) and is not part of this index; it is the rule source the library operates under.

## The library: 22 skills, 65 files

| Skill folder | Files | Purpose | Disposition |
|---|---|---|---|
| [alpaca-paper/](alpaca-paper/) | 16 | Trade and inspect Alpaca paper trading accounts with the account identity proven from the configured credentials before any account-level action. | Generalized: credentials re-pointed to environment variables; the credential file never lands |
| [chart-read/](chart-read/) | 4 | On-demand chart reading: deterministic Pass A geometry, then a perceptual Pass B read with scenarios, triggers, and invalidation. | Generalized: private paths and names replaced with environment variables and placeholders; depends on `core.ta_battery` via `CHART_READ_TA_REPO` (not bundled) |
| [stock-analysis/](stock-analysis/) | 4 | Full stock analysis and chart reading in one protocol: Pass A geometry, Pass B read, strategy lenses, market context, rigorous synthesis. | Generalized: local paths and private context replaced with placeholders; fragments land whole |
| [backtest-crosscheck/](backtest-crosscheck/) | 1 | Cross-check a daily-bar mechanical backtest headline against a second, independent oracle engine before the result is reported or acted on. | Generalized: the standing ruling re-attributed to the adopting project; the oracle is a declared external dependency, not bundled |
| [conviction-surface-definition/](conviction-surface-definition/) | 1 | Define what a ranking, board, or summary surface is and where its conviction is formed before building it. | Complete |
| [doctrine-provenance-check/](doctrine-provenance-check/) | 1 | Audit every veto, filter, and gate against stored doctrine and its provenance before it blocks anything. | Complete |
| [hermetic-test-isolation/](hermetic-test-isolation/) | 1 | Make regression tests prove the same verdict alone, in the full suite, and in a clean export. | Complete |
| [rea-teardown/](rea-teardown/) | 1 | Tear down a tool with REA reverse engineering, handling evidence so large bundles never break a backup or a public save. | Complete |
| [single-door-consumer-audit/](single-door-consumer-audit/) | 1 | Enumerate every consumer of a canonical source by exhaustive search and prove each rerouted, exempt, or off-engine. | Complete |
| [stable-tree-gate-integrity/](stable-tree-gate-integrity/) | 1 | Keep gates, commits, and dry-runs honest on a tree that background loops rewrite continuously. | Complete |
| [absence-proof-coverage-ledger/](absence-proof-coverage-ledger/) | 1 | Prove absence separately, with a coverage ledger, before reporting any not found or cannot be done verdict. | Complete |
| [claim-verification-ledger/](claim-verification-ledger/) | 1 | Verify absence claims, save claims, and delegated results against the artifact before repeating them as fact. | Complete |
| [gate-test-integrity/](gate-test-integrity/) | 1 | Keep regression gates and blocker tests honest when the tree moves during the run. | Complete |
| [judgment-provenance-check/](judgment-provenance-check/) | 1 | Check the provenance and formation point of any ranking, verdict, veto, or invalidation before it is built or spoken. | Complete |
| [literal-scope-and-silent-checks/](literal-scope-and-silent-checks/) | 1 | Execute short, scoped, or negative instructions literally, and run recurring checks silently. | Complete |
| [live-execution-proof/](live-execution-proof/) | 1 | Prove a system works on its live path, not from its component tests. | Complete |
| [persisted-field-consumption-audit/](persisted-field-consumption-audit/) | 1 | Audit every consumer of persisted producer fields before calling a migration to a canonical source complete. | Complete |
| [proof-before-green/](proof-before-green/) | 1 | Prove gate verdicts and live claims on the final tree and the final live state before reporting green. | Complete |
| [save-readback-verification/](save-readback-verification/) | 1 | Verify saves, backups, pushes, exports, and deletions by reading them back at the destination. | Complete |
| [efficiency-breakthroughs/](efficiency-breakthroughs/) | 1 | Pipeline mechanics for complete reads, bulk transport, rate limits, caches, watchdogs, seam validation, freshness, and reconciliation, each distilled from an incident where it was learned at cost. | Complete |
| [agent-enhancement-systems/](agent-enhancement-systems/) | 20 | Runnable mechanisms for the agent-enhancement disciplines: proactive pricing and gates, instincts, profile-plus-graph memory with honest recall, the skill laboratory and evidence capsules, authority handoffs, rationale records, freshness, outbound gating, deterministic IDs, a durable effect queue, owner routing, near-miss learning, and content-bound approvals, with templates and a package test. | Complete: Python standard library only; host state lives outside the folder |
| [memory-recall-systems/](memory-recall-systems/) | 4 | Design, repair, or audit an agent's memory, recall, context discipline, and long-job resource bounds: hybrid search over the markdown estate under a forced search rule, a canary eval on the agent's own history, masking over summarising, delta-only summaries, invalidate-never-delete, decay-ranked forgetting with write-gating, and checkpointed, memory-bounded long jobs, with the research report the skill distils. | Complete: Python standard library only; the full research report ships in the folder |

Every landed SKILL.md carries the same frontmatter shape: name (its folder name), a one-sentence description, and version 1.0.0, the library's first public version. Host metadata files from the source library do not land; their names and descriptions are folded into that frontmatter. Runtime artifacts (lock files, bytecode caches) never land.

## Recorded overlaps, with precedence (3.1.0)

Overlap is resolved by precedence, never by carrying the same law twice and hoping the copies agree.

- proof-before-green owns the verdict discipline only; gate mechanics live in gate-test-integrity and hermetic-test-isolation, live-path proof in live-execution-proof. proof-before-green routes to them and restates none of them.
- judgment-provenance-check is the routing checklist for its cluster; conviction-surface-definition governs surface definition, doctrine-provenance-check governs veto audits. Precedence is stated inside judgment-provenance-check.
- absence-proof-coverage-ledger is canonical for absence claims; claim-verification-ledger governs the wider claim set and routes absence claims to it. save-readback-verification is canonical for the save half of that ledger.
- single-door-consumer-audit and persisted-field-consumption-audit share the consumer-audit core and both land whole: the first governs doors (canonical sources), the second governs fields (persisted producer output); a task touching both runs both.
- memory-recall-systems and agent-enhancement-systems overlap on recall and both land whole: the systems package owns the runnable mechanisms for the wider enhancement disciplines; memory-recall-systems owns the memory architecture evidence and its canary contract governs how recall is measured. A task touching recall runs both.

## Excluded, with reasons

Two source folders do not land. The exclusions are decisions, not omissions.

- A patient appointment-text skill (2 files): a private life workflow built around one employer's scheduling system and patient phone numbers. Generalizing it would still publish the shape of a private working life, and stripped of that context the remainder is not a usable skill.
- A recovered-notes archive (19 files): by its own header, 17 unverified, possibly out-of-date recovered notes flagged compare-before-use. It is an archive, not an installable skill, and landing it would publish unverified instructions under this library's name. If a future pass verifies an individual note, that note lands then as its own skill through its own review.
