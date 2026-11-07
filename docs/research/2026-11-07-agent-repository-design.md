# Research-backed design for a portable operating doctrine

Research date: **2026-11-07**. This report develops external evidence into design recommendations for InfinityBlade's agent operating discipline. The [source ledger](2026-11-07-sources.json) records 15 source groups and code inspected at exact commits in five external repositories.

This is a source-led design study, not a substitute for reading the doctrine, a complete audit of its contents, or a measured claim that any LLM becomes more capable merely by reading it. The intended enhancement preserves the doctrine's depth and adds clearer activation, stronger examples, portable resources and observable verification.

## Make the intended behavior executable

A powerful operating principle should connect five things:

```text
Trigger → decision → action → observable result → honest report
```

For example, a completion claim should identify the artifact and the relevant final-state check. A saved file, a remote push and a deployed service require different observations. A report that contains the right status word can still be false.

[tau-bench](https://arxiv.org/abs/2406.12045) evaluates final task state, and [Anthropic's evaluation guidance](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) distinguishes a transcript from an outcome. The corresponding local design is to test the result being claimed, with structured fixtures and evidence pointers, rather than reward prescribed wording alone.

| Mechanism | What it can establish | What it cannot establish alone |
| --- | --- | --- |
| Frontmatter validator | Metadata satisfies a format contract. | The skill improves behavior. |
| Trigger evaluation | The host selected the intended skill for a prompt. | The skill solved the task. |
| Phrase or status checker | Required wording appears. | The statement is true. |
| Reference checker | An expected resource resolves in the tested package. | The resource is correct or useful. |
| Artifact/state oracle | The tested outcome matches the task's conditions. | Untested environments also work. |
| Controlled agent trial | Behavior under a specified model, task and environment. | Universal benefit for every model and task. |

These distinctions allow stronger claims when stronger evidence exists, while preserving useful lower-level checks.

## Keep the full doctrine and improve access

[The Agent Skills specification](https://agentskills.io/specification) describes progressive loading of metadata, instructions and resources. [AGENTS.md](https://agents.md/) offers a repository instruction convention. Both are useful interoperability patterns; neither is an empirical guarantee of better reasoning.

Retain the detailed references and the deep-study route. Add explicit activation conditions for task-specific material, stable entry points and examples of correct application. The reader should know whether it needs the core operating loop, a specialized workflow, an implementation guide or a full doctrinal review. A narrow task route does not authorize speaking for material the reader has not reviewed.

[The AGENTS.md evaluation paper](https://arxiv.org/html/2602.11988v3) supplies a caution against adding instructions without measuring their effect. Its findings do not prove that deleting doctrine improves agents. They motivate retaining distinctive, evidence-backed instructions and testing their practical consequences.

Long-context evidence also cuts both ways: [older retrieval experiments](https://aclanthology.org/2024.tacl-1.9/) found position effects, while [Google's Gemini 2.5 Flash study](https://research.google/pubs/retrieval-quality-at-context-limit/) did not observe that problem for simple factoid questions. Route design should therefore solve observable discovery and interpretation problems, not depend on a universal story about context failure.

## Portability should include the resources a skill needs

A skill that parses successfully may still fail when copied into a host with different tools, paths or dependencies. Validate installation from a clean exported package, rather than assuming the original repository remains nearby.

An installation contract should identify:

- Required resources and their resolution from the installed location.
- Dependencies, optional integrations and supported host assumptions.
- Which commands are illustrative and which are executed.
- The observable result of a local smoke check.
- What to report when a capability is unavailable.

The [reference Agent Skills validator](https://github.com/agentskills/agentskills/blob/83021e2be457a9b6679148719c1f6074f0ad975e/skills-ref/src/skills_ref/validator.py) checks metadata. Resource closure, executable examples and host compatibility require additional checks. A declared tool name is not proof that the tool exists or is authorized.

Portability should make the doctrine usable in more environments without weakening its proof standard. Optional providers should remain optional where the underlying task can be demonstrated locally.

## Build examples that resist plausible failure

Add worked cases that show both success and a nearby failure:

| Case | Successful behavior | Nearby failure to expose |
| --- | --- | --- |
| Save or export | Read back the intended destination and bind the claim to that artifact. | Trust a success message or an earlier local copy. |
| Changing repository | Bind verification to the tree actually delivered. | Report a check from an earlier tree after later edits. |
| Delegation | Inspect the delegated artifact and relevant evidence. | Repeat the delegate's summary as proof. |
| Missing evidence | Explain search coverage and what remains unknown. | Treat one empty search as an exhaustive negative result. |
| Tool failure | Classify the failure and choose a useful alternative within scope. | Repeat unchanged attempts or widen authority. |
| Memory update | Preserve provenance and distinguish superseded knowledge. | Apply a stale instruction as current. |
| Unavailable check | Report the precise unverified condition. | Convert a skipped check into a passing outcome. |

These are proposed evaluation cases, not assertions that the current implementation passes them. Fixtures should use synthetic identities, temporary files and explicit state boundaries. They should not require private user history, live accounts or external side effects.

## Evaluate instruction changes like product changes

[Anthropic's inspected skill-creator workflow](https://github.com/anthropics/skills/blob/2c5958ecac7cee2b583967a2c4981d0f4a75c579/skills/skill-creator/SKILL.md) compares baseline and skill-assisted trials. Apply the same experimental shape here, without assuming its implementation is a benchmark authority.

A useful record contains:

```text
Case and fixture revision
Repository/skill revision
Model and host version
Available tools and relevant configuration
Input, objective and permitted scope
Output artifact and observed final state
Grader version, decision and evidence
Trial outcome and failure reason
Elapsed seconds, tool calls and measured tokens
```

Keep missing metrics null. Distinguish input tokens, output tokens, characters and elapsed time. Retain failed and interrupted trials. The [inspected aggregation script](https://github.com/anthropics/skills/blob/2c5958ecac7cee2b583967a2c4981d0f4a75c579/skills/skill-creator/scripts/aggregate_benchmark.py) demonstrates why metric labels need inspection: one fallback stores output characters under a tokens field.

Compare the prior and candidate versions on matched tasks with controlled budgets. Evaluate useful autonomy, correctness, unnecessary work and recovery separately. Use held-out cases and human review to calibrate automated graders. Accept multiple valid action sequences when they establish the same authorized outcome. Report repeatability separately from whether any attempt succeeded.

[OpenAI's evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices) supports task-specific success criteria and calibrated grading. The records and fixtures should remain provider-independent so they can survive changes in hosted products.

## Memory, provenance and bounded execution

[LongMemEval](https://arxiv.org/abs/2410.10813) motivates separate tests for temporal reasoning, updates and abstention. For operating doctrine, record where a learned rule came from, when it applied, what superseded it, and what evidence would invalidate it. A remembered statement is evidence to evaluate; it does not independently grant authority.

[W3C PROV-DM](https://www.w3.org/TR/prov-dm/) offers a useful model of artifacts, generating activities and derivation. A practical receipt can carry source, revision, artifact identity and verification observation without adopting an ontology stack or claiming formal conformance.

[Mini-SWE-Agent's inspected implementation](https://github.com/SWE-agent/mini-swe-agent/blob/04d809ceab9df28f9adaed044884180159172930/src/minisweagent/agents/default.py) shows a compact execution loop with explicit limits and recorded exits. The useful pattern is inspectability: make resource bounds, recovery attempts and exit reasons visible. Reaching a limit is an operational outcome, not successful completion.

[Tool-design guidance](https://www.anthropic.com/research/writing-tools-for-agents) supports clear contracts and relevant results. Add workflow tooling only where it reduces a measured source of error or effort; extra tools and layers are not themselves evidence of stronger capability.

## Adoption and proof obligations

The [status evidence checker](../../tools/status_evidence_check.py) is a concrete
implementation surface for the syntax-versus-truth distinction: its contract
explicitly limits it to the final verdict and evidence-pointer presence. Review
it together with the [core skill](../../skills/infinityblade/SKILL.md) and
[installation guide](../../INSTALL.md). A passing wording check remains a
structural result; task-specific evidence must establish the outcome itself.

1. Preserve the current principles and detailed reference material.
2. Repair interoperability and resource-resolution defects.
3. Add outcome-oriented examples and adversarial fixtures.
4. Verify structural and executable contracts on the final repository state.
5. Run controlled behavioral trials before claiming a model-performance gain.

The proposed gain is practical: an agent can identify the applicable discipline, access its resources, act within the task, demonstrate the result and report the limits honestly. Whether a particular change produces that gain is an evaluation question.

## Research coverage and limitations

The [ledger](2026-11-07-sources.json) includes exact inspected commits and file hashes for Agent Skills, AGENTS.md, Anthropic skills, Mini-SWE-Agent and Aider. It distinguishes experimental results from standards and provider advice. No external code or prose was imported into the doctrine by this research report, and no model benchmark was run as part of the study. Later source revisions may change these findings.
