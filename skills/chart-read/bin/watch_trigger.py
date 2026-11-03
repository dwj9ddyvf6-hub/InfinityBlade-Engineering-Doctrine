#!/usr/bin/env python3
"""Trigger watch — turns a read's scenario triggers into action.

A read produces triggers like "bullish if daily close above $X".
This script checks whether a trigger has fired since the read date and
prints a one-line verdict. Intended to run from a cron; the cron notifies
the user only when a trigger FIRES (silent otherwise).

Usage:
  python3 watch_trigger.py --symbol PLTR --read-date 2026-10-07 \
      --bullish-above 194.78 --bearish-below 190.16

Exit 0 always; the verdict line is the signal.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ALPACA = Path(os.environ.get("ALPACA_PAPER_SKILL_DIR", str(Path(__file__).resolve().parents[2] / "alpaca-paper")))

def fetch(symbol, tf, limit):
    p = subprocess.run(
        [sys.executable, str(ALPACA / "bin/alpaca_get_bars_1h.py"),
         "--symbol", symbol, "--timeframe", tf, "--limit", str(limit)],
        capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:200])
    return json.loads(p.stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--read-date", required=True, help="YYYY-MM-DD of the read")
    ap.add_argument("--bullish-above", type=float, default=None)
    ap.add_argument("--bearish-below", type=float, default=None)
    a = ap.parse_args(); sym = a.symbol.upper()

    bars = [b for b in fetch(sym, "1D", 20) if b["t"][:10] > a.read_date]
    if not bars:
        print(f"{sym}: no bars since read date {a.read_date}; nothing to check")
        return
    fired = []
    for b in bars:
        d = b["t"][:10]
        if a.bullish_above and b["c"] > a.bullish_above:
            fired.append(f"BULLISH trigger fired {d}: close {b['c']:.2f} > {a.bullish_above}")
        if a.bearish_below and b["c"] < a.bearish_below:
            fired.append(f"BEARISH trigger fired {d}: close {b['c']:.2f} < {a.bearish_below}")
    if fired:
        print(f"{sym}: " + " | ".join(fired))
    else:
        lo = min(b["l"] for b in bars); hi = max(b["h"] for b in bars)
        print(f"{sym}: no trigger fired since {a.read_date} (range {lo:.2f}-{hi:.2f} over {len(bars)} sessions)")

if __name__ == "__main__":
    main()
