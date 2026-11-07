---
name: alpaca-paper
description: Trade and inspect Alpaca paper trading accounts with the account identity proven from the configured credentials before any account-level action; use for paper-account reads and orders, and skip for live trading.
version: 1.0.1
---

# Alpaca Paper Trading

## Why this skill exists

The default: Acting on an account before proving which account the keys open.
The cost: Orders placed against the wrong account identity are not a paperwork error; they are trades nobody authorized, on a book nobody was watching.
The replacement: Prove the account identity from the configured credentials before any account level action, and read every submitted order back before reporting it.

## Verify the account identity first

- Call `bin/alpaca_get_account.py` with the configured paper account credentials before any reset, key replacement, pause or resume step and record the account number, equity, cash and buying power it returns.

- For a known account, add `--expect-environment paper --expect-account-id <expected-id>` and, if available, `--expect-account-number <expected-number>`. A mismatch fails without emitting a misleading summary. Keep this identity evidence private. These checks establish the account reached by that request; repeat them when credentials or the account context change.

- Compare that API result with any dashboard view before acting on the dashboard and treat a mismatch as two different accounts until the numbers reconcile.

- Stop an account level action when the dashboard account and the key reached account differ in equity, positions or open orders and name the mismatch as the blocker.

- Re-run the account call after a new key pair is installed and report the account as connected only when that call succeeds with the new keys.

- Keep the secret out of files, logs and chat. The tools read both credentials from the environment and fail closed when either is absent:

```text
ALPACA_KEY_ID=            # credential/account identifier; do not publish it
ALPACA_API_SECRET_KEY=    # the secret; set it in your environment or secret store, never in a file in this folder
ALPACA_ENV=paper          # paper is the default; live requires the explicit confirmation flag as well
```

## Inspect and trade on paper

- This skill activates for paper-account work only: use `ALPACA_ENV=paper`. The shared transport retains an explicitly selected live mode and guarded live-order support for separately authorized workflows; their existence does not authorize this skill to trade live. Inspect each command’s actual guard before any separately authorized live use.

- List positions with `bin/alpaca_list_positions.py` and open orders before submitting, cancelling or closing anything so the action targets the current book.

- Submit orders with `bin/alpaca_submit_order.py` and keep the client order id stable across retries of the same intent so a retry cannot duplicate the order.

- Preserve `client_order_id` from every submit result or error. For an unknown outcome, reconcile with `bin/alpaca_get_order.py --client-order-id <same-id>` and the correctly identified account before deciding whether another request is warranted. A stable ID helps recover the original intent; it does not turn a timeout, redirect, malformed acknowledgement or 404 into a verified rejection or fill.

- Cancel with `bin/alpaca_cancel_order.py` and close with `bin/alpaca_close_position.py` only on the user word for that symbol.

- Read a submitted order back from the broker before reporting it filled and report the broker status, filled quantity and average price from that read back.

## Diagnose an order refusal

- Capture the full refusal body before diagnosing a failed order and read its code field first.

- Treat code 40310000 as insufficient buying power rather than an auth, proxy or transport failure and check it against the account call showing regt buying power and effective buying power.

- Diagnose transport first with an authorized read-only account or data call. A deliberately invalid-order probe is an optional paper-only diagnostic requiring explicit authorization for that broker request; its validation error proves only the reached validation boundary, not order execution.

- Report a buying power refusal as an account state blocker with the long and short market values that produced it and never as an execution-code failure.

## Pull bars and options data

- Pass an explicit start value on every stock bars call to make the requested time window explicit; the historical incident returned null bars without one, but endpoint defaults can change. Verify ordering and pagination on the current response.

- Follow the next page token and slice the newest bars on the client side when a limit matters.

- Prefer an explicitly entitled SIP feed for historical hourly or finer consolidated-volume work. Check the current subscription and endpoint entitlement; do not assume the origin account’s historical restriction applies to every adopter. Stamp the actual feed and delay, and keep IEX-only volume distinct from consolidated volume.

- Use options contracts under the v2 contracts path with tradable filtered on the client side and options quotes and snapshots under the v1beta1 market data paths.

- `alpaca_option_chain.py` follows all continuation pages within `--max-pages` and returns the established array only when coverage and tradability are resolved. Increase the page budget to finish a larger chain, or use `--with-coverage` to retain partial contracts, unknown-tradability rows and the continuation token explicitly. `alpaca_list_orders.py --with-coverage` identifies when its requested limit may truncate a changing order list. Neither page traversal nor a limit implies an atomic broker snapshot.

- Read each option quote's `quote_status`, `timestamp` and `feed`. Missing, invalid, one-sided or crossed quotes have no actionable synthetic midpoint. A valid bid/ask calculation alone does not establish quote freshness, consolidated coverage or executable size.

- Treat delayed sip as invalid on historical bars calls and never send sort, direction or tradable parameters to the options contracts endpoint.

## Credentials

- No credential file ships with this skill, and none may be added to it. Set ALPACA_KEY_ID and ALPACA_API_SECRET_KEY in the environment of the process that runs the tools.

## Alternatives for better results

- Reconcile the broker book against the local book before any trading session and let the broker state win when they differ.

- Snapshot equity, positions and open orders to disk before an account reset so the pre reset state stays provable after the wipe.
