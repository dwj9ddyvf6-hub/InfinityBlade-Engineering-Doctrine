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
There is no connector for Alpaca: never invent one, and never persist keys.

## Endpoints used

- `GET /v2/account` — equity, cash, buying_power, daytrade_count, pattern_day_trader, trading_blocked.
- `GET /v2/positions` — all open positions (JSON array).
- `POST /v2/orders` — JSON body: symbol, side (buy|sell), qty or notional,
  type (market|limit|stop|stop_limit), time_in_force (day|gtc|opg|cls|ioc|fok),
  limit_price, stop_price, client_order_id (always sent; UUID4 generated when
  omitted for idempotency), order_class=bracket + take_profit{limit_price} /
  stop_loss{stop_price} for brackets. Bracket entry leg must be a limit order.
  notional is supported on market orders only.
- `DELETE /v2/orders/{order_id}` — cancel; returns 204.
- `DELETE /v2/positions/{symbol}?qty=N` — close full position, or partial with qty.
- `GET /v2/stocks/{symbol}/bars?timeframe=1H&limit=N` (data host) — fields per
  bar: t (RFC3339), o, h, l, c, v. `feed=iex` is used (free tier). `adjustment`
  defaults to raw.

## Error handling

- 429 → exponential backoff (1s, 2s, 4s; 4 attempts total in `alpaca_lib.py`).
- Other 4xx/5xx → stderr message with the provider's error body, exit 1.
- Missing `ALPACA_KEY_ID`/`ALPACA_API_SECRET_KEY` → stderr, exit 1 (fail closed).
- Bad `ALPACA_ENV` → stderr, exit 1.
- Live order without `--i-understand-this-is-live` → stderr, exit 3.

## Notes

- Paper accounts reset independently of live accounts; keys are per-account.
- Day-trade count matters even in paper: `daytrade_count >= 3` in 5 days flags
  pattern-day-trader restrictions on small accounts.
- 1H bars are newest-last in the array; the CLI preserves API order.
