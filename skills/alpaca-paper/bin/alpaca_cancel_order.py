#!/usr/bin/env python3
"""alpaca_cancel_order — cancel an open order by its Alpaca order id."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import (AlpacaError, api_request, emit, quote_path,
                        require_live_confirmation, trading_base)


def main() -> None:
    p = argparse.ArgumentParser(description="Cancel an open Alpaca order.")
    p.add_argument("--order-id", required=True, help="Alpaca order id (UUID)")
    # 3x-daily bugcheck 2026-10-12 AM (HIGH-1): live-confirmation guard —
    # cancels mutate live broker state, so they need the same
    # --i-understand-this-is-live gate as the submit paths.
    p.add_argument("--i-understand-this-is-live", action="store_true",
                   dest="i_understand_this_is_live",
                   help="REQUIRED to cancel when ALPACA_ENV=live")
    args = p.parse_args()
    require_live_confirmation(args)
    try:
        result = api_request(
            "DELETE", f"{trading_base()}/v2/orders/{quote_path(args.order_id)}"
        )
    except AlpacaError as e:
        # 3x-daily bugcheck 2026-10-08 (LOW): structured JSON on stderr
        # instead of a traceback with empty stdout (same pattern as the
        # submit paths). A 422 on an already-filled order is a normal
        # race; callers can now tell it apart from a real failure.
        print(json.dumps({
            "error": True,
            "status_code": getattr(e, "status_code", None),
            "outcome_unknown": bool(getattr(e, "outcome_unknown", False)),  # 3x-daily bugcheck 2026-10-14 PM BC14P-9: DELETE is non-idempotent; see alpaca_submit_order.py
            "message": str(e)[:500],
            "order_id": args.order_id,
        }), file=sys.stderr)
        raise SystemExit(1)
    # 3x-daily bugcheck 2026-10-13 PM (LOW, BC13PM-7): api_request
    # returns {"raw": ...} on a non-JSON 2xx body; the old code
    # discarded the result and unconditionally reported a confirmed
    # cancellation. Every sibling mutating bin got this guard on
    # 2026-10-12 (pm3-H); cancel was missed. Fail loud instead.
    if isinstance(result, dict) and "raw" in result:
        print("Unexpected cancel response shape (non-JSON body)",
              file=sys.stderr)
        raise SystemExit(2)
    if result is not None and not isinstance(result, dict):
        print("Unexpected cancel response shape (non-object body)",
              file=sys.stderr)
        raise SystemExit(2)
    emit({"cancelled": True, "order_id": args.order_id})


if __name__ == "__main__":
    main()
