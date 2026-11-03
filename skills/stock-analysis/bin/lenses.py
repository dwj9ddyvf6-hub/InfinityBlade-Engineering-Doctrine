import os
#!/usr/bin/env python3
"""lenses.py — strategy lenses for unified stock analysis.

For each strategy sleeve, reports the strategy's OWN verdict on a symbol by
reading its ledger and universe. NEVER reimplements sleeve rules — extreme
rigor means reading the strategy's state, not vibing it.

Edge statuses come from your project's strategic audit:
  VALIDATED    sealed holdout / edge-lab grade
  WATCH        edge partial, eroded, or trails a naive alternative
  CONTESTED    validation disputed by a clean rerun (unresolved)
  EXPERIMENTAL live paper, no sealed validation cited
  CORE         project flagship (1H swing strategy, hash-pinned)
Strategies that FAILED your project's validation are EXCLUDED: list
them in EXCLUDED below in your own copy. They never appear as lenses.

Usage: python3 lenses.py --symbol PLTR
Output: JSON.
"""
import argparse, json
from pathlib import Path

DESK = Path(os.environ.get("STOCK_ANALYSIS_PROJECT_DIR", "."))

def basket_universe():
    # A basket file whose "symbols" entry is a list of dicts
    # ({"symbol": "AAA", ...}), not plain strings: set(b["symbols"])
    # raises TypeError on the unhashable dicts, a bare except swallows
    # it, and the lens then reports EVERY symbol as "not in basket".
    # Parse each entry defensively, as below.
    try:
        b = json.loads((DESK / "basket.json").read_text())
        out = set()
        for e in b["symbols"]:
            s = e.get("symbol") if isinstance(e, dict) else e
            if s:
                out.add(str(s).upper())
        return out
    except Exception:
        return set()

def file_list_universe():
    try:
        return {l.strip().upper() for l in
                (DESK / "example_universe.txt").read_text().splitlines()
                if l.strip() and not l.startswith("#")}
    except Exception:
        return set()

# Example roster. Replace every entry with your own strategies: the
# key, the ledger file that strategy writes, its edge class from your
# project's audit, a one-line note carrying that audit's verdict, and
# its universe gate if it has one. The entries below are placeholders
# that demonstrate the schema; they name no real strategy.
SLEEVES = [
    {"key": "example_core", "ledger": "example_core_ledger.jsonl", "edge": "CORE",
     "edge_note": "Example: your flagship strategy, with its audit verdict",
     "universe": ("example basket", lambda s, u: s in u),
     "universe_data": basket_universe},
    {"key": "example_validated", "ledger": "example_validated_ledger.jsonl", "edge": "VALIDATED",
     "edge_note": "Example: a strategy that passed your sealed holdout, with its grade",
     "universe": None, "universe_data": None},
    {"key": "example_experimental", "ledger": "example_experimental_ledger.jsonl", "edge": "EXPERIMENTAL",
     "edge_note": "Example: a live paper strategy with no sealed validation yet",
     "universe": ("example universe list", lambda s, u: s in u),
     "universe_data": file_list_universe},
]

EXCLUDED = ("none shipped: list your own failed-validation strategies "
            "here in your copy; they never appear as lenses")

KEY_FIELDS = ("ts", "episode", "decision", "event", "confidence", "phenotype",
              "action", "signal", "side", "reason", "note")

def latest_signal(ledger_path, symbol):
    """Latest ledger entry for the symbol (by ts), trimmed to key fields."""
    best, best_ts = None, ""
    try:
        with open(ledger_path) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if str(e.get("symbol", "")).upper() != symbol:
                    continue
                ts = str(e.get("ts", ""))
                if ts >= best_ts:
                    best, best_ts = e, ts
    except FileNotFoundError:
        return None
    if not best:
        return None
    return {k: best.get(k) for k in KEY_FIELDS if best.get(k) is not None}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--symbol", required=True)
    sym = ap.parse_args().symbol.upper()
    lenses = []
    for s in SLEEVES:
        lens = {"sleeve": s["key"], "edge": s["edge"], "edge_note": s["edge_note"]}
        # applicability
        if s["universe"]:
            name, check = s["universe"]
            uni = s["universe_data"]()
            ok = check(sym, uni)
            lens["applies"] = ok
            lens["applicability"] = (f"in {name}" if ok
                                     else f"not in {name} — lens does not apply")
            if not ok:
                lenses.append(lens); continue
        else:
            lens["applies"] = True
            lens["applicability"] = "no universe gate"
        sig = latest_signal(DESK / s["ledger"], sym)
        lens["signal"] = sig if sig else "no signal on record"
        lenses.append(lens)
    print(json.dumps({"symbol": sym, "excluded_sleeves": EXCLUDED,
                      "lenses": lenses}, indent=1))

if __name__ == "__main__":
    main()
