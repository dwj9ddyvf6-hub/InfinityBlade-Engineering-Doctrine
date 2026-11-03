---
name: single-door-consumer-audit
description: Enumerate every consumer of a canonical source, engine, or feed by exhaustive search, never by caller list, and prove each one rerouted, exempt, or off-engine before declaring a single-door migration complete.
version: 1.0.0
---

# Single-Door Consumer Audit

## Purpose
When a source, engine, or feed is declared canonical and sole (one pipeline, fail-closed), the migration is only complete when every consumer of the old route is found — caller lists have repeatedly missed consumers that kept producing live output from the retired route.

## Workflow
1. Define the door: name the canonical source/engine/feed, the retired route(s) it replaces, and the exact identifiers that betray the old route — module names, function names (`detect_signals`, bar-fetch helpers), data-path fragments (provider hostnames, cache directories, timeframe strings), and output labels.
2. Search exhaustively, not from a list: grep the whole tree for every identifier from step 1, including indirect consumers — analyzers, watchers, label printers, daily/weekly legs, research scripts, and cron-invoked entry points. Keep a coverage ledger: searched / excluded (with reason) / unavailable.
3. Classify every hit with line-level proof: ENGINE (feeds the canonical system's outputs — must reroute), OFF-ENGINE (proven not to feed those outputs, with the proof recorded), or COSMETIC (label/display only — still fixed, since a wrong label teaches a wrong doctrine).
4. Reroute every ENGINE hit to the canonical route, fail-closed: when the canonical source is unavailable the consumer produces nothing, never a fallback to the retired route or a stale cache.
5. Check caches and state files as consumers too: a watcher or report reading a stale cache written by the retired route is still printing the retired route's outputs.
6. Ship a gate-wired regression blocker that re-runs the step-2 search and fails if any unclassified hit on the retired route appears; verify the fail direction by reasoning or temporary revert.
7. Only then report the migration complete, naming the ledger counts.

## Output Contract
A coverage ledger (searched / excluded / unavailable), a classification table (one row per hit: file, line, class, proof or reroute), the blocker name and its gate wiring, and the final status in GREEN / PARTIAL / BLOCKED / UNVERIFIED terms. Any unclassified hit means the status is not GREEN.

## Operating Rules
1. A caller list supplied by the code's author, a previous audit, or your own memory is a starting hint, never the enumeration. The search is the enumeration.
2. Route failure is not absence: a grep that finds nothing proves that grep found nothing — re-run with the other identifiers from step 1 before claiming no consumers remain.
3. Never shrink the claim to the consumers you checked: report 'all consumers found by exhaustive search over <identifiers>' with the ledger, not 'all consumers'.
4. A consumer discovered after a 'complete' report reopens the migration and is logged as its own finding, not quietly patched.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
