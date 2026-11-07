#!/usr/bin/env python3
"""alpaca_get_bars_1h — print compact bars for a symbol as JSON.

Hits the market-data host (https://data.alpaca.markets), not the trading API.
--timeframe selects 1H (default), 1D, or 1W bars.
Output: [{"t","o","h","l","c","v"}, ...] newest last, exactly as the API returns.

NOTE: the data API returns no bars unless an explicit start is given, so when
--start is omitted one is derived from --limit and --timeframe with a generous
lookback (market-hour bars need more calendar time than their bar count).
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import AlpacaError, api_request, data_base, emit, fail, quote_path


def default_start(timeframe, limit):
    now = datetime.now(timezone.utc)
    if timeframe == "10Min":
        return now - timedelta(days=max(14, limit // 30))  # ~6.5h/day of 10m bars
    if timeframe == "1H":
        return now - timedelta(hours=limit * 5)   # ~5x: skips nights/weekends
    if timeframe == "1D":
        return now - timedelta(days=limit * 2)
    if timeframe == "1W":
        return now - timedelta(weeks=limit * 2)
    raise ValueError(timeframe)


def fetch_bars(symbol, timeframe, params, max_pages, max_windows, end=None):
    """Fetch bars for one symbol, oldest first, deduped by timestamp.

    The data API returns the *earliest* bars from `start` and paginates
    forward, so breaking the page loop on max_pages while a
    next_page_token remains would silently yield a STALE (old) window --
    the later `[-limit:]` slice then keeps old bars, not the newest.
    (2026-10-10: this truncated the daily-resample path to 2026-09-14
    for dense-history symbols and phantom-alerted a month-old swing.)

    Fix: when a window is truncated, slide `start` to the newest fetched
    bar and keep fetching. The per-window page cap (the 2026-10-09 hang
    guard) is preserved; the outer window loop is bounded by
    max_windows, and a no-progress window breaks the loop, so total
    requests stay bounded.
    """
    if max_pages < 1 or max_windows < 1:
        raise ValueError("max_pages and max_windows must be positive")
    params = dict(params)
    bars_all = []
    seen = set()
    windows = 0
    while True:
        windows += 1
        n_before = len(bars_all)
        page_token = None
        pages = 0
        truncated = False
        # 3x-daily bugcheck 2026-10-09 (MEDIUM): bound the
        # next_page_token pagination -- a pathological token loop
        # used to hang the runner forever. Mirrors
        # alpaca_option_chain.py --max-pages.
        while True:
            pages += 1
            if page_token:
                params["page_token"] = page_token
            else:
                params.pop("page_token", None)
            data = api_request(
                "GET", f"{data_base()}/v2/stocks/{quote_path(symbol.upper())}/bars",
                params=params,
            )
            if isinstance(data, dict) and "raw" in data:
                fail("Unexpected bars response shape (non-JSON body)", exit_code=2)
            # 3x-daily bugcheck 2026-10-14 PM (LOW, BC14P-11): a non-dict body, a dict with NO
            # "bars" key, or a non-list bars value silently degraded
            # to an empty result (callers read "no bars" for a data-
            # layer failure). Alpaca's documented {"bars": null} (no
            # data for the window) stays a legitimate empty result.
            if not isinstance(data, dict) or "bars" not in data:
                fail("Unexpected bars response shape (no bars key)",
                     exit_code=2)
            if data.get("bars") is not None and \
                    not isinstance(data.get("bars"), list):
                fail("Unexpected bars response shape (bars not a list)",
                     exit_code=2)
            raw = data.get("bars")
            if isinstance(raw, list):
                for b in raw:
                    t = b.get("t") if isinstance(b, dict) else None
                    if t is not None and t not in seen:
                        seen.add(t)
                        bars_all.append(b)
            page_token = data.get("next_page_token") if isinstance(data, dict) else None
            if not page_token or pages >= max_pages:
                truncated = bool(page_token)
                break
        if not truncated:
            break
        if windows >= max_windows:
            raise AlpacaError("Bar coverage incomplete: pagination budget exhausted with a continuation token; increase explicit limits")
        if len(bars_all) == n_before or not bars_all:
            raise AlpacaError("Bar coverage incomplete: pagination made no progress")
        # Slide the window forward: resume from the newest bar fetched.
        params["start"] = max(b["t"] for b in bars_all)
    bars_all.sort(key=lambda b: b.get("t") or "")
    return bars_all


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch bars from Alpaca market data.")
    p.add_argument("--symbol", required=True, help="Ticker symbol, e.g. AAPL")
    p.add_argument("--timeframe", default="1H", choices=["1H", "1D", "1W", "10Min"],
                   help="Bar timeframe: 1H (default), 1D, 1W, or 10Min")
    p.add_argument("--limit", type=int, default=10,
                   help="Number of bars, 1-10000 (default: 10)")
    p.add_argument("--start", default=None,
                   help="RFC3339 start, e.g. 2026-09-01T00:00:00Z (optional)")
    p.add_argument("--end", default=None,
                   help="RFC3339 end (optional)")
    p.add_argument("--adjustment", default="raw",
                   choices=["raw", "split", "dividend", "all"],
                   help="Corporate-action adjustment (default: raw)")
    p.add_argument("--max-pages", type=int, default=10,
                   help="Max API pages to fetch per window (default: 10; bounds the "
                        "next_page_token pagination loop)")
    p.add_argument("--max-windows", type=int, default=8,
                   help="Max start-sliding windows when a window is truncated "
                        "by --max-pages (default: 8). Total requests stay "
                        "bounded at --max-pages * --max-windows.")
    p.add_argument("--feed", default="sip",
                   choices=["iex", "sip", "otc"],
                   help="Market data feed (default: sip). TRADING-PATH-"
                        "FEED1H-20261031: the volume law requires "
                        "SIP for hourly-or-finer volume work and the "
                        "benchmark closes of record are SIP daily bars, "
                        "so sip is the default, matching the cured "
                        "5-minute script; pass iex explicitly only for "
                        "a real-time RTH check that names why. sip is "
                        "403 for recent data on some subscriptions but "
                        "works historically.")
    args = p.parse_args()
    if not 1 <= args.limit <= 10000:
        fail("--limit must be between 1 and 10000")

    params = {
        "timeframe": args.timeframe,
        "limit": "10000",  # page size; we slice the newest args.limit below
        "adjustment": args.adjustment,
        "feed": args.feed,
    }
    if args.start:
        params["start"] = args.start
    else:
        params["start"] = default_start(args.timeframe,
                                        args.limit).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.end:
        params["end"] = args.end

    bars_all = fetch_bars(args.symbol.upper(), args.timeframe, params,
                          args.max_pages, args.max_windows, end=args.end)
    bars = bars_all[-args.limit:] if args.limit < len(bars_all) else bars_all
    # TRADING-PATH-FEED1H-20261031: same stderr feed line and
    # fail-closed empty behaviour as the cured 5-minute script.
    # Before this cure a default invocation used iex (a fraction
    # of consolidated volume, different closes) and an empty
    # result printed as a bare empty list with exit 0.
    print(f"feed={args.feed} symbol={args.symbol.upper()} "
          f"bars={len(bars)}", file=sys.stderr)
    if not bars:
        fail(f"no bars returned for {args.symbol.upper()} "
             f"on feed={args.feed} in the requested window; refusing "
             f"to report an empty result as data (exit 3)",
             exit_code=3)
    emit(
        [
            {
                "t": b.get("t"),
                "o": b.get("o"),
                "h": b.get("h"),
                "l": b.get("l"),
                "c": b.get("c"),
                "v": b.get("v"),
            }
            # 3x-daily bugcheck 2026-10-09 (LOW): a malformed
            # bar entry (null/string) raised AttributeError on
            # b.get -- skip non-dict rows instead.
            for b in bars if isinstance(b, dict)
        ]
    )


if __name__ == "__main__":
    main()
