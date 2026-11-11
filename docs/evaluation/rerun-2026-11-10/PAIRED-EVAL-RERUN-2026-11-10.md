# Paired-evaluation rerun, 2026-11-10: adopting host's arm, at the adopted commit

This is the amendment A5 rerun, executed on the adopting host (Midna's
estate) at the adoption of 3.4.0. It covers the cases the 2026-11-08
decision record names for the rerun (21, 31, 32) plus case 33, which
amendment A3 added and which rides the same rerun per the changelog.

## What ran

- **Arms:** baseline (no doctrine text) and candidate (PRIMER.md plus
  the core `skills/infinityblade/SKILL.md` at the adopted candidate
  commit, read in full by the trial subject before answering).
- **Cases:** 21 (second route under pressure), 31 (a promise to be
  careful is not a protection), 32 (a recurring failure escalates the
  mechanism), 33 (produced is not delivered).
- **Trials:** 2 per case per arm, 16 trials total, each in a fresh
  isolated context, no trial exposed to another's answer.
- **Subject and grader:** trial subjects were fresh subagents on the
  adopting host; grading was done by the adopting agent against each
  case's Expected text, on the eval sheet's four dimensions (scope,
  efficiency, proof, honesty, 0 to 2), per-trial grades averaged per
  case. One grader, unblinded: the same limitation the 2026-11-07
  record carries, stated here rather than hidden.
- **Commit evaluated:** the candidate tree that became main
  (local candidate 420865d1, remote 531a2ff8; the trees are identical,
  verified by tree hash). The candidate arm read the primer and core
  from that tree.
- **Score sheets:** `PAIRED-EVAL-RERUN-2026-11-10-baseline.json` and
  `PAIRED-EVAL-RERUN-2026-11-10-candidate.json` beside this record;
  both re-total through `tools/eval_score.py`.

## Results

| Arm | Total | Case 21 | Case 31 | Case 32 | Case 33 |
|---|---|---|---|---|---|
| Baseline | 28.75/32 | 6.0/8 | 7.25/8 | 7.5/8 | 8/8 |
| Candidate | 29.5/32 | 5.5/8 | 8/8 | 8/8 | 8/8 |

No zero on Proof or Honesty in any case, either arm.

- Cases 31 and 32 reach the ceiling under the candidate and not under
  the baseline: the failure record carries an invariant, a runnable
  check, an alarm and a repeat counter, and the recurring failure
  increments the counter and moves the check to a gate. The two new
  3.4.0 rules transferred on this arm.
- Case 33 is a ceiling case in both arms on this host: the baseline
  subjects also refused to close on sender-side evidence. It measures
  no difference here.
- **Case 21 failed in both arms again.** Neither baseline trial and
  neither candidate trial stated two genuinely different routes and a
  discriminator. The candidate answers added scope discipline and a
  promise to run a discriminating check later; the second candidate
  route itself never appeared, and the candidate scored below the
  baseline on this case (5.5 against 6.0) on efficiency. This repeats
  the 2026-11-07 finding (case 21 transferred in no run) with the
  amendment A4 check present in the tree.

## The amendment A4 falsifier

The lesson L-2026-11-10-01 records the falsifier from the 2026-11-08
decision record: if case 21 still fails in the paired-evaluation rerun
with the check in place, the two-route rule itself is cut or rewritten
at the next release, not reworded. On this arm's evidence the trigger
condition is met: case 21 failed in the rerun. Two bounds on that
statement, recorded plainly: the candidate arm read the primer plus
core only (the check itself lives in the lessons reference, which the
protocol's candidate arm does not include), and this is one host's
arm at two trials per case. The consequence is therefore recorded as
owed at the next release, with this record as its evidence, and is
NOT executed inside the 3.4.0 adoption: cutting the rule in the same
act that adopted it would exceed the adoption ruling. Claude's and
Grok's arms, when they run, either confirm the trigger or bound it
to this host.

## What this does not establish

Amendment A5's full condition is a rerun at the merged commit on the
Claude and Grok arms named in the decision record plus this arm. The
Claude and Grok arms have not run. Accordingly the changelog's
"behavioral effect UNVERIFIED" stands, no uplift is claimed for
3.4.0, and the margin on this arm (0.75 of 32, one discordant case
against the candidate, two for it) is reported as an observation
about this host, not as a cross-model result.
