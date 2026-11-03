#!/usr/bin/env python3
"""alpaca_list_positions — print all open positions as JSON."""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import api_request, emit, trading_base


def _normalize_qty(positions):
    """Coerce whole-share qty strings to int-strings ("70", not "70.0").

    Forward fix 2026-10-07 (be forward thinking): the
    broker returns qty as e.g. "70.0"; every downstream consumer parsed it
    as float and re-stringified as "70.0", which Alpaca rejects on order
    submit. 21 float-qty patches across audits all treated the symptom.
    Normalizing at this single source kills the entire class: every
    sleeve, the audit, and the ledger now receive clean int-strings.
    Fractional quantities pass through untouched.
    """
    if not isinstance(positions, list):
        return positions
    for p in positions:
        if not isinstance(p, dict):
            continue
        q = p.get("qty")
        try:
            fq = float(q)
        # 3x-daily bugcheck 2026-10-08 (LOW): int(inf) raises
        # OverflowError, not ValueError -- a malformed broker qty like
        # "inf" crashed the whole listing instead of passing through.
        except (TypeError, ValueError, OverflowError):
            continue
        # 3x-daily bugcheck 2026-10-12 23:17 ET (LOW): float("inf") /
        # float("nan") SUCCEED, so the try above did not guard them --
        # int(inf) raised OverflowError and int(nan) ValueError at the
        # comparison below, crashing the whole positions listing (every
        # sleeve's broker view) on one malformed qty. The 2026-10-08
        # guard only covered the float() conversion. Pass non-finite
        # quantities through untouched instead.
        if not math.isfinite(fq):
            continue
        if fq == int(fq):
            p["qty"] = str(int(fq))
    return positions


def main() -> None:
    argparse.ArgumentParser(description="Print all open Alpaca positions as JSON.").parse_args()
    positions = api_request("GET", f"{trading_base()}/v2/positions")
    # 3x-daily bugcheck 2026-10-10 (MINOR): api_request returns
    # {"raw": text} on non-JSON 2xx bodies; the old code normalized and
    # emitted it verbatim. Fail loud (same class as the
    # alpaca_get_account.py 2026-10-08 fix).
    if isinstance(positions, dict) and "raw" in positions:
        print("Unexpected positions response shape (non-JSON body)",
              file=sys.stderr)
        sys.exit(2)
    # 3x-daily bugcheck 2026-10-14 PM (LOW, BC14P-10): any other dict body passed through
    # _normalize_qty and was emitted where every caller expects a
    # LIST of positions. Fail loud.
    if positions is not None and not isinstance(positions, list):
        print("Unexpected positions response shape (non-array body)",
              file=sys.stderr)
        sys.exit(2)
    emit(_normalize_qty(positions if positions is not None else []))


if __name__ == "__main__":
    main()
