---
name: persisted-field-consumption-audit
description: Use whenever a migration to a canonical source is about to be called complete, or a surface is built from persisted producer fields, even when a caller list looks complete; skip for greenfield builds with no predecessor route.
version: 1.0.2
---

# Consumer and Field Consumption Audit

## Why this skill exists

The default: Migrating a producer and trusting the fields to follow.
The cost: A field renamed at the producer kept its old meaning at one consumer, which read a stop as a backstop and acted on the confusion.
The replacement: Audit every consumer of every persisted field before calling the migration complete, role by role.

## Define the door and inventory the fields

- Name the canonical source, engine or feed, the retired routes it replaces, and the exact identifiers that betray an old route, covering module names, function names, data path fragments, provider hostnames, cache directories, timeframe strings and output labels.

- List every field a producer writes into a trade record, feed, ledger row or state file, including fields added for a future consumer.

- Treat a caller list from the code author, a previous audit or your own memory as a starting hint only, because the search is the enumeration.

## Search exhaustively and keep the ledger

- Search the whole tree with `muse.exec` for every identifier and every field name, including indirect consumers such as analyzers, watchers, label printers, daily and weekly legs, research scripts and cron invoked entry points.

- Check caches and state files as consumers too, because a watcher or report reading a stale cache written by a retired route is still printing that route output.

- Keep a coverage ledger covering searched, excluded with a reason, and unavailable, plus fields searched, fields consumed and fields unconsumed.

- Re run the search with the other identifiers before claiming no consumers remain, because a search that finds nothing proves only that the search found nothing.

## Classify consumers and check fields

- Classify every hit with line level proof as ENGINE when it feeds the canonical system outputs, OFF-ENGINE when it is proven not to feed those outputs, or COSMETIC when it is label or display only, and fix cosmetic hits too because a wrong label teaches a wrong doctrine.

- Reroute every ENGINE hit to the canonical route fail closed, so the consumer produces no decision or action from a missing canonical input and never falls back to a retired route or a stale cache. Emit an explicit unavailable/stale status. Independently authorized protective actions retain their own validated inputs and owner; a missing entry signal does not disable an exit path.

- Name the consumer for each persisted field, or mark it unconsumed and state what the intended reader was supposed to show from it, recording zero reference results as findings rather than harmless extras.

- Separate fields that share a plain name but carry different roles, such as a trading stop, a disaster backstop, an invalidation level and a target, and require each role to print under its own label.

- Reject any surface that substitutes one role for another, such as printing a percentage backstop as the trading stop, even when the substituted number recomputes exactly.

- Key lifecycle truth to the instance rather than to the symbol alone, and test with a prior closed instance of the same symbol still present in the record.

- Require an explicit selection rule when several producers stage a value for the same role, and reject selection by list order or by widest or narrowest value without a stated rule.

- Compare any uniform validity window, clock or expiry against each producer own clock, and flag a surface window that matches none of them.

## Check rendering and completeness

- Trace each consumed field from the producer record through the feed to the rendered page or report, and mark fields that compute in the feed but render nowhere.

- Check for two different values carrying the same label on one surface, and require distinct labels or a single reconciled value before reporting.

- Recompute at least one item end to end from the producer record, reading the target, stop and clock from the field the producer designated for the surface.

## Label session and freshness on every figure

- Record the session date and the source time from the producer record itself for every market figure, position count or state value a digest, report or surface presents, and never substitute the retrieval time or the presentation date for them.

- Label a prior session close with that session date and the word close, and reserve premarket, intraday and live for values the source actually recorded in that session window on that day.

- Stop and reconcile before publishing when two sources carry different values under the same label for the same session, and publish neither value as settled until the producer record decides which one is right.

- Name a fallback value as stale with its own date whenever the primary source fails and an older book, cache or measurement is used, or publish nothing for that item instead.

- Bar a surface from republishing a measurement, book or snapshot from an earlier session as fresh, and require its age against the surface stated window to be printed or checked before the surface ships.

- Add the session and freshness check to the gate wired blocker for any recurring digest or surface, so a figure with no session date, no source time or a stale fallback presented as current fails the gate.

## Block the regression and report

- Ship a named regression blocker wired into the gate that re runs the exhaustive search and fails when any unclassified hit on a retired route appears, when a designated surface field has zero consumers, when a backstop role is rendered as a trading stop, or when a lifecycle flag is keyed by symbol alone.

- Verify the fail direction by executing a temporary revert or targeted mutant in an isolated copy, and record the blocker name and its gate wiring in the audit output. Require failure caused by the planted defect, not an import error or broken harness. Reasoning alone leaves fail-direction proof UNVERIFIED.

- Report the audit with the coverage ledger counts, a classification table with one row per hit, and the field ledger naming consumer, role and scope for each designated field.

- Report GREEN only when every consumer is classified, every designated field has a named consumer with a distinct role label and instance level scope, and the blocker is gate wired, and reopen the audit as its own finding when a consumer is discovered after a complete report.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with the host’s connector-setup procedure (historical locator: `/opt/muse/skills/custom-connector-setup/SKILL.md`, an external host dependency; see [portable host setup](../../docs/OPERATING-PATHS.md#establish-a-portable-host-contract)), or build a custom connector.

## Alternatives for better results

- Start with the fields a surface claims to show, then widen to every field the producer wrote for that surface, because the second pass is where unconsumed fields appear.

- Run the consumer search and the field inventory in the same pass when a migration and a new surface land together, because each pass catches hits the other would miss.

## Host portability

`muse.*` names above describe the originating host. Discover equivalent advertised search, read, image-view and execution capabilities on the current host; do not call tools that are absent. The historical connector-setup path is not bundled. Use [the portable host contract](../../docs/OPERATING-PATHS.md#establish-a-portable-host-contract), retain the same evidence and authorization boundaries, and name a missing capability rather than pretending the recipe ran. Installing a connector or service still requires the task’s authority.
