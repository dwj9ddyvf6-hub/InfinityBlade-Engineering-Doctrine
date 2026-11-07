"""Score a proactive timeline with an explicitly chosen interruption price.

Benefit: MUST=4, MAY=2 once per window. Cost: every fire=1, plus 4 for each
MUST-NOT fire. The canonical implementation also powers the host lane.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/agent-enhancement-systems/bin"))
from proactive import DEFAULT_LAMBDAS, score_timeline


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline")
    parser.add_argument("--lambda", dest="lam", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        windows = json.loads(Path(args.timeline).read_text(encoding="utf-8"))["windows"]
        result = score_timeline(windows, lambdas=(*DEFAULT_LAMBDAS, args.lam))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))
    for lam in DEFAULT_LAMBDAS:
        print(f"lambda={lam}: benefit={result['benefit']} cost={result['cost']} net={result['nets'][str(lam)]}")
    print(f"verdict at lambda={args.lam}: {result['verdict_at'](args.lam)} (net {result['nets'][str(args.lam)]})")


if __name__ == "__main__":
    main()
