#!/usr/bin/env python3
"""alpaca_option_chain — list tradable option contracts for an underlying.

Wraps GET /v2/options/contracts. Emits a compact JSON array of contracts:
symbol (OCC), expiration, strike, type, multiplier.
(Audit 2026-10-06: the docstring previously said expiration_date /
strike_price, but the code normalizes to expiration / strike. A caller
bug already came from trusting the docstring.)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import api_request, emit, trading_base


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="List Alpaca option contracts.")
    p.add_argument("--underlying", required=True,
                   help="Underlying ticker, e.g. NVDA")
    p.add_argument("--type", default="call", choices=["call", "put"],
                   dest="ctype", help="Contract type (default: call)")
    p.add_argument("--expiry-gte", default=None,
                   help="Earliest expiration YYYY-MM-DD")
    p.add_argument("--expiry-lte", default=None,
                   help="Latest expiration YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=200,
                   help="Max contracts per page (default: 200)")
    p.add_argument("--max-pages", type=int, default=10,
                   help="Cap on pages followed via next_page_token (default: 10)")
    return p


def main() -> None:
    args = build_parser().parse_args()
    params = {
        "underlying_symbols": args.underlying.upper(),
        "status": "active",
        "type": args.ctype,
        "limit": args.limit,
    }
    if args.expiry_gte:
        params["expiration_date_gte"] = args.expiry_gte
    if args.expiry_lte:
        params["expiration_date_lte"] = args.expiry_lte
    # Follow next_page_token: a target strike may live on a later page.
    contracts = []
    page_token = None
    pages = 0
    while True:
        if page_token:
            params["page_token"] = page_token
        result = api_request("GET", f"{trading_base()}/v2/options/contracts",
                             params=params)
        # 3x-daily bugcheck 2026-10-11 night (MINOR): api_request returns
        # {"raw": text} on non-JSON 2xx bodies; the old code treated that
        # as "no contracts" and silently emitted []. A non-dict body also
        # crashed .get() below. Fail loud (same class as the
        # alpaca_get_account.py 2026-10-08 fix).
        if isinstance(result, dict) and "raw" in result:
            print("Unexpected contracts response shape (non-JSON body)",
                  file=sys.stderr)
            sys.exit(2)
        if not isinstance(result, dict):
            print("Unexpected contracts response shape (non-object body)",
                  file=sys.stderr)
            sys.exit(2)
        batch = (result or {}).get("option_contracts") or []
        # 3x-daily bugcheck 2026-10-08 (LOW): a malformed page (non-list
        # option_contracts, or non-dict entries) crashed .extend / the
        # filter below. Skip the malformed page instead.
        if not isinstance(batch, list):
            batch = []
        contracts.extend(batch)
        page_token = (result or {}).get("next_page_token")
        pages += 1
        if not page_token or pages >= args.max_pages:
            # 3x-daily bugcheck 2026-10-14 (LOW, BC14M-2): a live
            # page_token at the page cap means the chain is silently
            # truncated (the tradable filter below shrinks it further,
            # so a caller's strike can be missing with no signal).
            # Current callers pass --limit 500 with <=1-week /
            # <=~45-DTE windows and stay under the cap, so this is
            # latent -- warn on stderr (stdout stays a pure JSON
            # array) instead of truncating in silence.
            if page_token:
                print("WARNING: option chain truncated at --max-pages "
                      "%d (%d contracts before tradable filter); "
                      "raise --max-pages for a wider window"
                      % (args.max_pages, len(contracts)),
                      file=sys.stderr)
            break
    # client-side tradable filter (no server-side tradable param)
    # 3x-daily bugcheck 2026-10-08 (LOW): isinstance guard added with the
    # page-shape guard above -- a non-dict entry crashed .get().
    contracts = [c for c in contracts
                 if isinstance(c, dict) and c.get("tradable", True)]
    emit([{
        "symbol": c.get("symbol"),
        "expiration": c.get("expiration_date"),
        "strike": c.get("strike_price"),
        "type": c.get("type"),
        "multiplier": c.get("multiplier"),
    } for c in contracts])


if __name__ == "__main__":
    main()
