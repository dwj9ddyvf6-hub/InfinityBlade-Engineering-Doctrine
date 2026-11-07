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
from alpaca_lib import AlpacaError, api_request, emit, quote_path, trading_base, missing_order, require_order_response


def main() -> None:
    p = argparse.ArgumentParser(
        description="Fetch one Alpaca order by id (fill status check).")
    identity = p.add_mutually_exclusive_group(required=True)
    identity.add_argument("--order-id",
                   help="Alpaca order id (UUID)")
    identity.add_argument("--client-order-id", help="Original intent ID, including an ambiguous submission's returned client_order_id")
    args = p.parse_args()
    try:
        if args.client_order_id:
            result = api_request("GET", f"{trading_base()}/v2/orders:by_client_order_id",
                                 params={"client_order_id": args.client_order_id})
        else:
            result = api_request("GET", f"{trading_base()}/v2/orders/{quote_path(args.order_id)}")
        require_order_response(result, client_order_id=args.client_order_id)
        if args.order_id and result["id"] != args.order_id:
            raise AlpacaError("Order lookup returned a different order ID")
    except AlpacaError as e:
        # A 404 only establishes absence at this endpoint, not a final order state.
        if getattr(e, "status_code", None) == 404:
            missing = missing_order(args.order_id or args.client_order_id)
            if args.client_order_id:
                missing["client_order_id"] = args.client_order_id
            emit(missing)
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
