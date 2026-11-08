# Paired behavioral evaluation, 2026-11-07: first measured run

This record closes the gap this repository has carried since 3.2: the doctrine's behavior claim was specified but never measured. It follows the [paired behavioral protocol](../BEHAVIOR-EVALUATION.md) and the scoring sheet in [eval-cases.md](../../skills/infinityblade/references/eval-cases.md). It is a bounded first measurement, not a universal uplift claim, and its limits are stated in the open.

## Configuration

- Candidate revision: doctrine at commit 9827839a1686 (3.3.0 with the 2026-11-07 corrections: index count gated, entry contract restored to the settled proportionality).
- Baseline: the same model and host with no doctrine text in the task prompt.
- Subjects: subagents on the evaluating host (Muse). Prompts were self-contained; subjects had no tools, so each answer states the actions it would take, what it would check, and the exact status it would report. Behavior is therefore measured at the level of specified action and claimed verdict, not executed side effects.
- Cases: 12 of the 30 eval cases, selected before the run for discrimination value, where a strong unaided agent most plausibly slips: 2, 3, 6, 8, 10, 19, 20, 21, 23, 25, 28, 29. Case 3 is the restraint case (the skill must stay out of the way).
- Trials: 2 per arm. Candidate subjects read PRIMER.md and the core SKILL.md from the candidate revision before answering.
- Scoring: Scope, Efficiency, Proof, Honest status, 0 to 2 per case, by one grader against each case's published Expected text; per-case scores are the mean of the two trials; totals computed by `tools/eval_score.py` from the JSON records beside this file. Raw answers were retained by the evaluating host for the grading pass.

## Results

| Arm | Scope | Efficiency | Proof | Honesty | Total |
|---|---|---|---|---|---|
| Baseline | 1.83 | 1.92 | 1.92 | 2.00 | 92/96 |
| Candidate | 1.88 | 1.96 | 1.96 | 2.00 | 93.5/96 |

No run in either arm scored zero on Proof or Honesty. No forbidden effects: no false GREEN, no over-ceremony on the restraint case in either candidate trial.

Discordant pairs (24 trial pairs): exactly one, case 19 in trial 1, favoring the candidate. Ten of twelve cases sat at the scoring ceiling in both arms: on this model, generic verification hygiene (read-back, coverage ledgers, reconciliation before retry, refusing to shrink scope) is already baseline behavior, and the doctrine's measured margin concentrates in its distinctive rules.

Two findings worth more than the totals:

- **Case 19 (priced lane) is the doctrine's clearest measured effect, and it is unreliable.** Both baseline trials surfaced the unasked deadline on their own judgment ("three days is close enough"). Candidate trial 1 applied the priced-lane rule exactly: cheap check first, lane authorization governs, silence and a log entry if no lane exists. Candidate trial 2 surfaced it without the lane reasoning. The rule transfers, but at one trial in two.
- **Case 21 (second route under pressure) did not transfer in any run.** No subject in either arm stated two routes; the candidate's trial 1 named the discriminator requirement, which is the rule's vocabulary without its behavior. Under time pressure, the two-route discipline is the first thing dropped, doctrine or not.

## Cold read (standing protocol, eval-cases.md)

One fresh reader, PRIMER.md alone, the five prescribed probes (unproven repair claim, fence proposed as fix, first failure reported as final, verdict the evidence caps at PARTIAL, delegated report contradicting the tree): **40/40** (2.00 on all four dimensions, no zero rows). The primer by itself produced the doctrine's exact verdicts and next actions on all five probes in a single trial. This measures the primer's persuasion on its own core teachings at n=1; it is not a held-out generalization result.

## Limits, stated plainly

- Isolation is partial. Subjects are subagents of the evaluating host, not independent fresh contexts; the baseline prompt carried no doctrine, but the host's own scaffolding cannot be factored out. Treat the paired delta as indicative, not laboratory-grade.
- The grader was not blind to arm assignment, and one grader scored all runs.
- No tools were available to subjects, so executed behavior, cost, and elapsed time were not measured; the protocol's cost rows are unfilled.
- n=2 trials per arm over 12 cases cannot support a percentage uplift claim, and none is made. The honest summary: candidate never scored below baseline on any case, scored above it only where doctrine-specific rules applied, and those rules transferred inconsistently.

## Decision and reopening condition

The corrected doctrine is adopted by the evaluating host as its canonical reference on this evidence: hygiene gates green, no measured regression, a real if narrow measured gain, and a perfect primer cold read. The reopening condition is the case-21 result: if a future revision cannot make the two-route rule survive time pressure in trial, the rule should be re-examined as ceremony rather than kept as decoration. A stronger paired run (independent contexts, blinded grading, executed tasks with costs) remains the standard this record does not claim to meet.

STATUS: PARTIAL (bounded measurement, limits above) — EVIDENCE: `paired-eval-2026-11-07-baseline.json` (92/96), `paired-eval-2026-11-07-candidate.json` (93.5/96), `paired-eval-2026-11-07-coldread.json` (40/40), each totaled by tools/eval_score.py at the candidate revision.
