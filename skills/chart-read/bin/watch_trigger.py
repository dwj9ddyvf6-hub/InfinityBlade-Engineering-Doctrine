#!/usr/bin/env python3
"""Trigger watch — turns a read's scenario triggers into action.

A read produces triggers like "bullish if daily close above $X".
This script checks whether a trigger has fired since the read date and
prints a one-line verdict. Intended to run from a cron; the cron notifies
the user only when a trigger FIRES (silent otherwise).

Usage:
  python3 watch_trigger.py --symbol PLTR --read-date 2026-10-07 \
      --bullish-above 194.78 --bearish-below 190.16

Exit 0 means a completed check; failures exit 2. Default stdout is silent when
no trigger fires. This is a stateless evaluator; a notifier owns event
deduplication, acknowledgement and any schedule. --json supplies event records.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ALPACA = Path(os.environ.get("ALPACA_PAPER_SKILL_DIR", str(Path(__file__).resolve().parents[2] / "alpaca-paper")))

def fetch(symbol, tf, limit, start=None):
    command = [sys.executable, str(ALPACA / "bin/alpaca_get_bars_1h.py"),
               "--symbol", symbol, "--timeframe", tf, "--limit", str(limit)]
    if start:
        command.extend(["--start", start])
    p = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:200])
    return json.loads(p.stdout)


def evaluate_triggers(bars, read_date, bullish_above=None, bearish_below=None, now=None):
    """Evaluate only subsequent completed daily bars; no scheduling or orders.

    Completion uses the protocol's conservative regular-session 16:05 ET rule.
    Exchange holiday/early-close calendars are not inferred from OHLCV.
    """
    from datetime import date, datetime, timezone
    from zoneinfo import ZoneInfo
    import math
    first = date.fromisoformat(read_date)
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("now must carry a timezone")
    clock = clock.astimezone(ZoneInfo("America/New_York"))
    if first > clock.date():
        raise ValueError("read-date is in the future")
    thresholds = (bullish_above, bearish_below)
    if all(value is None for value in thresholds):
        raise ValueError("at least one trigger threshold is required")
    if any(value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0) for value in thresholds):
        raise ValueError("trigger thresholds must be finite positive prices")
    if not isinstance(bars, list):
        raise ValueError("bars must be an array")
    events, evaluated, provisional = [], 0, 0
    seen = {}
    for bar in bars:
        if not isinstance(bar, dict) or not isinstance(bar.get("t"), str):
            raise ValueError("invalid daily bar")
        stamp = datetime.fromisoformat(bar["t"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("daily bar timestamp needs an offset")
        day = stamp.astimezone(ZoneInfo("America/New_York")).date()
        close = bar.get("c")
        if isinstance(close, bool) or not isinstance(close, (int, float)) or not math.isfinite(close) or close <= 0:
            raise ValueError("invalid daily close")
        if day in seen:
            if seen[day] != close:
                raise ValueError("conflicting daily closes for one session")
            continue
        seen[day] = close
        if day <= first:
            continue
        if day > clock.date():
            raise ValueError("daily bar is in the future")
        if day == clock.date() and clock.strftime("%H:%M") < "16:05":
            provisional += 1
            continue
        evaluated += 1
        for direction, threshold, fired in (("BULLISH", bullish_above, bullish_above is not None and close > bullish_above),
                                             ("BEARISH", bearish_below, bearish_below is not None and close < bearish_below)):
            if fired:
                events.append({"direction": direction, "session": day.isoformat(), "close": close, "threshold": threshold})
    events.sort(key=lambda row: (row["session"], row["direction"]))
    return {"events": events, "completed_bars_evaluated": evaluated,
            "provisional_bars_excluded": provisional, "read_date": read_date,
            "completion_policy": "regular-session16:05America/New_York; no holiday/early-close calendar",
            "delivery_verified": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--read-date", required=True, help="YYYY-MM-DD of the read")
    ap.add_argument("--bullish-above", type=float, default=None)
    ap.add_argument("--bearish-below", type=float, default=None)
    ap.add_argument("--show-status", action="store_true", help="Print a non-trigger status; default cron output is silent")
    ap.add_argument("--json", action="store_true", help="Return event and completion evidence for an external notifier")
    a = ap.parse_args()
    sym = a.symbol.strip().upper()
    # Validate dates/thresholds before any data subprocess is allowed.
    evaluate_triggers([], a.read_date, a.bullish_above, a.bearish_below)
    if not sym:
        raise ValueError("symbol must be nonempty")
    bars = fetch(sym, "1D", 10000, start=a.read_date + "T00:00:00Z")
    result = evaluate_triggers(bars, a.read_date, a.bullish_above, a.bearish_below)
    if len(bars) >= 10000:
        raise ValueError("watch window reached the 10000-bar cap; narrow read-date or verify coverage separately")
    if a.json:
        print(json.dumps({"symbol": sym, **result}, allow_nan=False))
    elif result["events"]:
        print(f"{sym}: " + " | ".join(f"{e['direction']} trigger fired {e['session']}: close {e['close']:.2f} {'>' if e['direction'] == 'BULLISH' else '<'} {e['threshold']}" for e in result["events"]))
    elif a.show_status:
        print(f"{sym}: no trigger in {result['completed_bars_evaluated']} completed subsequent sessions")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Trigger check failed: {error}", file=sys.stderr)
        raise SystemExit(2)
