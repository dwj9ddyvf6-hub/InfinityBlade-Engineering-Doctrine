---
name: hermetic-test-isolation
description: Make regression tests prove the same verdict alone, in the full suite, and in a clean export, with no live-state reads, no unrestored monkeypatches, and no import-frozen paths, before any gate result is trusted.
version: 1.0.0
---

# Hermetic Test Isolation

## Purpose
A test that passes only because of the environment it ran in — live files present, another test's stub still installed, an import-time path pointing at real state — manufactures green. This skill makes every blocker test hermetic so a gate verdict means the same thing in any tree, in any order.

## Workflow
1. No live-state reads: a test must build every input it needs (fixtures, temp dirs, stubbed providers). If it opens a production data file, ledger, cache, or generated snapshot, rewrite it to construct that state itself.
2. Redirect everything, including import-frozen paths: when the code under test captured a path or constant at import time (lock files, state dirs, ledger paths), redirect that captured name too — redirecting only the runtime lookup leaves the test silently touching real state. Check siblings of any path you redirect for the same pattern.
3. Restore every patch: any monkeypatch, stub, or module-attribute replacement a test installs is recorded and restored (fixture teardown or try/finally), even on failure. A leaked stub silently neutralises other tests' blockers in full-suite runs.
4. Prove it three ways before trusting a blocker: (a) the test alone, (b) the full suite in gate order, (c) a clean export / pristine copy with no live state directory present. A test whose verdict differs between any two is not yet a blocker.
5. Prove the fail direction in the same clean environment: the test must fail on the pre-fix code and pass on the fixed code under the clean-export run, not only on the working tree.
6. When a full-suite failure disappears when files run alone (or vice versa), treat it as cross-test contamination until proven otherwise: find the leaking patch or shared state before re-running the gate for a verdict.

## Output Contract
For each new or repaired blocker: the three run results (alone / full suite / clean export), the fail-direction proof and where it was run, and a list of every patch and path the test installs or redirects with its restoration point. A gate report names which of the three environments its verdict comes from.

## Operating Rules
1. A working-tree pass is not evidence about a clean tree: generated files and live state present in the working tree are exactly what a clean export lacks.
2. Never pin a known non-hermetic test as 'expected to fail in export' and move on without a dated, shrink-only exemption entry naming it.
3. Test-writing is production work: a test that writes into production-shaped paths or leaves stubs installed is a defect in the test, logged and blocked like any other bug.
4. When a gate's own output truncates or hides failure names, the gate run is invalid for verdict purposes — get the full failure list before judging.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
