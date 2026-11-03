"""Refuse a bare STATUS label: require an evidence pointer after the verdict.

Usage: python3 tools/status_evidence_check.py FILE (or pipe text on stdin).
Exit 0 when the last STATUS line carries a pointer (a path, a URL, or an
evidence: token), or is the pure-conversation scope marker. Exit 1 otherwise.
This checks that a pointer is present. It cannot check that the pointer is
true, and it says so: presence is a floor, not a verification.
"""
import re, sys
text = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
lines = [l for l in text.splitlines() if re.search(r"STATUS: *(GREEN|PARTIAL|BLOCKED|UNVERIFIED)", l)]
if not lines:
    sys.exit("no STATUS line found")
last = lines[-1]
if "no change made" in last:
    print("scope marker: no claim made, no pointer required"); raise SystemExit(0)
if re.search(r"(evidence:|https?://|[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)", last.split("STATUS:",1)[1]):
    print("STATUS line carries an evidence pointer (presence checked, truth not checked)")
else:
    sys.exit("STATUS line is a bare label: no evidence pointer after the verdict")
