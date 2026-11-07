#!/usr/bin/env python3
"""alpaca_get_order — fetch one order by its Alpaca order id.

Wraps GET /v2/orders/{order_id}. Used by an options sleeve to
verify fill status before promoting a submitted order into a managed
position (pending_entry / pending_exit reconciliation).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import AlpacaError, api_request, emit, quote_path, trading_base, missing_order


def main() -> None:
    p = argparse.ArgumentParser(
        description="Fetch one Alpaca order by id (fill status check).")
    p.add_argument("--order-id", required=True,
                   help="Alpaca order id (UUID)")
    args = p.parse_args()
    try:
        result = api_request(
            "GET", f"{trading_base()}/v2/orders/{quote_path(args.order_id)}"
        )
    except AlpacaError as e:
        # A 404 only establishes absence at this endpoint, not a final order state.
        if getattr(e, "status_code", None) == 404:
            emit(missing_order(args.order_id))
            return
        raise
    # 3x-daily bugcheck 2026-10-10 (MINOR): api_request returns
    # {"raw": text} on non-JSON 2xx bodies; the old code emitted it
    # verbatim and callers expecting an order dict got {"raw": ...}.
    # Fail loud (same class as the alpaca_get_account.py 2026-10-08 fix).
    if isinstance(result, dict) and "raw" in result:
        print("Unexpected order response shape (non-JSON body)",
              file=sys.stderr)
        sys.exit(2)
    # 3x-daily bugcheck 2026-10-14 PM (LOW, BC14P-10): a non-dict 2xx body (e.g. a JSON list) was
    # emitted verbatim; callers expecting an order dict died on .get.
    # Fail loud like the submit bins' non-object guard.
    if result is not None and not isinstance(result, dict):
        print("Unexpected order response shape (non-object body)",
              file=sys.stderr)
        sys.exit(2)
    emit(result if result is not None else {})


if __name__ == "__main__":
    main()
