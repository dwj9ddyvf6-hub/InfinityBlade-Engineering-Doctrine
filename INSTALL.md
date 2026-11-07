# Install InfinityBlade

Install the source first, then activate the skill in your host. Keep the source layout intact: `PRIMER.md` is above the core folder, and several skills refer to siblings. Copying only `skills/infinityblade/` loses part of its required reading contract.

## 1. Preserve and verify the source

Use a pinned checkout, or build a source bundle from the repository root:

```bash
python3 tools/build_bundle.py --skill infinityblade --output /tmp/infinityblade-source.zip
```

Multiple `--skill` arguments select entrypoints and the prerequisites to inspect; the archive still contains the complete repository source. The exporter retains the repository-relative source layout and includes a `BUNDLE-MANIFEST.json` with hashes and declared external prerequisites. Extract the archive into a stable authorized directory and keep that layout. `--require-runtime` refuses selections with unresolved declared runtime prerequisites; a successful source export alone is not a runtime-readiness claim.

New exports use manifest schema 2 and preserve executable source modes. A Git export includes every tracked regular file and excludes untracked state. Re-exporting an extracted bundle uses its manifest inventory, including binary resources; additions require an explicitly updated inventory or a tracked checkout. A plain directory without Git or a manifest uses the exporter's clean-source exclusions. Legacy schema 1 readback remains available without a mode-preservation claim. If an extraction tool drops executable permissions, restore the manifest's declared modes before invoking executable scripts directly.

Verify the archive before using it:

```bash
python3 tools/build_bundle.py --verify /tmp/infinityblade-source.zip
```

This readback verifies declared inventory, bytes and schema-2 modes. Publisher authenticity, external runtime behavior and host activation require their own evidence.

From the preserved repository or bundle root, run:

```bash
python3 tools/validate_repo.py
python3 tools/check_prompt.py
python3 tools/skill_router.py --list
```

Read each result and its scope. The validator checks local repository contracts; the prompt checker checks wording. Neither proves that a model follows the doctrine. Use the bundle manifest as its exact inventory. Exporting the files is not the same as reading and auditing them.

## Complete the reading and ascent

The complete source is the curriculum. Read [PRIMER.md](PRIMER.md), the core, then every tracked resource through the [reading protocol](docs/READING-PROTOCOL.md). Use the [ascent path](docs/ASCENT-PATH.md) to turn the material into sharper judgment and demonstrated work. Keep reading notes outside the public repository.

The automatic reader uses a pinned Git checkout. An exported bundle has no Git database; use its verified `BUNDLE-MANIFEST.json` as the complete source inventory and read every listed file in bounded chunks, retaining hashes and per-chunk notes through the host's available reader. Source export, full reading, local mechanism checks and demonstrated behavioral transfer each have their own completion evidence.

## 2. Activate it in the host

| Host | Activation |
|---|---|
| **Claude Code** | Register the preserved source using the host's supported skills import/directory mechanism. Its conventional user path is `~/.claude/skills/infinityblade/`; project scope uses `.claude/skills/infinityblade/`. Preserve access to the primer and routed siblings when using either. |
| **Codex** | Register the preserved source through the host's skill mechanism; a conventional directory is `~/.codex/skills/infinityblade/`. Invoke with `Use $infinityblade …` where supported. Check the active host's actual path and import behavior. |
| **Other Agent Skills hosts** | Use the documented importer or skill directories and verify that dependency links remain accessible. |
| **Cursor** | Put the [README prompt](README.md#start-in-30-seconds-complete-the-ascent) in `.cursor/rules/infinityblade.mdc` with the host's supported always-apply metadata; include a locator to the preserved source. |
| **GitHub Copilot** | Put the prompt in `.github/copilot-instructions.md`, with the source locator. |
| **Repository instruction files** | Use `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` as supported by the host; retain the core source location and scope. |
| **Chat model / API** | Use the prompt plus the primer/core contents in the available instruction/context mechanism. Files the host cannot read do not count as loaded. |

If an importer accepts only one flattened folder, do not assume relative links survived. Supply the primer and routed files as additional resources, or use the source-locator/prompt route. A symlink may work in a host that follows links, but this is a host capability to verify, not a universal installation promise. The [portable host contract](docs/OPERATING-PATHS.md#establish-a-portable-host-contract) maps capabilities without inventing tools.

## 3. Add library skills by task

The [index](skills/INDEX.md) contains 22 noncore skills; the [registry](skills/registry.json) is the machine-readable inventory. Source-complete means the folder's authored text/code is present. It does not mean every external engine, renderer, credential, host tool or policy dependency is bundled.

```bash
python3 tools/skill_router.py 'verify a saved export and a delegated completion claim'
python3 tools/build_bundle.py --skill save-readback-verification --skill claim-verification-ledger --output /tmp/verification-source.zip
```

The router gives lexical suggestions and dependencies, not semantic certainty. Read the chosen skill's trigger and negative boundary. Chart/stock analysis requires the chart engine and renderer; backtest cross-checking requires its pinned external oracle; REA teardown requires its external toolchain. Credentials, private memory and runtime state belong outside this public source tree.

## Confirm installation and behavior separately

**Installation:** prove the host discovers the intended version and can open its primer, core and routed dependencies. Record host, source revision, activation route and any missing capability. Read-back beats a model recital.

**Local mechanisms:** run the matching package tests on temporary state. Record actual runner counts and final exit status, with the tested revision. This proves the tested contracts only.

**Behavior:** use the [paired evaluation procedure](docs/BEHAVIOR-EVALUATION.md). Start with a repair case and an absence/verdict case from [eval-cases.md](skills/infinityblade/references/eval-cases.md), plus a near-miss case where the workflow should not activate. Compare candidate and baseline in fresh contexts, keep selection data separate from a held-out final set, and report costs and regressions. An already successful baseline is not a failed install; it means that case establishes no improvement. Do not claim a cross-model effect without actual model trials.

## Enforce it

Instructions can be skipped. A Claude Code Stop hook checks the report's shape at the end of a turn. Keep [hooks/require-status.sh](hooks/require-status.sh) inside the repository/bundle so it can load [tools/status_evidence_check.py](tools/status_evidence_check.py). If copying the hook elsewhere, set `INFINITYBLADE_ROOT` to the preserved source root; the hook is not a standalone single-file installation.

For a repository containing the hook and tools, a project-level `.claude/settings.json` entry is:

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command", "command": "bash hooks/require-status.sh" }] }]
  }
}
```

Resolve the command relative to the host's actual working directory. For another directory, use an absolute path and set `INFINITYBLADE_ROOT` in the host's environment. Run a fresh-session smoke test before calling the hook active; a configuration file alone is not enforcement proof.

**What it checks:** the final assistant text carries a recognized `STATUS:` verdict with a supported evidence-pointer shape, or the exact no-change scope marker. A bare label is refused. A nonexistent or irrelevant locator can still pass a wording check; the hook does not verify evidence truth or grant completion. The active-hook guard prevents an endless stop loop. Input/configuration problems must be reported as such, never converted into successful proof.

**Activation scope:** the core skips casual conversation and pure explanation. The shipped checker accepts the standalone `STATUS: GREEN, no change made` marker for those skipped categories. A host applying enforcement to all conversational replies needs its own documented skip/answer adapter; the marker must never replace the answer the user requested. Until that adapter is verified, name the integration gap. It cannot excuse a result claim, performed work or a missing evidence row. Other hosts can apply the same shape checker at their own supported completion boundary; verify that integration independently.
