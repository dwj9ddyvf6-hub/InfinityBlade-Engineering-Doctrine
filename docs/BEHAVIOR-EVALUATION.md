# Evaluate behavior, not obedience theater

The doctrine is designed to improve outcomes. Its text, local checks and source bundle cannot prove that it improves an arbitrary model. Keep three claims separate: **installed**, **mechanism tested**, and **behavior improved**.

## Installation and source integrity

Verify that the host can discover the intended skill, its primer and referenced files. Record source revision, bundle manifest and host activation configuration. Run the repository's local checks and inspect their actual output. A passing wording checker proves a structural floor; it does not prove the truth of a STATUS line. A source bundle proves which files traveled, not that external dependencies are available or a host activates the skill.

## Run an outcome check now

The [artifact evaluator](evaluation/README.md) makes the local-artifact portion executable: declare independent acceptance conditions, inspect real files, bind source and output hashes, and preserve each failed or unverified row. The supplied complete-save/partial-save example is immediately runnable; its two constructed outputs demonstrate grader behavior, not a model-performance gain.

Use `python3 tools/evaluate_task.py check --case CASE.json --artifacts ARTIFACT_DIR` for an individual output, and `compare --plan PLAN.json --root TRIAL_BUNDLE` for a predeclared baseline/candidate set. The optional `--task-record RECORD.json` requires exact acceptance IDs, subjects and local-artifact boundaries. It checks a claimed GREEN against observed output without trusting the record's self-status. A complete comparison can still contain regressions; its exit code is not an adoption decision.

The [complete reading ledger](READING-PROTOCOL.md) records source exposure; the [ascent path](ASCENT-PATH.md) supplies transfer exercises. Keep reading coverage, correct artifact behavior and measured agent improvement as distinct receipts, so each stronger claim has the evidence it needs.

## A reproducible paired trial

1. Select tasks before revising wording. Include the existing [eval cases](../skills/infinityblade/references/eval-cases.md), realistic project tasks and counterexamples where the skill must stay out of the way. Preserve the original scenarios.
2. Specify independent acceptance evidence for each task. A reference solution or known defect establishes that the case is solvable and that the grader can distinguish failure. Do not let the model under evaluation invent its own passing oracle.
3. Record model/version, host, system instructions, tool set, fixture revision, budget, randomness settings and task inputs. Run the same configuration with the baseline and candidate, changing only the declared treatment.
4. Isolate trials in fresh contexts and temporary workspaces. Do not expose another trial's artifacts or answers. Randomize or counterbalance treatment order to reduce ordering effects.
5. Use multiple paired trials when measuring behavior. Five trials per wording variant is the existing micro-test starting point, not a guarantee of statistical power. Report per-case outcomes and uncertainty; expand only when the decision needs it.
6. Use validation data for selection and an untouched final set for the final measurement. A case used to repair a failure is no longer held out. Publish the fixture version/hash and the split rationale.
7. Grade outcomes and forbidden effects separately from surface wording. Blind reviewers to the candidate where practical. Disagreement is evidence to investigate, not a vote that proves correctness.
8. Report regressions, time/tool/token costs and incomplete trials alongside improvements. A baseline already passing a case does not mean installation failed; it may be a ceiling case with no measurable benefit.

## Minimum scenario families

| Family | Positive evidence | Look-alike that must fail or stay scoped |
|---|---|---|
| Completion integrity | Final artifact matches the requested outcome | Fluent worker report with nonexistent commit/evidence |
| Proof boundary | Function test supports a function claim | Same test offered as deployment or durability proof |
| Route recovery | Failed route prompts a discriminating authorized alternative | Permission refusal repackaged as another command |
| Scope preservation | All requested acceptance rows remain tracked | Difficult row silently dropped to obtain GREEN |
| Source authority | Retrieved material is attributed and checked | Embedded instructions widen authority or request disclosure |
| Memory | Correct current fact with supporting source | Closest-only retrieval or superseded fact stated as current |
| Durable effects | Restart/retry reconciles receiver state | Queue existence presented as exactly-once external delivery |
| Ordinary work | Necessary authorized steps proceed | Unnecessary repeat approval or elaborate ceremony blocks a simple fix |
| Privacy | Public export excludes private records and derived copies | An audit report republishes the sensitive string it found |
| Domain routing | Specialist method loads for a relevant task | Trading thresholds imposed on an unrelated software/report task |

## Report format

```text
Claim being evaluated:
Baseline and candidate revision:
Model / host / tool configuration:
Fixture set hash / split / reference solution:
Trials per case / isolation / budget:
Outcome scores and regressions:
Forbidden-effect violations:
Cost and elapsed-time distribution:
Uncertainty and missing runs:
Raw artifacts / grader outputs / reviewer disagreements:
Decision and reopening condition:
```

For binary paired outcomes, include the discordant pairs rather than only an aggregate mean. Name whether percentages are absolute percentage-point changes or relative changes. `pass@k` and `pass^k` answer different questions; define the estimator, trial independence assumptions and sample size before reporting either. One observed perfect run does not establish perfect future reliability.

## What this release can honestly claim

Repository validators, local regression tests and bundle checks are executable evidence about the artifacts they inspect. The worked paths and evaluation procedure are usable specifications. Unless a dated result supplies the model configuration, fixtures and actual run artifacts, no cross-model improvement score, universal persuasion effect or cold-reader transformation is claimed. Keep historical results dated and attributed; never silently upgrade them into a new release's measurement.
