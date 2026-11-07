#!/usr/bin/env python3
"""Discipline 12: every fact is timeless, dated, or a pointer.

The illegal form is a present-tense claim about a fast fact with no date
outside a dated container. Aged lines get exactly one disposition:
re-observe, convert to a pointer, or retire into a dated note.

Standard library only.
"""
import re
from datetime import date

VOLATILE = re.compile(r"\b(count|counts|balance|balances|status|roster|positions?|"
                      r"equity|cash|files|rows|entries|defects?|open items?)\b", re.I)
NUMBER = re.compile(r"(\$\s?\d|\b\d[\d,]*(?:\.\d+)?\b)")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
DEFAULT_WINDOW_DAYS = 7
DISPOSITIONS = ("re-observe", "convert-to-pointer", "retire")


def validate_fact(fact):
    kind = fact.get("kind")
    errors = []
    if kind not in ("timeless", "dated", "pointer"):
        return ["kind must be timeless, dated, or pointer"]
    if kind == "dated" and not fact.get("as_of"):
        errors.append("dated fact needs as_of")
    if kind == "pointer":
        if not fact.get("target"):
            errors.append("pointer must name where the truth lives")
        if fact.get("last_observed") is None:
            errors.append("pointer needs a last-observed value")
        if not fact.get("as_of"):
            errors.append("pointer needs an as-of date for its last-observed value")
    if kind == "timeless" and fact.get("as_of"):
        errors.append("timeless fact should not carry a decaying stamp")
    if fact.get("as_of"):
        try:
            date.fromisoformat(fact["as_of"])
        except (TypeError, ValueError):
            errors.append("as_of must be a valid ISO calendar date")
    return errors


def lint_text(text, reference_date=None, window_days=DEFAULT_WINDOW_DAYS):
    reference = date.fromisoformat(reference_date) if reference_date else date.today()
    if isinstance(window_days, bool) or not isinstance(window_days, int) or window_days < 0:
        raise ValueError("window_days must be a nonnegative integer")
    findings = []
    containers = []
    in_dated_container = False
    for number, line in enumerate(text.splitlines(), 1):
        heading = re.match(r"^(#{1,6})\s", line)
        if heading:
            level = len(heading.group(1))
            containers = [(depth, dated) for depth, dated in containers if depth < level]
            containers.append((level, bool(DATE_RE.search(line))))
            in_dated_container = any(dated for _, dated in containers)
        stamp = DATE_RE.search(line)
        if NUMBER.search(line) and VOLATILE.search(line):
            if not stamp and "as of" not in line.lower() and not in_dated_container:
                findings.append({"code": "FRESH-1", "line": number,
                                 "message": "unstamped quantitative present-tense claim about a volatile noun"})
            elif stamp:
                try:
                    age = (reference - date.fromisoformat(stamp.group(1))).days
                except ValueError:
                    findings.append({"code": "FRESH-4", "line": number, "message": "invalid calendar date"})
                    continue
                if age > window_days:
                    findings.append({"code": "FRESH-2", "line": number, "age_days": age,
                                     "message": "stamp older than the freshness window",
                                     "allowed_dispositions": list(DISPOSITIONS)})
        if "proof:" in line.lower() and "MISSING" in line:
            findings.append({"code": "FRESH-3", "line": number, "message": "pointer does not resolve"})
    return findings


def aged_disposition(line):
    matches = re.findall(r"freshness-action:\s*(re-observe|convert-to-pointer|retire)\b", line)
    if len(matches) != 1:
        raise ValueError("an aged line needs exactly one disposition: re-observe, convert-to-pointer, or retire")
    return matches[0]


def refresh_on_read(fact, still_true, on_date, contract_declared=False):
    """Refresh a stamp only where the store contract declares refresh-on-read."""
    date.fromisoformat(on_date)
    result = dict(fact)
    if contract_declared and still_true and fact.get("kind") in ("dated", "pointer"):
        result["as_of"] = on_date
        result["refreshed_on_read"] = True
    return result


if __name__ == "__main__":
    print(__doc__)
