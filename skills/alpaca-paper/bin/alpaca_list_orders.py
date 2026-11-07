#!/usr/bin/env python3
"""alpaca_list_orders — print open Alpaca orders as JSON (for the
protection gate: every held position must show stop evidence)."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import api_request, emit, fail, trading_base, require_order_response


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Print open Alpaca orders as JSON.")
    ap.add_argument("--status", default="open",
                    help="Order status filter (default: open).")
    ap.add_argument("--limit", type=int, default=500,
                    help="Max orders to return (default: 500).")
    ap.add_argument("--with-coverage", action="store_true", help="Include requested limit and possible truncation without claiming a complete book")
    args = ap.parse_args()
    if not 1 <= args.limit <= 500 or args.status not in ("open", "closed", "all"):
        fail("limit must be1..500 and status open, closed or all")
    orders = api_request(
        "GET", f"{trading_base()}/v2/orders",
        params={"status": args.status, "limit": args.limit,
                "direction": "desc"})
    # 3x-daily bugcheck 2026-10-10 (MINOR): api_request returns
    # {"raw": text} on non-JSON 2xx bodies; the old code emitted it
    # verbatim and callers expecting a list got a dict (same class as
    # the alpaca_get_account.py 2026-10-08 fix). Fail loud.
    if isinstance(orders, dict) and "raw" in orders:
        print("Unexpected orders response shape (non-JSON body)",
              file=sys.stderr)
        sys.exit(2)
    # 3x-daily bugcheck 2026-10-14 PM (LOW, BC14P-10): any other dict body was emitted where
    # callers expect a LIST of orders (exposure._stop_protected_
    # symbols had to defensively unwrap dicts). Fail loud.
    if not isinstance(orders, list):
        print("Unexpected orders response shape (non-array body)",
              file=sys.stderr)
        sys.exit(2)
    for order in orders:
        require_order_response(order)
    coverage = {"requested_limit": args.limit, "returned": len(orders), "possibly_truncated": len(orders) >= args.limit, "snapshot_atomic": False}
    emit({"orders": orders, "coverage": coverage} if args.with_coverage else orders)


if __name__ == "__main__":
    main()
