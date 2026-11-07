# Operating paths: from a request to a demonstrated result

Use this guide after [the primer](../PRIMER.md) and [the core](../skills/infinityblade/SKILL.md). The core governs; this guide makes the route concrete. It adds no permission to deploy, trade, contact someone, publish private information or operate a live account.

## Choose the smallest complete route

| Requested outcome | Load next | Required closing evidence |
|---|---|---|
| Repair a local function or library | Field manual; gate-test-integrity when a regression gate is used | Reproduced defect, discriminating regression, final source identity |
| Deliver a deployed workflow | Playbooks; live-execution-proof | Authorized deployment identity and observed effect through the real entry point |
| Inspect a completion claim | Review mode; claim-verification-ledger | Opened artifact, checked identifiers, every requested row reconciled |
| Find everything or establish absence | Absence-proof-coverage-ledger | Finite corpus, search families, pagination, excluded/unavailable rows |
| Save, export, push or delete | Save-readback-verification | Destination read-back at the promised durability boundary |
| Change a canonical source or producer field | Single-door-consumer-audit and persisted-field-consumption-audit | Exhaustive consumer inventory and each consumer's disposition |
| Build agent memory or operations | Agent-enhancement reference and systems operator guide | Module proof, actual caller, host receipt, named unimplemented contracts |
| Analyze charts, stocks or daily backtests | Relevant specialist folder from the index | Declared dependencies, data identity, method provenance, bounded domain verdict |
| Evaluate or modify the doctrine | Whole-repository pinned read ledger and behavior evaluation guide | Exact coverage, source checks, regression evidence, unmeasured claims labeled |

“Smallest” means no unnecessary machinery. “Complete” means no requested outcome disappears. If a task crosses two rows, combine their evidence requirements rather than substituting one for the other.

## Establish a portable host contract

Before the first consequential action, resolve the actual tools available in this session. Historical tool names in specialist skills are examples of capabilities, not commands that every host possesses.

| Needed capability | Portable behavior | Host check |
|---|---|---|
| File search/read | Locate the authoritative path, then read the relevant content | Resolve workspace roots and repository instructions; preserve encoding and provenance |
| Command execution | Run a bounded process and capture exit status and output | Use the advertised executor; never invent `muse.*` tools on another host |
| Source research | Read primary sources and retain exact locators | Distinguish fetched content, index snippets, inaccessible pages and unverified claims |
| Images/UI | Inspect the actual output at the requested boundary | A source file or generated path is not a viewed image |
| Durable mutation | Read back the exact destination object | Know whether the tool saved locally, queued remotely or committed durably |
| Background work | Checkpoint and supervise observable progress | Tool/session lifetime, restart behavior and resource ceilings are explicit |
| Messaging/economic effect | Use only the authorized account and effect path | A repository procedure never grants missing authority |

If a host lacks a capability, use an authorized equivalent with the same contract or report the exact missing boundary. Do not install a service, broaden permissions or manufacture a result to make the guide appear portable.

## A task record that survives handoffs

Copy [TASK-RECORD.template.json](TASK-RECORD.template.json) into the task's authorized state area. The repository itself is not the default home for private task records. Small tasks may use the same fields as a short note; the contract matters more than the file format.

1. Preserve the request and constraints in the user's terms. Write acceptance rows as outcomes, not implementation steps.
2. Bind each row to a subject and boundary: local file, function, integration, deployed service, published document or authoritative remote object.
3. Capture two material routes and their cheapest discriminator. A routine deterministic edit does not need invented architecture alternatives; compare the relevant repair paths.
4. Record evidence identity: exact artifact/revision, inputs, environment, observation time, expected and observed result, locator, and limitations.
5. Keep each unresolved obligation open. Delegation changes ownership, not scope or the definition of done.
6. Read back the record after saving it. On resume, inspect the actual artifact and canonical authority; a summary carries context but cannot grant new permissions.

The example values are placeholders, not receipts. Never cite the template as proof that a task happened.

## Worked path 1: repair a deterministic function

**Request:** the parser rejects valid leap-day dates. Preserve the existing API and invalid-date behavior.

**SCOPE:** parser and focused regression · API and rejection behavior preserved · valid leap day accepted, invalid dates rejected.

**Routes:** patch the date validator or normalize input before validation. The discriminator is a minimal valid input that bypasses normalization and still fails inside the validator. Repair that cause; preserve the failing input as an independent oracle.

**Acceptance:** a valid leap-day example passes; a non-leap-year look-alike fails; existing supported formats remain valid. A function-level claim can be GREEN after the discriminating test and relevant regression checks on the final tree. No deployment or external mutation is required because the requested deliverable is a local function change.

**Receipt shape:** `subject=parser`, `boundary=function`, `revision=<final tree hash>`, `expected=<declared cases>`, `observed=<runner result>`, `evidence=<saved output>`. If the user also asked for the service to be deployed, retain a separate deployment row; function proof cannot close it.

## Worked path 2: review “the export is complete”

**Request:** verify a worker's claim that all source records were exported.

Start with the claim, its source manifest and the destination identity. Open the destination itself. Reconcile record counts, stable identifiers, required fields and representative payloads; verify hashes when byte preservation is required. Check pagination and any skipped/error rows. A success exit code proves the command completed, not that the destination has every record.

**Counterexample:** a file contains the expected row count but duplicates one identifier and omits another. Count equality passes; identity reconciliation fails. Preserve this as the regression case.

**Verdict:** the verified subset may be PASS while the whole export remains PARTIAL. If the destination cannot be read, name that missing read-back as UNVERIFIED or BLOCKED rather than repeating the worker's report. Restoration is a further acceptance row when recoverability was promised.

## Worked path 3: add a durable effect queue

**Request:** keep authorized notifications from being lost or duplicated during restarts.

Read enhancement disciplines 13–16 and the systems operator guide. Use temporary state to exercise enqueue, restart, later/deferred outcomes, due-time backoff, competing claimants and generation-bound settlement. The local package test proves only the tested queue contracts.

Then wire the queue before the existing authorized send boundary. Supply receiver idempotency, deduplication or authoritative reconciliation. Inject a crash after receiver acceptance and before local settlement; resume and prove the receiver effect was not duplicated. A durable queue alone cannot earn an exactly-once external-delivery claim.

**Evidence layers:** specification inspected → source present → local contract tested → real caller verified → receiver receipt observed. Each layer has its own status. If only temporary-state integration was authorized, report that boundary; do not send a real message merely to improve the verdict.

## Worked path 4: research with incomplete access

**Request:** find all published implementations of a named method.

Define the bounded corpus: official project, release tags, package registries, fork network, papers and dated search routes. Track searches, pagination, exclusions and unavailable sources. Read source artifacts before attributing behavior; a README is a project's claim, and a passing local fixture is stronger evidence only for the tested path.

**Counterexample:** a repository returns 404 because the URL moved. This proves that URL failed; it does not prove the implementation was never published. Follow canonical project references and authorized registry routes, retaining the failed route in the coverage record.

**Report:** “No implementation found in the sources checked as of <date>; <rows> remain unavailable.” An honest bounded result is useful. A universal absence statement requires coverage that can actually support it.

## Keep five evidence states separate

| State | What it supports | What it does not support |
|---|---|---|
| Source inspected | The current artifact contains a design or implementation | Execution, correctness or adoption |
| Local contract tested | Named behavior passed on recorded inputs and revision | Uncovered cases, host wiring or external effects |
| Host integration observed | A real entry point called the mechanism under recorded conditions | All routes, all users or indefinite future health |
| External effect confirmed | Authoritative receiver state/receipt matches the intended effect | Unrelated effects or universal exactly-once behavior |
| Behavioral improvement measured | A named model/harness improved on a declared evaluation | Every model, task or future version |

This matrix prevents “written,” “tested,” “wired,” “live” and “better” from collapsing into one claim. Stronger claims need stronger evidence; ordinary local claims do not need unrelated live actions.

## Specialist craft remains specialized

The financial skills retain their complete methods, examples and account safeguards. They are not generic prerequisites for every agent task. Chart geometry depends on an external TA engine and render assets; backtest cross-checking depends on an independent oracle. The Alpaca package includes guarded transport capabilities, while its named skill activates for paper-account work. Reading or installing any of these grants no trading authority.

The memory and operations packages are reusable mechanisms, not a replacement system of record. Adapt them to an existing canonical store. Ordinary supersession preserves history; authorized privacy erasure removes sensitive content across derived copies and retains a non-sensitive receipt. These are different operations and must remain different.

## Close without losing the remaining work

Report the outcome first, then the exact scope of proof and open acceptance rows. Include only the evidence needed for the reader to verify the claim. Save the next action, owner and reopening condition for unfinished work. GREEN is earned at the requested boundary; a clean source check, a fluent report or a complete template cannot earn it by itself.
