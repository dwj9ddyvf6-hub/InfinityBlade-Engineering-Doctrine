# Alpaca API details (alpaca-paper skill)

Bulky detail the CLIs encode; kept here so `SKILL.md` stays lean.
Original API review: 2026-09-25. Order/bracket and contracts-pagination details rechecked against the linked public specifications on 2026-11-07. This is a source review and an offline client audit, not an authenticated endpoint or account-entitlement test. If an endpoint changes, update the CLI in `bin/` and note it here.

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
Read from the process environment at call time by `bin/alpaca_lib.py`, including after in-process rotation. Provider error bodies redact both values before truncation. A trading URL must match the selected `ALPACA_ENV`; the market-data host is shared across environments.
Discover the host’s actual Alpaca capabilities before choosing a route. A connector may exist on some hosts; never invent one when absent. Use the authorized connector or shipped CLI and keep credentials and account identifiers out of public artifacts.

## Endpoints used

- `GET /v2/account` — id, account_number, status, equity, cash, buying_power, daytrade_count, pattern_day_trader, trading_blocked. The CLI adds the selected environment and optional `--expect-account-id`, `--expect-account-number` and `--expect-environment` assertions. Account identity fields must exist; optional financial fields remain provider values and are not replaced with guessed zeroes.
- `GET /v2/positions` — all open positions (JSON array).
- `POST /v2/orders` — JSON body: symbol, side (buy|sell), qty or notional,
  type (market|limit|stop|stop_limit), time_in_force (day|gtc|opg|cls|ioc|fok),
  limit_price, stop_price, client_order_id (always sent; UUID4 generated when
  omitted for idempotency), order_class=bracket + take_profit{limit_price} /
  stop_loss{stop_price} for brackets. Market and limit bracket entries are supported; both exits are required, their prices must agree with the entry direction, and bracket/OCO TIF is day or gtc. OCO's side describes its exits, the inverse of a bracket entry side. Provider eligibility and actual fill state still require readback. [Alpaca's order contract](https://docs.alpaca.markets/us/docs/orders-at-alpaca) is the source for these relationships.
  notional is supported on market orders only.
- `GET /v2/orders/{order_id}` or `GET /v2/orders:by_client_order_id?client_order_id=...` — reconcile by the broker order ID or the client intent ID retained even when the submission acknowledgement was lost.
- `GET /v2/options/contracts` — the contract-list CLI follows `next_page_token`, validates each row and filters explicit `tradable: true`. The page limit is 1–10,000; omitted expiration bounds retain provider defaults and do not mean every expiration. See [the contracts specification](https://docs.alpaca.markets/us/reference/get-options-contracts) and [documented default expiration scope](https://docs.alpaca.markets/us/docs/options-trading).
- `DELETE /v2/orders/{order_id}` — cancel; returns 204.
- `DELETE /v2/positions/{symbol}?qty=N` — close full position, or partial with qty.
- `GET /v2/stocks/{symbol}/bars?timeframe=1H&limit=N` (data host) — fields per
  bar: t (RFC3339), o, h, l, c, v. The actual configured `feed` is part of the evidence identity; check the CLI default and the account’s entitlement. IEX volume is not consolidated SIP volume. `adjustment`
  defaults to raw.

## Error handling

- 429 → bounded exponential backoff (4 total attempts in `alpaca_lib.py`), respecting a longer numeric or HTTP-date `Retry-After`. The default 120-second monotonic budget bounds retries/backoff; a longer provider delay is surfaced for later recovery rather than slept indefinitely. Each socket timeout is at most 30 seconds and clipped to the remaining budget. A socket timeout is not a strict total wall-clock deadline against a peer that continually trickles bytes.
- Other 4xx/5xx → provider error surfaced without blind HTTP retry. A mutating request with an ambiguous transport failure or 5xx is marked outcome-unknown and requires broker-state reconciliation before any retry. Read-only transport failures use the bounded retry path.
- Missing `ALPACA_KEY_ID`/`ALPACA_API_SECRET_KEY` → stderr, exit 1 (fail closed).
- Bad `ALPACA_ENV` → stderr, exit 1.
- Live order without `--i-understand-this-is-live` → stderr, exit 3.

## Notes

- Paper accounts reset independently of live accounts; keys are per-account.
- Day-trade count matters even in paper: `daytrade_count >= 3` in 5 days flags
  pattern-day-trader restrictions on small accounts.
- Bar arrays are sorted newest-last by actual timestamp instant, with equivalent boundary duplicates collapsed. Missing/invalid OHLCV, contradictory price geometry, conflicting duplicates, out-of-window rows, token cycles or exhausted traversal budgets fail explicitly. These checks establish returned-payload integrity; they do not prove every expected exchange session exists.
- Quantities, supplied prices and spread ratios are parsed with decimal arithmetic. Whole quantities remain integer strings; fractional precision and signed credit/debit spread prices are preserved. Neither parsing nor a successful acknowledgement proves provider eligibility, option approval, buying power or a fill.

## Acknowledgement, final state, and absence

The public client preserves each broker response and distinguishes request acceptance from a completed market action. Cancel and close responses add `request_accepted: true`, `final_state_verified: false`, and `reconciliation_required: true`. A cancellation request reports `cancel_requested: true` and `cancelled: null`; a position-close request reports `close_requested: true` and `closed: null`. Consumers must reconcile the order and position through the correctly identified account before treating either action as complete. Existing broker order IDs, statuses and other response fields remain available.

A 404 from the one-order endpoint produces `status: "not_found"`, `terminal_state_verified: false`, and `reconciliation_required: true`. It establishes absence at the queried endpoint. It does not establish cancellation, expiry, a completed fill, or a safe basis for removing a pending record: first reconcile the account, paper/live environment, order identifier and relevant broker state.

The transport requires HTTPS on an allowlisted host and the default TLS port, rejects URL credentials and fragments, and disables redirects so API headers are never forwarded automatically. Mutating requests with a transport failure, 408, redirect, server error or invalid successful response carry an unknown-outcome indication; resolve that uncertainty before retrying. Successful order acknowledgements require a broker ID/status and the submitted client ID. A malformed acknowledgement keeps that client ID in structured error output for the recovery lookup; it never means “safe to resubmit.” Offline regression tests use transport doubles only; they do not establish account identity, entitlements, live connectivity, market fills or order-state convergence.

## Coverage and analytical use

- A complete option contract traversal preserves the existing normalized array output. `--with-coverage` returns `contracts`, `unverified_contracts` and `coverage`: source-page completion, page count, unique rows, excluded nontradable rows, unknown tradability and continuation token. Incomplete coverage without that flag exits nonzero. Increase `--max-pages` to complete the same query, preserving its filters; pagination completeness applies only to that query and is not an atomic snapshot.
- The orders list retains its existing array default. `--with-coverage` adds the requested limit, returned count, `possibly_truncated` and `snapshot_atomic: false`; use a separately defined history-reconciliation process when a complete order history is needed.
- Option quotes retain bid/ask and add `quote_status`, timestamp and feed. Only finite, positive, uncrossed two-sided quotes get a midpoint/spread calculation. Missing, invalid, crossed and one-sided observations remain distinguishable; no zero-valued fabricated quote represents a missing symbol.
- A multi-leg order is submitted as one broker request with its leg ratios and signed net limit. Preserve parent and leg statuses/filled quantities when reconciling partial fills; an accepted combined request does not prove every requested spread unit has filled. See [Alpaca's multi-leg guide](https://docs.alpaca.markets/us/docs/options-level-3-trading).
