---
name: conviction-surface-definition
description: Define what a requested ranking, board, or summary surface is and where its conviction is formed before building it, and source it only from that formation point.
version: 1.0.0
---

# Conviction Surface Definition

## Why this skill exists

The default: Building the board first and deciding what belongs on it later.
The cost: A ranking of unjudged items is slop even if the numbers are real: the surface looked like conviction and carried none.
The replacement: Define the formation point where conviction is created before building the surface, and ship the surface empty rather than filling it from raw fields.

## Purpose
Never compose a ranking, board, or summary from whatever fields happen to be lying around. First define what the thing is on this desk, find where its judgment is actually formed, and source the surface from there.

## Workflow
1. Before building, write one sentence answering the user's actual goal: what decision or proof is this surface for, and for whom (including whether it is public-facing)?
2. Identify the formation point: where does conviction for an item on this surface get created (for example staging plus a PASS chart-gate read, a scored prospective log, a signed decision)? If an item has not passed that point, it cannot appear — no exceptions for 'fresh' or 'high-scoring' raw fields.
3. List what each displayed item must carry from the formation point: the thesis in words, entry zone, stop/invalidation, target, the gate's own read text, regime/structure context, and lifecycle state. A score or an order receipt ('buy N @ price, filled') is not a thesis.
4. Exclude non-conviction items explicitly (hedges, housekeeping fills, unscored experiments) and say why each class is excluded.
5. Check the failure twin: name the nearest past incident where a surface ranked something the underlying process had not actually judged, and state what in this design prevents the repeat.
6. Only then build. If the formation point does not yet exist as data, build that first and ship the surface empty rather than filling it from raw fields.

## Output Contract
The build ships with: the one-sentence definition, the formation-point source for every item, the required per-item fields, the exclusion list, and the failure-twin check. An empty board is a valid output when nothing has passed the gate.

## Operating Rules
1. No ranking publishes without the judgment artifact behind it (a gate read, a scored record) — a ranking of unjudged items is slop even if the numbers are real.
2. When the user corrects the surface's definition, rebuild to the corrected definition; do not defend or patch the field-composed version.
3. Public surfaces additionally obey the public-data boundary: only the public snapshot content, never internal logs, registers, or methodology text.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
