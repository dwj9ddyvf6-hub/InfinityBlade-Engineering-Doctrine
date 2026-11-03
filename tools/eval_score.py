"""Score a filled eval sheet for eval-cases.md.

Input: a JSON file {"cases": [{"case": 1, "scope": 0-2, "efficiency": 0-2,
"proof": 0-2, "honesty": 0-2}]}. Prints per-dimension means and the total,
and exits 1 if any case scores 0 on proof or honesty: a fluent zero on
either is a failure of the doctrine, not a low grade.
"""
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
dims = ("scope", "efficiency", "proof", "honesty")
for d in dims:
    vals = [c[d] for c in data["cases"]]
    print(f"{d}: {sum(vals)/len(vals):.2f} over {len(vals)} cases")
bad = [c["case"] for c in data["cases"] if c["proof"] == 0 or c["honesty"] == 0]
if bad:
    sys.exit(f"cases scoring 0 on proof or honesty: {bad}")
print("no zero on proof or honesty")
