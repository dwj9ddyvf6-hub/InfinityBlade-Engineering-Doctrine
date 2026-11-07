#!/usr/bin/env python3
"""alpaca_option_mleg — submit a multi-leg options spread order (paper).

Submits 2-4 legs as a single atomic order (order_class=mleg). All legs
fill together or not at all.

Alpaca's sign convention (audit 2026-10-06): positive limit_price = DEBIT
(you pay), negative limit_price = CREDIT (you receive). For a net-credit
spread, pass limit_price as NEGATIVE (e.g. -0.05 for a $5 credit).
For a net-debit spread, pass limit_price as POSITIVE (the debit paid).
Alpaca does NOT reject the wrong sign -- it fills it. Get this wrong and
the spread's economics invert.

Legs are passed as JSON: --legs '[{"symbol": "...", "side": "sell",
"position_intent": "sell_to_open", "ratio_qty": 1}, ...]'
"""
import argparse
import json
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
    p = argparse.ArgumentParser(description="Submit a multi-leg options order (paper).")
    p.add_argument("--legs", required=True,
                   help="JSON array of legs: [{symbol, side, position_intent, ratio_qty}]")
    p.add_argument("--qty", type=int, required=True,
                   help="Number of spreads (whole number)")
    p.add_argument("--limit-price", type=float, required=True,
                   help="Net limit price for the spread (audit 2026-10-06: "
                        "positive = DEBIT you pay, negative = CREDIT you "
                        "receive; e.g. -0.05 for a $5 credit)")
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
    # 3x-daily bugcheck 2026-10-11 night (MINOR): --limit-price nan/inf
    # was serialized verbatim into the payload ("nan") and 422'd at the
    # API. The price may be NEGATIVE (credit spread = you receive), so
    # only finiteness is enforced, not positivity.
    if args.qty <= 0:
        fail("--qty must be a positive whole number of spreads")
    if not math.isfinite(args.limit_price):
        fail("--limit-price must be a finite number")


def main() -> None:
    args = build_parser().parse_args()
    require_live_confirmation(args)
    validate(args)
    try:
        legs = json.loads(args.legs)
    except json.JSONDecodeError as e:
        fail("invalid --legs JSON: %s" % e)
    if not isinstance(legs, list) or not (2 <= len(legs) <= 4):
        fail("--legs must be a JSON array of 2-4 legs")
    for i, leg in enumerate(legs):
        if not isinstance(leg, dict):
            fail("leg %d: must be an object" % i)
        for k in ("symbol", "side", "position_intent"):
            if k not in leg:
                fail("leg %d: missing '%s'" % (i, k))
        if leg["side"] not in ("buy", "sell"):
            fail("leg %d: side must be buy or sell" % i)
        if leg["position_intent"] not in VALID_INTENTS:
            fail("leg %d: invalid position_intent" % i)
        if not leg["position_intent"].startswith(leg["side"] + "_"):
            fail("leg %d: side and position_intent must agree" % i)
        ratio = leg.get("ratio_qty", 1)
        try:
            value = float(ratio)
        except (ValueError, TypeError):
            fail("leg %d: ratio_qty must be a positive whole number" % i)
        if isinstance(ratio, bool) or not math.isfinite(value) or value <= 0 or not value.is_integer():
            fail("leg %d: ratio_qty must be a positive whole number" % i)
        leg["ratio_qty"] = str(int(value))
        if not isinstance(leg["symbol"], str) or not leg["symbol"].strip():
            fail("leg %d: symbol must be a nonempty string" % i)
        leg["symbol"] = leg["symbol"].strip().upper()
    order = {
        "order_class": "mleg",
        "qty": str(args.qty),
        "type": "limit",
        "time_in_force": args.time_in_force,
        "limit_price": str(args.limit_price),
        "legs": legs,
        "client_order_id": args.client_order_id or str(uuid.uuid4()),
    }
    try:
        result = api_request("POST", f"{trading_base()}/v2/orders",
                             payload=order)
    except AlpacaError as e:
        # 3x-daily bugcheck 2026-10-08 (MEDIUM): port the
        # alpaca_submit_order.py structured-error pattern (see
        # alpaca_option_order.py for the rationale: empty stdout +
        # JSONDecodeError in callers, double-submit risk on blind retry).
        print(json.dumps({
            "error": True,
            "status_code": getattr(e, "status_code", None),
            "outcome_unknown": bool(getattr(e, "outcome_unknown", False)),  # 3x-daily bugcheck 2026-10-14 PM BC14P-9: see alpaca_submit_order.py
            "message": str(e)[:500],
            "legs": len(legs),
            "leg_symbols": [leg.get("symbol") for leg in legs],
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
