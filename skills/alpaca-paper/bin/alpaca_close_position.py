#!/usr/bin/env python3
"""alpaca_close_position — liquidate a position (full or partial by qty)."""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import (AlpacaError, api_request, emit, fail, quote_path,
                        require_live_confirmation, trading_base)


def validate(args: argparse.Namespace) -> None:
    # 3x-daily bugcheck 2026-10-11 night (MINOR): --qty nan/inf slipped
    # past the positivity check (NaN comparisons are False) and was sent
    # to the API as "nan"/"inf" -> 422. Same class as the 2026-10-10
    # alpaca_submit_order.py --qty fix. Finiteness is checked FIRST
    # (2026-10-12 PM: NaN fails every comparison, so a combined check
    # could not produce the finite-specific message).
    if args.qty is not None and not math.isfinite(args.qty):
        fail("--qty must be a finite number")
    if args.qty is not None and args.qty <= 0:
        fail("--qty must be positive")


def main() -> None:
    p = argparse.ArgumentParser(description="Close an Alpaca position.")
    p.add_argument("--symbol", required=True, help="Ticker symbol, e.g. AAPL")
    p.add_argument("--qty", type=float, default=None,
                   help="Partial close quantity (omit to close the full position)")
    # 3x-daily bugcheck 2026-10-12 AM (HIGH-2): live-confirmation guard —
    # closing a position mutates live broker state, so it needs the same
    # --i-understand-this-is-live gate as the submit paths.
    p.add_argument("--i-understand-this-is-live", action="store_true",
                   dest="i_understand_this_is_live",
                   help="REQUIRED to close when ALPACA_ENV=live")
    args = p.parse_args()
    require_live_confirmation(args)
    validate(args)
    # Twice-daily bugcheck 2026-10-06: serialize whole-share quantities as
    # ints ("70"), not floats ("70.0") -- Alpaca may reject non-integer qty
    # strings on whole-share positions (same fix as alpaca_submit_order).
    if args.qty is not None:
        q = args.qty
        qstr = str(int(q)) if float(q).is_integer() else str(q)
        params = {"qty": qstr}
    else:
        params = None
    try:
        result = api_request(
            "DELETE",
            f"{trading_base()}/v2/positions/{quote_path(args.symbol.upper())}",
            params=params,
        )
    except AlpacaError as e:
        # 3x-daily bugcheck 2026-10-08 (LOW): structured JSON on stderr
        # instead of a traceback with empty stdout (same pattern as the
        # submit paths).
        print(json.dumps({
            "error": True,
            "status_code": getattr(e, "status_code", None),
            "outcome_unknown": bool(getattr(e, "outcome_unknown", False)),
            "message": str(e)[:500],
            "symbol": args.symbol.upper(),
        }), file=sys.stderr)
        raise SystemExit(1)
    # 3x-daily bugcheck 2026-10-12 PM (LOW, restored pm3-H guard):
    # fail loud on {"raw": ...} non-JSON 2xx bodies (see
    # alpaca_submit_order.py) instead of emitting a fake close result.
    if isinstance(result, dict) and "raw" in result:
        print("Unexpected close response shape (non-JSON body)",
              file=sys.stderr)
        sys.exit(2)
    # 3x-daily bugcheck 2026-10-14 PM (LOW, BC14P-10): a non-dict 2xx body (e.g. a JSON list) was
    # emitted as a fake close result. Fail loud.
    # 3x-daily bugcheck 2026-10-14 evening (MEDIUM, BC14E-16): was `if result and ...` --
    # a FALSY non-dict 2xx body ([], 0, "") bypassed the guard and the
    # line below emitted a synthesized {"closed": true} the broker
    # never made, on a mutating path. Siblings use `is not None`.
    if result is not None and not isinstance(result, dict):
        print("Unexpected close response shape (non-object body)",
              file=sys.stderr)
        sys.exit(2)
    emit(result if result else {"closed": True, "symbol": args.symbol.upper()})


if __name__ == "__main__":
    main()
