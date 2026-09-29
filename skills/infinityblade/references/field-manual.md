# InfinityBlade Field Manual

Use this manual for incidents, multi-stage integrations, automation pipelines, deployments, performance failures, and tasks whose first route failed.

## Build the evidence map

```text
Requested outcome:
Authorized surface:
Protected invariants:
Known execution path:
Success evidence:
```

Map the path as boundaries where evidence can be observed. Locate the **first failed boundary**; later symptoms are not automatically root causes.

## Maintain an evidence ledger

```text
Hypothesis:
Action:
Expected discriminator:
Observed evidence:
Conclusion:
Next uncertainty:
```

An action is useful when it solves the problem or reduces uncertainty. Output volume, elapsed time, and command count are not progress measures.

## Find an Efficiency Breakthrough

1. Measure the complete path under representative conditions.
2. Attribute delay, cancellation, contention, or failure to individual stages.
3. Rank stages by contribution to the end result.
4. Repair or remove the dominant constraint.
5. Rerun the same complete measurement.

Prefer a structural correction that collapses the bottleneck over optimizations spread across non-governing stages.

## Recover from route failure

Classify the failure: implementation defect, incorrect hypothesis, tool or transport failure, missing dependency, permission boundary, external failure, or missing user choice.

State what the failure disproves. Then choose the safest alternative route that provides the most information per action. Stop when new authority is required, risk changes materially, or reasonable authorized routes are exhausted.

## Run the anti-spiral reset

Reset when a failure class repeats without a revised hypothesis, the touched surface keeps expanding, new infrastructure appears before the defect is located, or the next action has no evidentiary purpose.

```text
Known facts:
Unproven assumptions:
Last new evidence:
First failed boundary:
Protected working state:
Smallest next discriminating check:
```

## Verify the final system state

Verification depth follows the claim. For end-to-end claims, exercise the end-to-end route. Provider acceptance is not destination receipt. Deploy-command success is not runtime health. Schedule existence is not completed execution.

Any material post-verification change invalidates the affected proof.

