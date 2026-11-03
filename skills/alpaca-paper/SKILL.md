---
name: alpaca-paper
description: Trade and inspect Alpaca paper trading accounts with the account identity proven from the configured credentials before any account-level action; use for paper-account reads and orders, and skip for live trading.
version: 1.0.0
---

# Alpaca Paper Trading

## Why this skill exists

The default: Acting on an account before proving which account the keys open.
The cost: Orders placed against the wrong account identity are not a paperwork error; they are trades nobody authorized, on a book nobody was watching.
The replacement: Prove the account identity from the configured credentials before any account level action, and read every submitted order back before reporting it.

## Verify the account identity first

- Call `bin/alpaca_get_account.py` with the configured paper account credentials before any reset, key replacement, pause or resume step and record the account number, equity, cash and buying power it returns.

- Compare that API result with any dashboard view before acting on the dashboard and treat a mismatch as two different accounts until the numbers reconcile.

- Stop an account level action when the dashboard account and the key reached account differ in equity, positions or open orders and name the mismatch as the blocker.

- Re-run the account call after a new key pair is installed and report the account as connected only when that call succeeds with the new keys.

- Keep the secret out of files, logs and chat. The tools read both credentials from the environment and fail closed when either is absent:

```text
ALPACA_KEY_ID=            # the public key identifier, not a secret
ALPACA_API_SECRET_KEY=    # the secret; set it in your environment or secret store, never in a file in this folder
ALPACA_ENV=paper          # paper is the default; live requires the explicit confirmation flag as well
```

## Inspect and trade on paper

- Default every call to the paper base and require both the live environment flag and the explicit live confirmation flag before any live base call.

- List positions with `bin/alpaca_list_positions.py` and open orders before submitting, cancelling or closing anything so the action targets the current book.

- Submit orders with `bin/alpaca_submit_order.py` and keep the client order id stable across retries of the same intent so a retry cannot duplicate the order.

- Cancel with `bin/alpaca_cancel_order.py` and close with `bin/alpaca_close_position.py` only on the user word for that symbol.

- Read a submitted order back from the broker before reporting it filled and report the broker status, filled quantity and average price from that read back.

## Diagnose an order refusal

- Capture the full refusal body before diagnosing a failed order and read its code field first.

- Treat code 40310000 as insufficient buying power rather than an auth, proxy or transport failure and check it against the account call showing regt buying power and effective buying power.

- Prove the transport healthy with a control call that returns a clean validation error on a deliberately invalid order before blaming the calling code.

- Report a buying power refusal as an account state blocker with the long and short market values that produced it and never as an execution-code failure.

## Pull bars and options data

- Pass an explicit start value on every stock bars call because the bars endpoint returns null bars without one and returns the earliest bars from that start.

- Follow the next page token and slice the newest bars on the client side when a limit matters.

- Use the sip feed for historical hourly or finer volume work and expect recent sip data to lag and to refuse on this subscription.

- Use options contracts under the v2 contracts path with tradable filtered on the client side and options quotes and snapshots under the v1beta1 market data paths.

- Treat delayed sip as invalid on historical bars calls and never send sort, direction or tradable parameters to the options contracts endpoint.

## Credentials

- No credential file ships with this skill, and none may be added to it. Set ALPACA_KEY_ID and ALPACA_API_SECRET_KEY in the environment of the process that runs the tools.

## Alternatives for better results

- Reconcile the broker book against the local book before any trading session and let the broker state win when they differ.

- Snapshot equity, positions and open orders to disk before an account reset so the pre reset state stays provable after the wipe.
