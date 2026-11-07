---
name: backtest-crosscheck
description: Cross-check a simple daily-bar mechanical backtest headline against a second, independent oracle engine before the result is reported, graded, adopted, or used to kill a setup; skip for intraday, options, or path-dependent strategies, which are out of the oracle scope.
version: 1.0.1
---

# Backtest Cross-Check With the Standing Oracle

## Why this skill exists

The default: Reporting a backtest headline from the engine that produced it.
The cost: The oracle earns its keep exactly when it disagrees: a headline that survived only its own engine's arithmetic was a bug with a chart.
The replacement: Corroborate the headline against an independent oracle before reporting, with kill criteria stated in advance.

Use when a backtest of a simple daily-bar mechanical sleeve or strategy produces a headline result that will be reported, graded, adopted, or used to kill a setup: before the result is stated, run the same rules through the standing oracle and report both numbers.

## The oracle

- Engine: quantjourney-bt (Apache-2.0), pinned at commit 16fe1ac6c8345bae922207ee4d2f4eb123a89166, vendored at <oracle-install>/quantjourney-bt/ (set ORACLE_DIR to your install location) with its README protocol and the worked EMA 20/50 corroboration fixture under examples/ema-2050/.
- Historical origin: a project adoption ruling dated 2026-10-31, whose study reportedly reproduced a reference backtest exactly on trade count, wins, and win rate with the return gap fully attributed. This is provenance, not a ruling made by a new adopter. A new host must verify the pinned external engine and fixture before adopting it locally.
- Offline only: ExecutionSimulator, FillEngine, PortfolioLedger on local bars. Never the QuantJourney gateway, SDK connector path, or any hosted service.
- Scope limit: deterministic daily-bar rules with next-open or close fills. Intraday, options, and path-dependent strategies are out of scope; say so instead of forcing a fit.

## Adoption boundary

The engine and worked fixture are external prerequisites, not files shipped in this folder. Verify the pin, license, fixture inputs and expected outputs from their actual source; report the cross-check BLOCKED or UNVERIFIED when unavailable. The numerical kill criteria below are the recorded method's policy, not statistical guarantees. A changed policy needs a dated local ruling and a fresh independent fixture; no cross-check authorizes an order.

## Protocol

- State the falsifiable claim and kill criteria before running anything: sign flip of the net result, trade count differing by more than 25 percent without a named mechanical cause, or return differing by more than a third without a fully itemised cause.
- Record our own headline numbers and their source first, then translate the rules into the oracle's idiom with a written translation log. Any rule that cannot map one to one is named in the log, never silently adjusted.
- Same universe, same window, same underlying bars. Match cost assumptions as closely as the oracle's model allows and itemise every parameter that could not be matched.
- Report the comparison table and decompose the return gap into named causes (fill model, cost model, data, translation, sizing mechanics). The historical fixture attributed roughly 2 percent relative to sizing mechanics; that is an incident result, not a universal allowance. Every observed gap needs its own named cause.
- Verdicts: CORROBORATED, CORROBORATED WITH NAMED GAPS, NOT CORROBORATED. A NOT CORROBORATED verdict blocks reporting our number as settled until the divergence is root-caused.
- Save scripts, outputs, and the comparison in the study's own research record. The tools directory keeps only the pinned engine and the fixture.

## Rationalization table

| Excuse | Reality |
|---|---|
| "Our engine is already tested, a second engine adds nothing." | The oracle earns its keep exactly when it disagrees; a cross-check that only runs on suspect results never catches the quiet ones. |
| "The rules almost map, close enough." | An unlogged translation change makes the comparison meaningless and can manufacture either agreement or divergence. |
| "The gap is small, no need to decompose it." | The 2026-10-31 fixture gap was small AND fully explained; a small unexplained gap is how a real defect hides. |
| "This sleeve is too complex for the oracle, skip it." | Out-of-scope is a stated verdict, not a silent skip: name it and let the result carry the unchecked flag. |

## Eval and release gate

- The fixture at <oracle-install>/quantjourney-bt/examples/ema-2050/ is the regression test for this skill's machinery: after any environment change, pin move, or harness edit, re-run run_reference.py and run_qj.py there and confirm both still reproduce expected/ (177 round trips, 60 wins, 33.90 percent win rate, +53.20 and +52.16 percent).
- A pin move without a fresh fixture pass and a note in the adopting project's adoption study record does not ship.
