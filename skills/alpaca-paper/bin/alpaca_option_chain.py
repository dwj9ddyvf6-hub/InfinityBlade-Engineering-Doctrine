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
from alpaca_lib import AlpacaError, api_request, emit, fail, trading_base
from datetime import date
from decimal import Decimal, InvalidOperation


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
    p.add_argument("--with-coverage", action="store_true",
                   help="Return contracts plus explicit completion, continuation and unknown-tradability metadata")
    return p


def fetch_contracts(params, max_pages=10, request=None):
    """Follow the complete token chain; never turn a corrupt page into absence.

    The returned envelope retains unknown-tradability contracts separately.
    A consumer that needs only the legacy tradable array must require complete.
    """
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("max_pages must be a positive integer")
    request = request or api_request
    query = dict(params)
    contracts, unknown, seen_symbols, seen_tokens = [], [], {}, set()
    token, excluded, pages = None, 0, 0
    for pages in range(1, max_pages + 1):
        if token:
            query["page_token"] = token
        else:
            query.pop("page_token", None)
        result = request("GET", f"{trading_base()}/v2/options/contracts", params=dict(query))
        if not isinstance(result, dict) or not isinstance(result.get("option_contracts"), list):
            raise AlpacaError("Invalid option-contract page: option_contracts must be an array")
        for contract in result["option_contracts"]:
            if not isinstance(contract, dict):
                raise AlpacaError("Invalid option-contract entry: expected an object")
            try:
                symbol = contract["symbol"]
                if not isinstance(symbol, str) or not symbol.strip():
                    raise ValueError("symbol")
                date.fromisoformat(contract["expiration_date"])
                if contract["type"] not in ("call", "put"):
                    raise ValueError("type")
                for field in ("strike_price", "multiplier"):
                    value = Decimal(str(contract[field]))
                    if not value.is_finite() or value <= 0:
                        raise ValueError(field)
                if "tradable" in contract and not isinstance(contract["tradable"], bool):
                    raise ValueError("tradable")
            except (KeyError, ValueError, TypeError, InvalidOperation) as error:
                raise AlpacaError("Invalid option-contract identity, date, numeric field or tradability") from error
            if symbol in seen_symbols:
                if seen_symbols[symbol] != contract:
                    raise AlpacaError("Conflicting duplicate option contract across pages")
                continue
            seen_symbols[symbol] = dict(contract)
            normalized = {"symbol": symbol, "expiration": contract["expiration_date"],
                          "strike": contract["strike_price"], "type": contract["type"],
                          "multiplier": contract["multiplier"]}
            if contract.get("tradable") is True:
                contracts.append(normalized)
            elif contract.get("tradable") is False:
                excluded += 1
            else:
                unknown.append(normalized)
        token = result.get("next_page_token")
        if token is not None and (not isinstance(token, str) or not token):
            raise AlpacaError("Invalid option-contract continuation token")
        if token in seen_tokens:
            raise AlpacaError("Option-contract pagination repeated a continuation token")
        if token is None:
            break
        seen_tokens.add(token)
    return {"contracts": contracts, "unverified_contracts": unknown,
            "coverage": {"complete": token is None and not unknown,
                         "source_pages_complete": token is None,
                         "pages": pages, "unique_contracts_seen": len(seen_symbols),
                         "excluded_nontradable": excluded,
                         "unknown_tradability": len(unknown), "next_page_token": token}}


def main() -> None:
    args = build_parser().parse_args()
    if not args.underlying.strip() or not 1 <= args.limit <= 10000 or args.max_pages < 1:
        fail("Nonempty underlying, limit1..10000 and positive max-pages are required")
    try:
        dates = [date.fromisoformat(x) for x in (args.expiry_gte, args.expiry_lte) if x]
        if len(dates) == 2 and dates[0] > dates[1]:
            raise ValueError("inverted expiration window")
    except ValueError:
        fail("Expiration bounds must be YYYY-MM-DD in ascending order")
    params = {"underlying_symbols": args.underlying.strip().upper(), "status": "active",
              "type": args.ctype, "limit": args.limit}
    if args.expiry_gte:
        params["expiration_date_gte"] = args.expiry_gte
    if args.expiry_lte:
        params["expiration_date_lte"] = args.expiry_lte
    try:
        result = fetch_contracts(params, args.max_pages)
        if not args.with_coverage and not result["coverage"]["complete"]:
            raise AlpacaError("Option chain incomplete or tradability unknown; increase --max-pages or use --with-coverage to retain explicit partial evidence")
    except AlpacaError as error:
        fail(str(error), exit_code=2)
    emit(result if args.with_coverage else result["contracts"])


if __name__ == "__main__":
    main()
