#!/usr/bin/env python3
"""alpaca_option_order — submit a single-leg options limit order.

Simple orders only (no bracket/OCO/OTO). Whole-contract quantities.
position_intent must be one of buy_to_open / buy_to_close / sell_to_open /
sell_to_close (the four Alpaca options intents); credit-spread sleeves sell
to open and buy to close.
"""
import argparse
import math
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import (
    AlpacaError,
    api_request,
    emit,
    fail,
    require_live_confirmation,
    trading_base,
)

VALID_INTENTS = {"buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Submit an options order (paper).")
    p.add_argument("--symbol", required=True,
                   help="OCC option symbol, e.g. NVDA261023C00235000")
    p.add_argument("--side", required=True, choices=["buy", "sell"])
    p.add_argument("--qty", type=int, required=True,
                   help="Whole number of contracts")
    p.add_argument("--limit-price", type=float, required=True,
                   help="Limit price per share of the contract")
    p.add_argument("--position-intent", required=True,
                   choices=sorted(VALID_INTENTS),
                   help="buy_to_open (entry) or sell_to_close (exit)")
    p.add_argument("--time-in-force", default="day",
                   choices=["day", "gtc", "ioc", "fok"],
                   dest="time_in_force", help="Time in force (default: day)")
    p.add_argument("--client-order-id", default=None,
                   help="Idempotency key; a UUID4 is generated when omitted")
    p.add_argument("--i-understand-this-is-live", action="store_true",
                   dest="i_understand_this_is_live",
                   help="REQUIRED to submit when ALPACA_ENV=live")
    return p


def validate(args: argparse.Namespace) -> None:
    # 3x-daily bugcheck 2026-10-11 night (MINOR): --limit-price nan
    # slipped past the positivity check (NaN comparisons are False) and
    # was serialized into the payload as "nan" -> 422 at the API. Same
    # class as the 2026-10-10 alpaca_submit_order.py --qty fix.
    if args.qty <= 0:
        fail("--qty must be a positive whole number of contracts")
    if args.limit_price <= 0 or not math.isfinite(args.limit_price):
        fail("--limit-price must be a positive finite number")


def main() -> None:
    args = build_parser().parse_args()
    require_live_confirmation(args)
    validate(args)
    order = {
        "symbol": args.symbol.upper(),
        "side": args.side,
        "type": "limit",
        "time_in_force": args.time_in_force,
        "qty": str(args.qty),
        "limit_price": str(args.limit_price),
        "position_intent": args.position_intent,
        "client_order_id": args.client_order_id or str(uuid.uuid4()),
    }
    try:
        result = api_request("POST", f"{trading_base()}/v2/orders",
                             payload=order)
    except AlpacaError as e:
        # 3x-daily bugcheck 2026-10-08 (MEDIUM): port the
        # alpaca_submit_order.py structured-error pattern. The old code
        # let the traceback go to stderr with EMPTY stdout, so callers'
        # json.loads(stdout) raised JSONDecodeError and callers could
        # not distinguish a 422-duplicate-cid (safe to abandon) from a
        # retryable failure (blind retry = double-submit risk).
        import json as _json
        print(_json.dumps({
            "error": True,
            "status_code": getattr(e, "status_code", None),
            "outcome_unknown": bool(getattr(e, "outcome_unknown", False)),  # 3x-daily bugcheck 2026-10-14 PM BC14P-9: see alpaca_submit_order.py
            "message": str(e)[:500],
            "symbol": args.symbol.upper(),
            "side": args.side,
            "position_intent": args.position_intent,
        }), file=sys.stderr)
        raise SystemExit(1)
    # 3x-daily bugcheck 2026-10-12 PM (LOW, restored pm3-H guard):
    # fail loud on {"raw": ...} non-JSON 2xx bodies (see
    # alpaca_submit_order.py) instead of emitting a fake order.
    if isinstance(result, dict) and "raw" in result:
        print("Unexpected order response shape (non-JSON body)",
              file=sys.stderr)
        sys.exit(2)
    if not isinstance(result, dict):
        print("Unexpected order response shape (non-object body)",
              file=sys.stderr)
        sys.exit(2)
    emit(result)


if __name__ == "__main__":
    main()
