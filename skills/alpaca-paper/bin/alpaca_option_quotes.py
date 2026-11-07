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


def normalize_quotes(result, requested_symbols, feed):
    """Keep missing/invalid/crossed quotes distinct from executable prices."""
    if not isinstance(result, dict) or not isinstance(result.get("quotes"), dict):
        raise ValueError("Quotes response must contain a quotes object")
    out = {}
    for symbol in dict.fromkeys(requested_symbols):
        quote = result["quotes"].get(symbol)
        row = {"bid": None, "ask": None, "mid": None, "spread_frac": None,
               "quote_status": "missing", "timestamp": None, "feed": feed}
        if quote is None:
            out[symbol] = row
            continue
        if not isinstance(quote, dict):
            row["quote_status"] = "invalid"
            out[symbol] = row
            continue
        row["timestamp"] = quote.get("t")
        try:
            if any(isinstance(quote.get(k), bool) for k in ("bp", "ap")):
                raise ValueError("boolean price")
            bid, ask = float(quote["bp"]), float(quote["ap"])
            if not all(math.isfinite(x) and x >= 0 for x in (bid, ask)):
                raise ValueError("nonfinite or negative price")
        except (KeyError, TypeError, ValueError, OverflowError):
            row["quote_status"] = "invalid"
        else:
            row.update(bid=bid, ask=ask)
            if bid == 0 or ask == 0:
                row["quote_status"] = "one_sided"
            elif bid > ask:
                row["quote_status"] = "crossed"
            else:
                mid = bid / 2.0 + ask / 2.0
                row.update(mid=round(mid, 4), spread_frac=(ask - bid) / mid, quote_status="valid")
        out[symbol] = row
    return out


def main() -> None:
    args = build_parser().parse_args()
    symbols = list(dict.fromkeys(s.strip().upper() for s in args.symbols.split(",") if s.strip()))
    if not symbols:
        raise SystemExit("--symbols needs at least one nonempty symbol")
    result = api_request("GET", f"{data_base()}/v1beta1/options/quotes/latest",
                         params={"symbols": ",".join(symbols), "feed": args.feed})
    try:
        emit(normalize_quotes(result, symbols, args.feed))
    except ValueError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
