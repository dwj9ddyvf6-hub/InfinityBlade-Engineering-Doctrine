# Turn a claim into a result another agent can verify

The strongest agent leaves work that survives inspection. This evaluator gives
that principle a practical instrument: declare the outcome, inspect the actual
artifact, retain every failed condition, and compare changes without hiding the
cost or the missing trials. A persuasive completion report now has a mechanical
route back to the thing it describes.

Run it immediately from the repository root:

```sh
python3 tools/evaluate_task.py check \
  --case docs/evaluation/example/case.json \
  --artifacts docs/evaluation/example/candidate \
  --task-record docs/evaluation/example/task-record.json
```

The result is `PASS`: the actual saved JSON contains three exact records, the
protected schema's SHA-256 matches, and the output inventory contains only the
two intended files. The receipt includes the bytes inspected, their hashes,
the oracle hash, the checker hash, and each expected/observed comparison.

Now change only the artifact directory to `example/baseline`. The result is
`FAIL`, exit code 1: only two of the three records were saved. The schema and
scope checks still pass, so the precise failed boundary stays visible. A
handwritten `GREEN` label cannot supply the missing record.

These are deliberately constructed examples, **not model trials or evidence of
model improvement**. They demonstrate that the instrument distinguishes a
completed save from a plausible partial save. The [research notes](RESEARCH.md)
explain the external designs and failure cases behind it.

## What this adds to the working loop

| Earlier failure | Mechanism | Observable improvement |
|---|---|---|
| “Saved successfully” was accepted without readback. | Inspect actual file content and digest. | Missing or wrong output fails the relevant condition. |
| An easy acceptance row replaced the hard requested row. | Exact acceptance ID, subject and boundary matching against an optional task record. | Dropped outcomes and adjacent proof are rejected. |
| A test emitted the right `status` field. | Re-evaluate the artifact; do not import its passing label. | A forged score cannot change a failing artifact's verdict. |
| Averages hid regressions and unfinished trials. | Predeclare pairs, retain missing/error trials, expose discordant outcomes. | Improvements, regressions and coverage remain separate. |
| A different model or budget was presented as an instruction gain. | Match model, host, tools, system, budget and seed controls. | Incomparable pairs remain visible outside the comparison denominator. |
| Missing token counts were replaced with character counts. | Explicit metric units and `null` for unmeasured values. | Cost comparisons show their own coverage. |

The checker complements [the task record](../TASK-RECORD.template.json) and
[the behavioral evaluation protocol](../BEHAVIOR-EVALUATION.md). It strengthens
the evidence for a declared local outcome; it does not force every kind of task
through a local-file interface.

## Author an outcome contract

Start with [example/case.json](example/case.json), retaining its complete shape.
The case is the oracle: review it independently before using it to select a
change. Include both the intended result and the state that must stay intact.

Each acceptance row has a stable `id`, human-readable `description`, exact
logical `subject`, `boundary: "local-artifact"`, and one or more checks.
Every row and check ID must be unique; zero checks never constitute success.

| Check kind | Required fields | What it proves |
|---|---|---|
| `json_equals` | `path`, `pointer`, `expected` | The selected JSON value equals the expected value, including nested values and types; booleans are distinct from numbers. |
| `file_sha256` | `path`, `expected` | The complete observed file has the expected SHA-256. Useful for protected state and exact-byte output contracts. |
| `text_contains` | `path`, nonempty `expected` | A literal UTF-8 substring occurs. This proves presence, never meaning or truth. |
| `path_absent` | `path` | The named path was absent at observation and readback. It is not an all-system privacy scan. |
| `inventory_equals` | `expected` relative-file array | The complete regular-file inventory of this artifact root matches the declared set. |

JSON pointers follow [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901.txt):
`""` selects the whole value, `/rows/0/id` selects an array member, `~1` encodes
`/`, and `~0` encodes `~`. Invalid escapes, unresolved selectors, duplicate JSON
keys and non-finite values cannot pass. Numeric `1` and `1.0` compare as the
same JSON number; `true` does not equal `1`.

Choose actual state, not a self-awarded grade. Checking a JSON field named
`tests_passed: true` establishes only what that file says. To prove the claim,
use an independently specified output artifact or a trusted runner's verified
record with the requested subject and execution boundary. This tool does not
authenticate external runner records or execute the commands they describe.

The optional task record must have exactly the case's acceptance IDs,
subjects and boundaries. `overall_status: "GREEN"` is checked against the
observed result; it never affects that result. Other narrative fields remain
the record author's responsibility. The root task template remains suitable
for broader work that needs a different oracle.

## Compare an improvement without concealing its cost

```sh
python3 tools/evaluate_task.py compare \
  --plan docs/evaluation/example/plan.json \
  --root docs/evaluation/example
```

The synthetic example reports one comparable pair and one `improved` outcome.
It recomputes both verdicts from the two artifact directories. It does not read
or trust a prior passing receipt. All cost means remain `null`, because no model
or timed agent run produced these example artifacts.

Use [example/plan.json](example/plan.json) as the complete machine-readable
template. List every intended `pair_id` before running the experiment. Each
pair names a case file and fixture file relative to the supplied trial-bundle
root. Their actual bytes are checked against the declared case and fixture
SHA-256 values; a changed fixture cannot be pooled with its predecessor.

Baseline and candidate trial records contain:

- A unique `trial_id`, `treatment_revision`, and `status`: `completed`, `error`
  or `not_run`. Completed trials name their artifact directory; errors and
  unrun trials retain a reason. Observed trials require a valid timestamp with
  timezone.
- The case and fixture hashes, plus identical control configuration within
  each pair: `model`, `host`, `tools_sha256`, `system_sha256`, an explicitly
  unit-named positive `budget`, and `seed` (integer or explicit `null`). The
  treatment revision is separate from these fixed controls.
- Optional measured `elapsed_seconds`, `input_tokens`, `output_tokens`,
  `tool_calls`, and `cost_usd`. Omitted/unmeasured values remain `null`.
  Counts must be integers; costs must be nonnegative and finite. Budget and
  metric values must fit the checker's finite floating-point evaluation range;
  overflowing metadata is an invalid measurement contract, not a failed task.

Different pairs may exercise different cases and fixtures. A given pair must
use the same pinned case and fixture for both variants. This permits a diverse
suite without laundering a changed test into an improvement. Different model
families belong in separate controlled comparisons; one pooled percentage is
not evidence that every family improved.

The report keeps `both_pass`, `both_fail`, `improved` and `regressed` counts,
then states the total planned, comparable and excluded/unverified pairs. The
pass-rate difference is an **absolute percentage-point change on comparable
pairs**. Each cost difference reports its own measured-pair count and missing
count. No confidence interval, causal conclusion or universal uplift is
invented. The paired protocol still needs isolation, randomization where
appropriate, independent oracle review and held-out cases.

## Interpret the result correctly

| Observation | Check result | Meaning |
|---|---|---|
| Expected output missing, wrong value, malformed produced JSON, or unexpected file | `FAIL` | The inspected output does not satisfy the declared condition. Missing expected output stays a failure. |
| Root unavailable, permission/read error, redirected/nonregular source, inspection bound exceeded, or state changed during readback | `UNVERIFIED` | The measurement cannot substantiate a verdict. |
| Every condition passes on stable observations | `PASS` | The declared local-artifact conditions are demonstrated. |
| Malformed case/plan, duplicated IDs, changed oracle/fixture identity, or incomplete task-record mapping | `INVALID`, exit 2 | Repair the measurement contract before interpreting it. |

`check` exits 0 for `PASS`, 1 for `FAIL`/`UNVERIFIED`, and 2 for invalid input.
`compare` exits 0 for a complete comparison and 1 for incomplete coverage.
**A complete comparison can show regressions or universal failure.** Its exit
code does not authorize adoption; read the outcome table.

The default per-file inspection bound is 16 MiB and can be increased with
`--max-file-bytes`; inventory checks stop above 10,000 files. These are resource
bounds, not claims that larger artifacts are invalid. Freeze writers before
collecting release evidence: repeated hashing detects observed changes but is
not an atomic filesystem snapshot. Use a controlled artifact directory rather
than a home directory or live data store. Reports can contain small expected
and observed values, so select public fixtures for public evidence.

The evaluator writes JSON to stdout and performs no commands, imports from
artifact files, network calls, model calls, or host installation. Save output
outside the checked artifact root so the receipt does not alter the inventory
it is measuring. Hashes bind bytes; they do not authenticate a producer. For
signed build provenance or live service effects, use the stronger verification
appropriate to that boundary.
