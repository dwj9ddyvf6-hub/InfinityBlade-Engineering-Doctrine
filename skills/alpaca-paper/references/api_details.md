# Alpaca API details (alpaca-paper skill)

Bulky detail the CLIs encode; kept here so `SKILL.md` stays lean.
Verified against Alpaca's public docs on 2026-09-25. If an endpoint
changes, update the CLI in `bin/` and note it here.

## Hosts

| Purpose  | Host                          |
|----------|-------------------------------|
| Trading  | `https://paper-api.alpaca.markets` (paper) |
| Market data | `https://data.alpaca.markets` |

The live trading base (`https://api.alpaca.markets`) is resolved only from
`ALPACA_ENV=live`; it is never used unless that flag is set, and order CLIs
additionally refuse without `--i-understand-this-is-live`.

## Auth

Headers on every request:
`APCA-API-KEY-ID: <ALPACA_KEY_ID>`, `APCA-API-SECRET-KEY: <ALPACA_API_SECRET_KEY>`.
Read from the process environment at call time by `bin/alpaca_lib.py`.
Discover the host’s actual Alpaca capabilities before choosing a route. A connector may exist on some hosts; never invent one when absent. Use the authorized connector or shipped CLI and keep credentials and account identifiers out of public artifacts.

## Endpoints used

- `GET /v2/account` — equity, cash, buying_power, daytrade_count, pattern_day_trader, trading_blocked.
- `GET /v2/positions` — all open positions (JSON array).
- `POST /v2/orders` — JSON body: symbol, side (buy|sell), qty or notional,
  type (market|limit|stop|stop_limit), time_in_force (day|gtc|opg|cls|ioc|fok),
  limit_price, stop_price, client_order_id (always sent; UUID4 generated when
  omitted for idempotency), order_class=bracket + take_profit{limit_price} /
  stop_loss{stop_price} for brackets. Bracket support is bounded by the current provider contract and CLI validation; do not infer a universal limit-only requirement from a historical example.
  notional is supported on market orders only.
- `DELETE /v2/orders/{order_id}` — cancel; returns 204.
- `DELETE /v2/positions/{symbol}?qty=N` — close full position, or partial with qty.
- `GET /v2/stocks/{symbol}/bars?timeframe=1H&limit=N` (data host) — fields per
  bar: t (RFC3339), o, h, l, c, v. The actual configured `feed` is part of the evidence identity; check the CLI default and the account’s entitlement. IEX volume is not consolidated SIP volume. `adjustment`
  defaults to raw.

## Error handling

- 429 → bounded exponential backoff (4 total attempts in `alpaca_lib.py`), respecting a longer numeric `Retry-After`.
- Other 4xx/5xx → provider error surfaced without blind HTTP retry. A mutating request with an ambiguous transport failure or 5xx is marked outcome-unknown and requires broker-state reconciliation before any retry. Read-only transport failures use the bounded retry path.
- Missing `ALPACA_KEY_ID`/`ALPACA_API_SECRET_KEY` → stderr, exit 1 (fail closed).
- Bad `ALPACA_ENV` → stderr, exit 1.
- Live order without `--i-understand-this-is-live` → stderr, exit 3.

## Notes

- Paper accounts reset independently of live accounts; keys are per-account.
- Day-trade count matters even in paper: `daytrade_count >= 3` in 5 days flags
  pattern-day-trader restrictions on small accounts.
- 1H bars are newest-last in the array; the CLI preserves API order.

## Acknowledgement, final state, and absence

The public client preserves each broker response and distinguishes request acceptance from a completed market action. Cancel and close responses add `request_accepted: true`, `final_state_verified: false`, and `reconciliation_required: true`. A cancellation request reports `cancel_requested: true` and `cancelled: null`; a position-close request reports `close_requested: true` and `closed: null`. Consumers must reconcile the order and position through the correctly identified account before treating either action as complete. Existing broker order IDs, statuses and other response fields remain available.

A 404 from the one-order endpoint produces `status: "not_found"`, `terminal_state_verified: false`, and `reconciliation_required: true`. It establishes absence at the queried endpoint. It does not establish cancellation, expiry, a completed fill, or a safe basis for removing a pending record: first reconcile the account, paper/live environment, order identifier and relevant broker state.

The transport requires HTTPS on an allowlisted host and the default TLS port, rejects URL credentials and fragments, and disables redirects so API headers are never forwarded automatically. Mutating requests with a transport failure, server error or invalid successful response carry an unknown-outcome indication; resolve that uncertainty before retrying. Rate-limited reads honor numeric `Retry-After` alongside exponential backoff. Bar pagination that exhausts its explicit budget or makes no progress fails instead of presenting an incomplete old window as complete data. Offline regression tests use transport doubles only; they do not establish account identity, entitlements, live connectivity, market fills or order-state convergence.
