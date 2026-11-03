#!/usr/bin/env python3
"""alpaca_option_quotes — latest quotes for OCC option symbols.

Wraps GET /v1beta1/options/quotes/latest. Emits a JSON object keyed by OCC
symbol with bid/ask/mid/spread_frac (spread as a fraction of mid).
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import api_request, emit, data_base


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Latest quotes for option symbols.")
    p.add_argument("--symbols", required=True,
                   help="Comma-separated OCC symbols, e.g. NVDA261023C00235000")
    p.add_argument("--feed", default="indicative",
                   help="Options feed (default: indicative)")
    return p


def main() -> None:
    args = build_parser().parse_args()
    result = api_request(
        "GET", f"{data_base()}/v1beta1/options/quotes/latest",
        params={"symbols": args.symbols, "feed": args.feed})
    # 3x-daily bugcheck 2026-10-11 night (MINOR): api_request returns
    # {"raw": text} on non-JSON 2xx bodies; the old code emitted an empty
    # quotes object that callers read as "no quotes available". A non-dict
    # body also crashed .get() below. Fail loud (same class as the
    # alpaca_get_account.py 2026-10-08 fix).
    if isinstance(result, dict) and "raw" in result:
        print("Unexpected quotes response shape (non-JSON body)",
              file=sys.stderr)
        sys.exit(2)
    if not isinstance(result, dict):
        print("Unexpected quotes response shape (non-object body)",
              file=sys.stderr)
        sys.exit(2)
    # 3x-daily bugcheck 2026-10-08 (LOW): "quotes": null (key present,
    # value null) crashed .items() below. Treat as empty.
    quotes = (result or {}).get("quotes") or {}
    # 3x-daily bugcheck 2026-10-14 evening (LOW, BC14E-16): a non-dict non-null quotes
    # value (list/str) raised uncaught AttributeError on .items() --
    # fail loud like every other shape break in the bin set.
    if not isinstance(quotes, dict):
        print("Unexpected quotes response shape (quotes is not an object)",
              file=sys.stderr)
        sys.exit(2)
    out = {}
    for sym, q in quotes.items():
        # 3x-daily bugcheck 2026-10-08 (LOW): a malformed quote entry
        # must not nuke every symbol's quotes -- skip it.
        if not isinstance(q, dict):
            continue
        try:
            bid = float(q.get("bp") or 0)
            ask = float(q.get("ap") or 0)
        except (TypeError, ValueError):
            bid, ask = 0.0, 0.0
        # 3x-daily bugcheck 2026-10-13: float() succeeds on "inf"/"NaN"
        # strings, so non-finite quotes passed validation and emit()
        # produced Infinity/NaN tokens -- invalid strict JSON that
        # callers reject (or silently ingest as inf/NaN mids). Same
        # class alpaca_list_positions was fixed for on 2026-10-12.
        if not math.isfinite(bid):
            bid = 0.0
        if not math.isfinite(ask):
            ask = 0.0
        mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else 0.0
        spread_frac = (ask - bid) / mid if mid > 0 else None
        out[sym] = {"bid": bid, "ask": ask, "mid": round(mid, 4),
                    "spread_frac": spread_frac}
    emit(out)


if __name__ == "__main__":
    main()
