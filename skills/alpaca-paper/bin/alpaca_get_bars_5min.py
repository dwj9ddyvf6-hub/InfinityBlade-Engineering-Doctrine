#!/usr/bin/env python3
"""alpaca_get_bars_5min — fetch 5-minute stock bars as JSON.

Supports --feed selection (iex | sip | otc). An options sleeve
uses feed=sip for the extended-hours compression history (full 04:00-19:55
ET coverage historically; lags ~15-18 min behind real time — do not use it
for real-time decisions) and feed=iex for real-time RTH exit sweeps (IEX
prints IEX hours only). feed=delayed_sip is NOT valid on this endpoint.

NOTE: the data API returns no bars unless an explicit start is given, so when
--start is omitted one is derived from --limit with a generous lookback
(same as alpaca_get_bars_1h).
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alpaca_lib import api_request, data_base, emit, fail, quote_path


def default_start(limit):
    # Twice-daily bugcheck 2026-10-06: ported from alpaca_get_bars_1h.
    # ~78 RTH 5-min bars/day -> limit*25 minutes is a generous calendar
    # lookback that always covers the requested bar count.
    return (datetime.now(timezone.utc)
            - timedelta(minutes=limit * 25)).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch 5-min bars from Alpaca.")
    p.add_argument("--symbol", required=True, help="Ticker symbol, e.g. NVDA")
    p.add_argument("--limit", type=int, default=100,
                   help="Number of bars, 1-10000 (default: 100)")
    p.add_argument("--start", default=None,
                   help="RFC3339 start, e.g. 2026-09-25T00:00:00Z (optional)")
    p.add_argument("--end", default=None, help="RFC3339 end (optional)")
    p.add_argument("--feed", default="sip",
                   choices=["iex", "sip", "otc"],
                   help="Market data feed (default: sip). TRADING-PATH-"
                        "FEED-20261031: the book charter prices "
                        "fills from the next 5-minute SIP bar open, and "
                        "the volume law disqualifies non-SIP data "
                        "for volume signals, so sip is the default; "
                        "pass iex explicitly only for a real-time RTH "
                        "check that names why. sip is 403 for recent "
                        "data on some subscriptions but works "
                        "historically.")
    p.add_argument("--adjustment", default="raw",
                   choices=["raw", "split", "dividend", "all"],
                   help="Corporate-action adjustment (default: raw)")
    p.add_argument("--max-pages", type=int, default=10,
                   help="Max API pages to fetch per window (default: 10; "
                        "bounds the next_page_token pagination loop)")
    p.add_argument("--max-windows", type=int, default=8,
                   help="Max start-sliding windows when a window is "
                        "truncated by --max-pages (default: 8). Total "
                        "requests stay bounded at --max-pages * "
                        "--max-windows.")
    return p


def fetch_bars(symbol, params, max_pages, max_windows, end=None):
    """Fetch 5-min bars for one symbol, oldest first, deduped by timestamp.

    3x-daily bugcheck 2026-10-10 (MEDIUM): ported from
    alpaca_get_bars_1h.fetch_bars. The data API returns the *earliest*
    bars from `start` and paginates forward, so breaking the page loop on
    max_pages while a next_page_token remained silently yielded a STALE
    (old) window -- the later `[-limit:]` slice then kept old bars, not
    the newest (the 1h daily-resample path hit exactly this on 2026-10-10
    and phantom-alerted a month-old swing). A repeated/stale page_token
    also duplicated bars with no `seen` set, corrupting bar counts for the
    an options sleeve's compression/exit logic.

    Fix: when a window is truncated, slide `start` to the newest fetched
    bar and keep fetching. The per-window page cap (the 2026-10-09 hang
    guard) is preserved; the outer window loop is bounded by
    max_windows, and a no-progress window breaks the loop, so total
    requests stay bounded.
    """
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
        if not truncated or end is not None or windows >= max_windows:
            break
        if len(bars_all) == n_before or not bars_all:
            break  # no progress -- do not spin on a stuck token
        # Slide the window forward: resume from the newest bar fetched.
        params["start"] = bars_all[-1].get("t")
    bars_all.sort(key=lambda b: b.get("t") or "")
    return bars_all


def main() -> None:
    args = build_parser().parse_args()
    if not 1 <= args.limit <= 10000:
        fail("--limit must be between 1 and 10000")
    params = {
        "timeframe": "5Min",
        "limit": "10000",
        "adjustment": args.adjustment,
        "feed": args.feed,
    }
    if args.start:
        params["start"] = args.start
    else:
        params["start"] = default_start(args.limit)
    if args.end:
        params["end"] = args.end

    bars_all = fetch_bars(args.symbol.upper(), params,
                          args.max_pages, args.max_windows, end=args.end)
    bars = bars_all[-args.limit:] if args.limit < len(bars_all) else bars_all
    # TRADING-PATH-FEED-20261031: record the feed used on stderr on
    # every call (stdout stays the bare bars list its consumers
    # parse), and fail closed on an empty result: before this cure
    # a default invocation outside IEX hours returned an empty
    # JSON list with exit 0 and no label, indistinguishable from a
    # genuine no-data window.
    print(f"feed={args.feed} symbol={args.symbol.upper()} "
          f"bars={len(bars)}", file=sys.stderr)
    if not bars:
        fail(f"no 5-minute bars returned for {args.symbol.upper()} "
             f"on feed={args.feed} in the requested window; refusing "
             f"to report an empty result as data (exit 3)",
             exit_code=3)
    emit([{"t": b.get("t"), "o": b.get("o"), "h": b.get("h"),
           "l": b.get("l"), "c": b.get("c"), "v": b.get("v")}
          # 3x-daily bugcheck 2026-10-09 (LOW): a malformed bar entry
          # (null/string) raised AttributeError on b.get -- skip non-dict
          # rows instead (same class already fixed in option_chain).
          for b in bars if isinstance(b, dict)])


if __name__ == "__main__":
    main()
