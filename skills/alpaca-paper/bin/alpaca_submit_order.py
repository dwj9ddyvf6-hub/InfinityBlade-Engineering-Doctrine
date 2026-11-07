#!/usr/bin/env python3
"""alpaca_submit_order — submit a market, limit, or bracket order as JSON.

Every order carries a client_order_id for idempotency: pass
--client-order-id or one is generated (UUID4). Without it, a retry could
double-fill.
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
    require_order_response,
    decimal_argument,
    decimal_text,
    trading_base,
)

VALID_SIDES = {"buy", "sell"}
VALID_TYPES = {"market", "limit", "stop", "stop_limit"}
VALID_TIF = {"day", "gtc", "opg", "cls", "ioc", "fok"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Submit an Alpaca order (paper by default).")
    p.add_argument("--symbol", required=True, help="Ticker symbol, e.g. AAPL")
    p.add_argument("--side", required=True, choices=sorted(VALID_SIDES))
    size = p.add_mutually_exclusive_group(required=True)
    size.add_argument("--qty", type=decimal_argument, help="Fractional or whole share quantity")
    size.add_argument("--notional", type=decimal_argument, help="Dollar notional (market orders only)")
    p.add_argument("--type", default="market", choices=sorted(VALID_TYPES),
                   dest="order_type", help="Order type (default: market)")
    p.add_argument("--time-in-force", default="day", choices=sorted(VALID_TIF),
                   dest="time_in_force", help="Time in force (default: day)")
    p.add_argument("--limit-price", type=decimal_argument, default=None,
                   help="Limit price (required for limit/stop_limit; entry leg of brackets)")
    p.add_argument("--stop-price", type=decimal_argument, default=None,
                   help="Stop trigger price (required for stop/stop_limit)")
    p.add_argument("--client-order-id", default=None,
                   help="Idempotency key; a UUID4 is generated when omitted")
    p.add_argument("--bracket", action="store_true",
                   help="Submit as order_class=bracket (requires --take-profit and --stop-loss)")
    p.add_argument("--oco", action="store_true",
                   help="Submit as order_class=oco: take-profit limit + stop-loss "
                        "as one-cancels-other legs (requires --take-profit and "
                        "--stop-loss). Top-level type is forced to limit; the "
                        "legs carry the prices.")
    p.add_argument("--take-profit", type=decimal_argument, default=None,
                   help="Bracket/OCO take-profit limit price")
    p.add_argument("--stop-loss", type=decimal_argument, default=None,
                   help="Bracket/OCO stop-loss stop price")
    p.add_argument("--i-understand-this-is-live", action="store_true",
                   dest="i_understand_this_is_live",
                   help="REQUIRED to submit when ALPACA_ENV=live")
    return p


def validate(args: argparse.Namespace) -> None:
    if not args.symbol.strip():
        fail("--symbol must be nonempty")
    if args.client_order_id is not None and not args.client_order_id.strip():
        fail("--client-order-id must be nonempty when supplied")
    # 3x-daily bugcheck 2026-10-09 (LOW): --oco forces the container leg to
    # type=limit with prices on the OCO legs (main() pops the top-level
    # prices), so a top-level --limit-price must not be required for OCO --
    # the old check rejected valid `--type limit --oco` orders.
    if (args.order_type in ("limit", "stop_limit")
            and args.limit_price is None and not args.oco):
        fail(f"--limit-price is required for order type {args.order_type!r}")
    if args.order_type in ("stop", "stop_limit") and args.stop_price is None:
        fail(f"--stop-price is required for order type {args.order_type!r}")
    if args.notional is not None and args.order_type != "market":
        fail("--notional is only supported with --type market")
    if args.bracket and args.oco:
        fail("--bracket and --oco are mutually exclusive")
    if args.bracket:
        if args.order_type not in ("market", "limit"):
            fail("--bracket supports --type market or limit for the entry leg")
        if args.take_profit is None or args.stop_loss is None:
            fail("--bracket requires both --take-profit and --stop-loss")
    if args.oco:
        if args.take_profit is None or args.stop_loss is None:
            fail("--oco requires both --take-profit and --stop-loss")
    if args.bracket or args.oco:
        if args.time_in_force not in ("day", "gtc"):
            fail("--bracket and --oco require --time-in-force day or gtc")
        if args.qty is None:
            fail("--bracket and --oco require --qty")
        # A bracket side is its entry; an OCO side is its pair of exits.
        profit_above_stop = (args.side == "buy") if args.bracket else (args.side == "sell")
        if ((profit_above_stop and args.take_profit <= args.stop_loss)
                or (not profit_above_stop and args.take_profit >= args.stop_loss)):
            fail("--take-profit and --stop-loss prices are reversed for the order side")
    if args.qty is not None and args.qty <= 0:
        fail("--qty must be positive")
    # 3x-daily bugcheck 2026-10-10 (LOW): reject non-finite qty/notional
    # (nan/inf). NaN comparisons are False, so --qty nan used to slip past
    # the positivity check and die later in int(_q) with an uncaught
    # ValueError (raw traceback on stderr, empty stdout) instead of the
    # standard ERROR path.
    if args.qty is not None and not math.isfinite(args.qty):
        fail("--qty must be a finite number")
    if args.notional is not None and not math.isfinite(args.notional):
        fail("--notional must be a finite number")
    if args.notional is not None and args.notional <= 0:
        fail("--notional must be positive")
    # 3x-daily bugcheck 2026-10-11 night (MINOR): extend the 2026-10-10
    # qty/notional finite check to the price params. NaN comparisons are
    # False, so --limit-price nan used to slip through and get serialized
    # into the payload as "nan" (422 at the API) instead of failing on
    # the standard ERROR path.
    for _name in ("limit_price", "stop_price", "take_profit", "stop_loss"):
        _v = getattr(args, _name)
        if _v is not None and not math.isfinite(_v):
            fail("--%s must be a finite number" % _name.replace("_", "-"))
        # 3x-daily bugcheck 2026-10-14 evening (LOW, BC14E-16): prices were finite-checked
        # but never positivity-checked (option_order's validate does);
        # --limit-price -5 serialized straight into the POST payload.
        if _v is not None and _v <= 0:
            fail("--%s must be positive" % _name.replace("_", "-"))
    # 3x-daily bugcheck 2026-10-14 evening (LOW, BC14E-16): the notional check above tests
    # the PRE-OCO type, but main() forces type=limit for --oco while
    # keeping notional and no qty -- a payload Alpaca always rejects.
    if args.oco and args.notional is not None:
        fail("--notional cannot be combined with --oco (OCO orders "
             "require --qty)")


def main() -> None:
    args = build_parser().parse_args()
    require_live_confirmation(args)
    validate(args)

    client_order_id = args.client_order_id or str(uuid.uuid4())
    order: dict = {
        "symbol": args.symbol.strip().upper(),
        "side": args.side,
        "type": args.order_type,
        "time_in_force": args.time_in_force,
        "client_order_id": client_order_id,
    }
    if args.qty is not None:
        # Audit 2026-10-06: whole-number quantities must serialize as ints
        # ("70", not "70.0"). Alpaca rejects non-integer qty strings for
        # whole-share orders; fractional shares still pass through.
        order["qty"] = decimal_text(args.qty)
    else:
        order["notional"] = str(args.notional)
    if args.limit_price is not None:
        order["limit_price"] = str(args.limit_price)
    if args.stop_price is not None:
        order["stop_price"] = str(args.stop_price)
    if args.bracket:
        order["order_class"] = "bracket"
        order["take_profit"] = {"limit_price": str(args.take_profit)}
        order["stop_loss"] = {"stop_price": str(args.stop_loss)}
    if args.oco:
        order["type"] = "limit"  # container leg; prices live on the OCO legs
        order.pop("limit_price", None)
        order.pop("stop_price", None)
        order["order_class"] = "oco"
        order["take_profit"] = {"limit_price": str(args.take_profit)}
        order["stop_loss"] = {"stop_price": str(args.stop_loss)}

    try:
        result = api_request("POST", f"{trading_base()}/v2/orders", payload=order)
        require_order_response(result, mutation=True, client_order_id=order["client_order_id"])
    except AlpacaError as e:
        # 3x-daily audit 2026-10-07: emit structured JSON instead of a
        # traceback so callers get machine-readable
        # errors with the HTTP status. Follows alpaca_get_order.py pattern.
        # Bug fix 2026-10-07: print to stderr, not stdout -- run_cli()
        # builds SkillError from stderr only, so stdout errors arrived
        # as "empty error detail".
        import json as _json
        print(_json.dumps({
            "error": True,
            "client_order_id": order["client_order_id"],
            "reconciliation_required": bool(getattr(e, "outcome_unknown", False)),
            "status_code": getattr(e, "status_code", None),
            # 3x-daily bugcheck 2026-10-14 PM (MEDIUM, BC14P-9): alpaca_lib marks non-idempotent
            # network failures outcome_unknown=True (the order may
            # exist at the broker), but this payload dropped the flag --
            # callers could not tell a definite rejection from a
            # maybe-submitted order and could blind-retry into a double
            # submit. close_position already carried it; port it here.
            "outcome_unknown": bool(getattr(e, "outcome_unknown", False)),
            "message": str(e)[:500],
            "symbol": args.symbol.upper(),
            "side": args.side,
        }), file=sys.stderr)
        raise SystemExit(1)
    # 3x-daily bugcheck 2026-10-12 PM (LOW, restored pm3-H guard): api_request
    # returns {"raw": text} on non-JSON 2xx bodies; emitting it verbatim
    # would hand callers a fake "order" with no id/status. Fail loud
    # (same class as the read-path bins, 2026-10-10).
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
