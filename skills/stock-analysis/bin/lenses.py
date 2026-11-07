#!/usr/bin/env python3
import os
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
from datetime import datetime, timezone
from pathlib import Path

DESK = Path(os.environ.get("STOCK_ANALYSIS_PROJECT_DIR", "."))

def basket_universe():
    # A basket file whose "symbols" entry is a list of dicts
    # ({"symbol": "AAA", ...}), not plain strings: set(b["symbols"])
    # raises TypeError on the unhashable dicts, a bare except swallows
    # it, and the lens then reports EVERY symbol as "not in basket".
    # Parse each entry defensively, as below.
    b = json.loads((DESK / "basket.json").read_text(encoding="utf-8"))
    if not isinstance(b, dict) or not isinstance(b.get("symbols"), list):
        raise ValueError("basket must contain a symbols list")
    out = set()
    for entry in b["symbols"]:
        symbol = entry.get("symbol") if isinstance(entry, dict) else entry
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("basket contains an invalid symbol")
        out.add(symbol.strip().upper())
    return out


def file_list_universe():
    return {line.strip().upper() for line in
            (DESK / "example_universe.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")}

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
    best, best_ts = None, None
    with open(ledger_path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError(f"ledger line {number} is not an object")
            if str(entry.get("symbol", "")).upper() != symbol.upper():
                continue
            stamp = datetime.fromisoformat(str(entry.get("ts", "")).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError(f"ledger line {number} timestamp needs a timezone")
            stamp = stamp.astimezone(timezone.utc)
            if best_ts is None or stamp >= best_ts:
                best, best_ts = entry, stamp
    return None if best is None else {k: best[k] for k in KEY_FIELDS if best.get(k) is not None}

def main():
    global DESK
    ap = argparse.ArgumentParser(); ap.add_argument("--symbol", required=True)
    ap.add_argument("--project-dir", type=Path, default=DESK)
    args = ap.parse_args()
    DESK, sym = args.project_dir, args.symbol.upper()
    lenses = []
    for s in SLEEVES:
        if isinstance(EXCLUDED, (list, tuple, set)) and s["key"] in EXCLUDED:
            continue
        lens = {"sleeve": s["key"], "edge": s["edge"], "edge_note": s["edge_note"]}
        # applicability
        if s["universe"]:
            name, check = s["universe"]
            try:
                uni = s["universe_data"]()
                ok = check(sym, uni)
            except (OSError, ValueError, TypeError) as exc:
                lens.update(applies=None, applicability="unknown: universe unavailable or invalid",
                            source_status="unavailable" if isinstance(exc, FileNotFoundError) else "invalid",
                            error_type=type(exc).__name__)
                lenses.append(lens)
                continue
            lens["applies"] = ok
            lens["applicability"] = (f"in {name}" if ok
                                     else f"not in {name} — lens does not apply")
            if not ok:
                lenses.append(lens); continue
        else:
            lens["applies"] = True
            lens["applicability"] = "no universe gate"
        try:
            sig = latest_signal(DESK / s["ledger"], sym)
            lens["signal"] = sig if sig else "no signal on record"
            lens["source_status"] = "read_complete"
        except (OSError, ValueError, TypeError) as exc:
            lens.update(signal=None, source_status="unavailable" if isinstance(exc, FileNotFoundError) else "invalid",
                        error_type=type(exc).__name__)
        lenses.append(lens)
    print(json.dumps({"symbol": sym, "example_only": all(s["key"].startswith("example_") for s in SLEEVES),
                      "excluded_sleeves": EXCLUDED,
                      "lenses": lenses}, indent=1))

if __name__ == "__main__":
    main()
