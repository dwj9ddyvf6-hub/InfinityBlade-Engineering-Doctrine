#!/usr/bin/env python3
"""Discipline 2: confidence-scored procedural memory ("instincts").

An instinct is an atomic trigger-to-action unit. Confidence is earned by
observation count, promotion is human-gated, contradicted units are frozen,
and session injection is capped and budgeted. External units land only as
pending, inherited-only records after import hardening.

Standard library only.
"""
import ipaddress
import json
import math
import re
import sys, os
from datetime import date
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from operations import redact, deterministic_id
from _storage import bounded_blocks

MIN_CONFIDENCE = 0.7
MIN_SUCCESS_RATE = 0.6
MAX_INJECT = 6
MAX_PER_TYPE = 3
SUMMARY_CHARS = 220
BUDGET_CHARS = 8000
PROJECT_BOOST = 0.25
STACK_BOOST = 0.20
NEAR_DUP_JACCARD = 0.80
PENDING_TTL_DAYS = 30
MAX_IMPORT_BYTES = 65536
TOK = re.compile(r"[a-z0-9]+")


def confidence_for_count(count, strong_source=False):
    if strong_source:
        return 0.9
    if count >= 11:
        return 0.85
    if count >= 6:
        return 0.7
    if count >= 3:
        return 0.5
    return 0.0


def validate_instinct(unit):
    if not isinstance(unit, dict):
        return ["instinct must be an object"]
    errors = []
    for field in ("id", "trigger", "action", "domain", "evidence", "summary"):
        if not unit.get(field):
            errors.append(f"{field} missing")
    confidence = unit.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 0.9:
        errors.append("confidence must be between 0 and 0.9")
    success = unit.get("success_rate", 0)
    if isinstance(success, bool) or not isinstance(success, (int, float)) or not math.isfinite(success) or not 0 <= success <= 1:
        errors.append("success_rate must be finite and between zero and one")
    if unit.get("scope") not in ("project", "global"):
        errors.append("scope must be project or global")
    if unit.get("status") not in ("active", "pending", "frozen"):
        errors.append("status must be active, pending, or frozen")
    return errors


def promotion_decision(unit):
    contexts = unit.get("contexts") or []
    eligible = len(set(contexts)) >= 2 and unit.get("confidence", 0) >= 0.8
    return {"eligible": eligible, "scope": "global" if eligible else unit.get("scope", "project"),
            "human_gate_required": True,
            "reason": "two or more contexts and average confidence at least 0.8" if eligible
                      else "promotion floor not met"}


def capture_event(event, observer="observer", max_chars=1000):
    """Capture one observation safely: no self-observation, redacted, truncated."""
    if event.get("actor") == observer:
        raise ValueError("anti-self-observation: the observer must not observe itself")
    clean = redact(dict(event))
    for key, value in list(clean.items()):
        if isinstance(value, str) and len(value) > max_chars:
            clean[key] = value[:max_chars] + "[TRUNCATED]"
    clean["capture"] = {"observer": observer, "redacted": True, "max_chars": max_chars}
    return clean


def extract_candidates(events):
    """Distil repeated trigger/action observations into pending instincts.

    This is the deterministic submission layer. A host may replace the
    grouping with a model observer pass, but the output must land in this
    shape and remain pending until the confidence and review rules admit it.
    A new submission for the same trigger/action replaces the prior pending
    candidate in the returned set.
    """
    groups, seen_ids = {}, set()
    for event in events:
        if event.get("id") in seen_ids:
            continue
        if event.get("id"):
            seen_ids.add(event["id"])
        trigger, action = event.get("trigger"), event.get("action")
        if not trigger or not action:
            continue
        key = (trigger, action, event.get("domain", "general"))
        group = groups.setdefault(key, {"observations": 0, "evidence": [], "contexts": set()})
        group["observations"] += 1
        if event.get("id"):
            group["evidence"].append(event["id"])
        if event.get("context"):
            group["contexts"].add(event["context"])
    candidates = []
    for (trigger, action, domain), group in groups.items():
        count = group["observations"]
        candidates.append({
            "id": "candidate-" + deterministic_id([trigger, action, domain])[:16], "trigger": trigger, "action": action,
            "domain": domain, "confidence": confidence_for_count(count), "observations": count,
            "contexts": sorted(group["contexts"]), "evidence": group["evidence"],
            "scope": "project", "status": "pending", "success_rate": 0.0,
            "contradicted": False, "summary": f"When {trigger}, {action}.",
            "created_on": None,
        })
    return candidates


def _is_private_or_local_host(host):
    if not host or host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.endswith(".local")


def import_instinct(payload, source_url, now=None):
    """Harden an external instinct before it can land as pending."""
    if len(payload) > MAX_IMPORT_BYTES:
        raise ValueError("import exceeds the size cap")
    now = date.today().isoformat() if now is None else now
    date.fromisoformat(now)
    parsed = urlparse(source_url)
    if parsed.scheme not in ("https", "http") or _is_private_or_local_host(parsed.hostname):
        raise ValueError("import source fails the URL syntax screen (DNS and redirects are not checked)")
    unit = json.loads(payload.decode("utf-8"))
    if any(str(unit.get(f, "")).startswith(("/", "~")) for f in ("id", "trigger", "action")):
        raise ValueError("system-path shaped content is blocked")
    errors = validate_instinct({**unit, "scope": unit.get("scope", "project"),
                                "status": unit.get("status", "pending")})
    if errors:
        raise ValueError(f"invalid imported instinct: {errors}")
    unit = dict(unit)
    unit.update(status="pending", landing="inherited-only", imported_on=now)
    return unit


def _tokens(text):
    return set(TOK.findall((text or "").lower()))


def _age_days(created_on, now):
    if not created_on or not now:
        return 0
    return (date.fromisoformat(now) - date.fromisoformat(created_on)).days


def build_injection(units, stack=None, now=None, budget_chars=BUDGET_CHARS):
    """Select the units a session may see, with every omission accountable."""
    rejected, admitted = [], []
    for original in units:
        unit = dict(original)
        errors = validate_instinct(unit)
        if errors:
            rejected.append({"id": unit.get("id"), "reason": "; ".join(errors)})
        elif unit.get("contradicted"):
            rejected.append({"id": unit["id"], "reason": "contradicted: frozen, excluded"})
        elif unit.get("status") == "pending" and _age_days(unit.get("created_on"), now) > PENDING_TTL_DAYS:
            rejected.append({"id": unit["id"], "reason": "pending unit expired after 30 days"})
        elif unit.get("status") != "active":
            rejected.append({"id": unit["id"], "reason": "not active: human review required before injection"})
        elif unit.get("confidence", 0) < MIN_CONFIDENCE:
            rejected.append({"id": unit["id"], "reason": f"confidence {unit.get('confidence')} < {MIN_CONFIDENCE}"})
        elif unit.get("success_rate", 0) < MIN_SUCCESS_RATE:
            rejected.append({"id": unit["id"], "reason": f"success_rate {unit.get('success_rate')} < {MIN_SUCCESS_RATE}"})
        else:
            admitted.append(unit)
    kept, merged = [], []
    for unit in sorted(admitted, key=lambda u: -u["confidence"]):
        toks = _tokens(unit["trigger"] + " " + unit["action"])
        duplicate = None
        for existing in kept:
            other = _tokens(existing["trigger"] + " " + existing["action"])
            if toks and other and len(toks & other) / len(toks | other) >= NEAR_DUP_JACCARD:
                duplicate = existing
                break
        if duplicate:
            merged.append(unit["id"])
        else:
            kept.append(unit)
    by_type = {}
    for unit in kept:
        by_type.setdefault(unit["domain"], []).append(unit)
    pool, type_capped = [], []
    for group in by_type.values():
        group.sort(key=lambda u: -u["confidence"])
        pool.extend(group[:MAX_PER_TYPE])
        type_capped.extend(u["id"] for u in group[MAX_PER_TYPE:])
    for unit in pool:
        unit["rank"] = unit["confidence"] + (PROJECT_BOOST if unit["scope"] == "project" else 0) \
            + (STACK_BOOST if stack and unit["domain"] == stack else 0)
    pool.sort(key=lambda u: -u["rank"])
    chosen = pool[:MAX_INJECT]
    result = bounded_blocks([(unit["id"], f"[{unit['id']}] {unit['summary'][:SUMMARY_CHARS]}")
                             for unit in chosen], budget_chars, total=len(units))
    omitted = result["omitted"] + [u["id"] for u in pool[MAX_INJECT:]] + type_capped + merged
    return {"text": result["text"], "injected": result["included"],
            "rejected": rejected, "merged": merged, "type_capped": type_capped,
            "omitted": omitted, "used_chars": result["used_chars"]}


def cluster_skill_candidates(units, min_units=1):
    """Propose mature clusters as skill drafts. A human gates promotion."""
    clusters = {}
    for unit in units:
        if unit.get("status") == "active" and unit.get("confidence", 0) >= MIN_CONFIDENCE and not unit.get("contradicted"):
            clusters.setdefault(unit["domain"], []).append(unit["id"])
    return [{"domain": domain, "units": ids, "status": "skill-draft-proposal",
             "human_gate_required": True}
            for domain, ids in sorted(clusters.items()) if len(ids) >= min_units]


if __name__ == "__main__":
    print(__doc__)
