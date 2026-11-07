# Research: make the evidence harder to fake and easier to use

Research date: 2026-11-07 UTC. This second-pass study adds five primary web
sources and four pinned source-file inspections across three external
repositories to the earlier [repository-design research](../research/2026-11-07-agent-repository-design.md).
The exact inspected portions, source revisions and byte hashes are in
[SOURCES.json](SOURCES.json). No external framework was installed, no external
code was copied into the implementation, and no model trial was run.

## Separate a wrong result from an unavailable measurement

Inspect's [scoring policy](https://inspect.aisi.org.uk/scoring-policy.html)
distinguishes an incorrect response, a scorer malfunction and an unscored
sample. They affect denominator coverage differently. Its
[error-handling guidance](https://inspect.aisi.org.uk/handling-errors.html)
also preserves partial results and warns that retrying a log can execute code
and use settings named by that log. The inspected
[scoring entry point](https://github.com/UKGovernmentBEIS/inspect_ai/blob/aa934845905492fc13935f37a811a36bae64dfb7/src/inspect_ai/scorer/_score.py)
retains per-scorer evidence and target context.

**Adoption here:** missing required output and malformed produced JSON are
failed outcomes; an unreadable artifact root is an unavailable observation.
Every predeclared pair remains visible. The local checker executes no code
from records and re-reads actual artifacts instead of trusting imported
scores. A comparison with incomplete coverage is explicitly `PARTIAL`.

## Judge the requested final state, while preserving constraints

The pinned [τ²-bench evaluation guide](https://github.com/sierra-research/tau2-bench/blob/033bf082f48e4a3c6a1256208e93cf2ce9c3bb6f/docs/evaluation.md)
explains that reference actions often derive a target state rather than
prescribe the only allowed trajectory. Its
[evaluator](https://github.com/sierra-research/tau2-bench/blob/033bf082f48e4a3c6a1256208e93cf2ce9c3bb6f/src/tau2/evaluator/evaluator.py)
combines the task's declared reward components and rejects a requested
component that was not evaluated. Some framework-specific defaults, such as
a neutral reward when no criteria exist, depend on that framework's context.

**Adoption here:** acceptance conditions describe actual output and protected
state. They do not demand a particular sequence of tool calls. Every declared
condition is retained, and an empty local oracle is invalid. This preserves
useful agent autonomy while keeping the requested result testable.

## Keep repair and preservation evidence separate

The inspected [SWE-bench grading implementation](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/swebench/harness/grading.py)
tracks fail-to-pass and pass-to-pass results separately. Its log validity
checks address a concrete false-positive mechanism: a suite that did not run
must not be mistaken for a resolved task. It also cross-checks some apparently
passing logs against command exit status. Its framework-specific handling of
empty metric sets is not a generic proof rule.

**Adoption here:** outcome checks and protected-state checks are both explicit.
The paired report displays improvements and regressions instead of only a net
average. No observed pair means a null rate, not perfect performance. A
`COMPLETE` comparison means its planned pairs were measured; it does not mean
the candidate improved.

## Challenge sequences, not only isolated happy paths

[Hypothesis's stateful-testing documentation](https://hypothesis.readthedocs.io/en/latest/stateful.html)
shows how operations can be chained and checked against a simpler model. Its
worked database example preserves a short action sequence that reproduces a
failure, and invariants can run after every transition.

**Adoption here:** tests include source mutation between first read and
readback, a forged passing label over a wrong artifact, a changed fixture, an
unexpected output, duplicate identities, missing planned pairs and a
configuration change. These are explicit deterministic counterexamples. The
new checker does not claim exhaustive state-space exploration or introduce a
Hypothesis dependency.

## Make selectors and provenance precise

[RFC 6901](https://www.rfc-editor.org/rfc/rfc6901.txt) defines JSON Pointer
escaping, object selection and array indices. Duplicate members make object
selection ambiguous, and a nonexistent pointer target is an error.

**Adoption here:** the evaluator implements exact pointer decoding, refuses
duplicate JSON keys, preserves boolean/number distinctions, rejects non-finite
numbers and reports missing selectors as failed output conditions. A literal
text check is labeled as presence evidence, never a semantic judgment.

[SLSA's artifact-verification guidance](https://slsa.dev/spec/v1.2/verifying-artifacts)
distinguishes provenance inspection from simply possessing provenance. Its
verification model includes identity, signatures, expected parameters and
roots of trust.

**Adoption here:** reports identify case, checker, fixture and observed artifact
bytes. Paired comparison verifies fixture bytes and fixed configuration
records. These are inspectable digest bindings, not signed attestations or
proof of producer identity. Stronger identity and live-execution claims remain
with their appropriate verifier.

## The resulting capability

The [runnable guide](README.md) turns this research into a direct loop:
author a case independently, prove that a nearby failure is rejected, check
the final artifact, then compare paired runs with their missing data and
regressions intact. This gives an agent useful feedback it can act on: which
condition failed, which bytes were observed, and what evidence would close
the outcome. It adds a practical instrument to the doctrine without reducing
its principles to a phrase count or a single self-assigned score.
