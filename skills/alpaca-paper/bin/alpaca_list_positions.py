#!/usr/bin/env python3
"""alpaca_list_positions — print all open positions as JSON."""
import argparse
from decimal import Decimal, InvalidOperation
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import AlpacaError, api_request, emit, trading_base


def _normalize_qty(positions):
    """Normalize decimal quantities exactly, preserving every position field.

    Binary float conversion can change a whole quantity above 2**53 or round
    a fractional quantity to an integer. Invalid quantities must not masquerade
    as a complete, usable broker position list.
    """
    if not isinstance(positions, list):
        raise AlpacaError("Positions must be an array")
    normalized = []
    for row in positions:
        if not isinstance(row, dict) or "qty" not in row or isinstance(row["qty"], bool):
            raise AlpacaError("Position lacks a valid quantity")
        try:
            quantity = Decimal(str(row["qty"]))
        except (InvalidOperation, ValueError) as error:
            raise AlpacaError("Position quantity is not decimal") from error
        if not quantity.is_finite():
            raise AlpacaError("Position quantity must be finite")
        value = str(int(quantity)) if quantity == quantity.to_integral_value() else format(quantity, "f")
        normalized.append({**row, "qty": value})
    return normalized


def main() -> None:
    argparse.ArgumentParser(description="Print all open Alpaca positions as JSON.").parse_args()
    positions = api_request("GET", f"{trading_base()}/v2/positions")
    # 3x-daily bugcheck 2026-10-10 (MINOR): api_request returns
    # {"raw": text} on non-JSON 2xx bodies; the old code normalized and
    # emitted it verbatim. Fail loud (same class as the
    # alpaca_get_account.py 2026-10-08 fix).
    if isinstance(positions, dict) and "raw" in positions:
        print("Unexpected positions response shape (non-JSON body)",
              file=sys.stderr)
        sys.exit(2)
    # 3x-daily bugcheck 2026-10-14 PM (LOW, BC14P-10): any other dict body passed through
    # _normalize_qty and was emitted where every caller expects a
    # LIST of positions. Fail loud.
    if not isinstance(positions, list):
        print("Unexpected positions response shape (non-array body)",
              file=sys.stderr)
        sys.exit(2)
    if any(not isinstance(p, dict) or not isinstance(p.get("symbol"), str) or not p["symbol"].strip() for p in positions):
        raise AlpacaError("Position list contains an invalid symbol/record")
    emit(_normalize_qty(positions))


if __name__ == "__main__":
    main()
