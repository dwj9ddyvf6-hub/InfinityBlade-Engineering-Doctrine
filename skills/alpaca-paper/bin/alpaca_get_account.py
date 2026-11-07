#!/usr/bin/env python3
"""alpaca_get_account — print the Alpaca account summary as JSON."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import api_request, emit, fail, trading_base


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the Alpaca account summary as JSON.")
    parser.add_argument("--expect-account-id", help="Assert the configured account UUID before emitting its summary")
    parser.add_argument("--expect-account-number", help="Assert the configured account number")
    parser.add_argument("--expect-environment", choices=("paper", "live"), help="Assert the selected environment before requesting account data")
    args = parser.parse_args()
    environment = "live" if trading_base().startswith("https://api.") else "paper"
    if args.expect_environment is not None and args.expect_environment != environment:
        fail("Configured environment does not match --expect-environment")
    acct = api_request("GET", f"{trading_base()}/v2/account")
    # 3x-daily bugcheck 2026-10-08 (LOW): api_request returns
    # {"raw": text} on non-JSON 2xx bodies; the old isinstance check
    # passed that and emitted an all-None account summary. Fail loud.
    if not isinstance(acct, dict) or "raw" in acct:
        fail("Unexpected account response shape")
    if not all(isinstance(acct.get(k), str) and acct[k].strip() for k in ("id", "account_number", "status")):
        fail("Account response lacks the identity/status required to identify the account")
    if args.expect_account_id is not None and args.expect_account_id != acct["id"]:
        fail("Configured account does not match --expect-account-id")
    if args.expect_account_number is not None and args.expect_account_number != acct["account_number"]:
        fail("Configured account does not match --expect-account-number")
    emit(
        {
            "id": acct["id"],
            "environment": environment,
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
