#!/usr/bin/env python3
"""alpaca_get_account — print the Alpaca account summary as JSON."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import api_request, emit, fail, trading_base


def main() -> None:
    argparse.ArgumentParser(description="Print the Alpaca account summary as JSON.").parse_args()
    acct = api_request("GET", f"{trading_base()}/v2/account")
    # 3x-daily bugcheck 2026-10-08 (LOW): api_request returns
    # {"raw": text} on non-JSON 2xx bodies; the old isinstance check
    # passed that and emitted an all-None account summary. Fail loud.
    if not isinstance(acct, dict) or "raw" in acct:
        fail("Unexpected account response shape")
    emit(
        {
            "account_number": acct.get("account_number"),
            "status": acct.get("status"),
            "equity": acct.get("equity"),
            "cash": acct.get("cash"),
            "buying_power": acct.get("buying_power"),
            "daytrade_count": acct.get("daytrade_count"),
            "pattern_day_trader": acct.get("pattern_day_trader"),
            "trading_blocked": acct.get("trading_blocked"),
        }
    )


if __name__ == "__main__":
    main()
