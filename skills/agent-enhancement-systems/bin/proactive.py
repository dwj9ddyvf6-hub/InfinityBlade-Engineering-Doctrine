#!/usr/bin/env python3
"""Discipline 1: price and gate a proactive lane.

This module is deliberately host-neutral. A host lane calls score_timeline
before deployment, decide_lane inside its own send path, validate_assessment
for any model judgement that can start work, grade_delivery before delivery,
and LaneLedger for feedback and silence audits. A gate kept only in an
offline harness does not make the live lane gated; wire decide_lane into the
lane's serving path.

Standard library only.
"""
import json
import os
import re
import math
import time
from _storage import locked

BENEFIT = {"MUST": 4, "MAY": 2}
DEFAULT_LAMBDAS = (0.25, 0.5, 1, 2, 4)
LEAK_MARKERS = ("origin_event", "lane:", "lane_id", "tau=", "p_accept", "p_need",
                "would-accept", "would_accept", "fire_id", "dedup", "{", "}",
                "verdict", "C_FA", "C_FN")
NEXT_STEP_HINTS = ("next", "shall i", "want me to", "ready", "you can", "tap",
                   "reply", "scheduled", "booked", "confirmed", "due", "open")


def score_timeline(windows, lambdas=DEFAULT_LAMBDAS):
    """Score labelled windows. Benefit is once per window; cost is per fire."""
    if not windows:
        raise ValueError("timeline must contain observed windows")
    if any(isinstance(lam, bool) or not isinstance(lam, (int, float)) or not math.isfinite(lam) or lam < 0 for lam in lambdas):
        raise ValueError("interruption prices must be finite and nonnegative")
    benefit = 0
    cost = 0
    for window in windows:
        label = window.get("label")
        fires = window.get("fires", 0)
        if isinstance(fires, bool) or not isinstance(fires, int) or fires < 0:
            raise ValueError("fires must be a non-negative integer")
        if label not in ("MUST", "MAY", "MUST-NOT", "OTHER"):
            raise ValueError(f"unknown window label {label!r}")
        if fires:
            benefit += BENEFIT.get(label, 0)
            cost += fires + (4 * fires if label == "MUST-NOT" else 0)
    nets = {str(lam): benefit - lam * cost for lam in lambdas}

    def verdict_at(lam):
        return "DEPLOY" if benefit - lam * cost > 0 else "SILENCE"

    return {"benefit": benefit, "cost": cost, "nets": nets, "verdict_at": verdict_at}


def tau(c_fa, c_fn, p_need):
    """PRISM threshold: C_FA / (C_FA + p_need * C_FN). Fail closed."""
    for name, value in (("C_FA", c_fa), ("C_FN", c_fn), ("p_need", p_need)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"missing {name}: fail closed")
    if c_fa < 0 or c_fn < 0 or not 0.0 <= p_need <= 1.0:
        raise ValueError("cost or probability out of range: fail closed")
    scale = max(c_fa, c_fn)
    if scale == 0:
        return 1.0
    denominator = c_fa / scale + p_need * (c_fn / scale)
    return 1.0 if denominator == 0 else (c_fa / scale) / denominator


def check_rate(history, now, min_interval, max_fires_per_window, window_s=3600):
    for label, value in (("now", now), ("min_interval", min_interval), ("window_s", window_s)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{label} must be finite")
    if min_interval < 0 or window_s <= 0:
        raise ValueError("min_interval must be nonnegative and window_s positive")
    if isinstance(max_fires_per_window, bool) or not isinstance(max_fires_per_window, int) or max_fires_per_window < 0:
        raise ValueError("max_fires_per_window must be a nonnegative integer")
    history = list(history)
    if any(isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts) for ts in history):
        raise ValueError("history timestamps must be finite")
    recent = [ts for ts in history if now - ts < window_s]
    if recent and now - max(recent) < min_interval:
        return False
    return len(recent) < max_fires_per_window


def decide_lane(config, p_accept, p_need, now=None, history=()):
    """Return fire, slow, silent, would_accept, or blocked.

    Observe mode is the safe starting mode: a would-be fire is recorded as
    would_accept by the caller and is not sent. Promotion to auto is a human
    configuration change, represented by config['mode'] == 'auto'.
    """
    if isinstance(p_accept, bool) or not isinstance(p_accept, (int, float)) or not math.isfinite(p_accept) or not 0.0 <= p_accept <= 1.0:
        raise ValueError("p_accept missing or out of range: fail closed")
    threshold = tau(config.get("C_FA"), config.get("C_FN"), p_need)
    margin = config.get("margin", 0.0)
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not math.isfinite(margin) or margin < 0:
        raise ValueError("margin must be finite and nonnegative")
    if p_accept >= threshold:
        verdict = "fire"
    elif p_accept >= threshold - margin:
        verdict = "slow"
    else:
        verdict = "silent"
    if verdict == "fire":
        now = time.time() if now is None else now
        if not check_rate(history, now, config.get("min_interval"),
                          config.get("max_fires_per_window"), config.get("window_s", 3600)):
            verdict = "blocked"
    if verdict == "fire" and config.get("mode", "observe") != "auto":
        verdict = "would_accept"
    return {"lane": config.get("lane", "unnamed"), "tau": threshold,
            "verdict": verdict, "p_accept": p_accept, "p_need": p_need,
            "class": config.get("class", "horizontal")}


def validate_assessment(enabled_rule_ids, assessment, mode="observe"):
    """Host-validate a model assessment before any work starts.

    Every enabled rule must be judged exactly once; every judgement needs
    evidence; accept needs a matched rule and intent evidence. An inferred
    accept outside auto mode is downgraded to would_accept.
    """
    judged = assessment.get("rules_judged")
    if not isinstance(judged, list):
        raise ValueError("rules_judged must be a list")
    ids = [row.get("rule_id") for row in judged]
    if sorted(ids) != sorted(enabled_rule_ids) or len(ids) != len(set(ids)):
        raise ValueError("every enabled rule must be judged exactly once")
    for row in judged:
        if row.get("verdict") not in ("match", "no_match"):
            raise ValueError("each rule verdict must be match or no_match")
        if not str(row.get("evidence", "")).strip():
            raise ValueError("every judgement requires non-empty evidence")
    result = dict(assessment)
    if result.get("decision") not in ("accept", "reject", "defer", "would_accept", "silent"):
        raise ValueError("unknown assessment decision")
    if result.get("decision") == "accept":
        if result.get("strength") not in ("explicit", "inferred"):
            raise ValueError("accept requires explicit or inferred admission strength")
        if not any(row["verdict"] == "match" for row in judged):
            raise ValueError("accept requires at least one matched rule")
        if not str(result.get("intent_evidence", "")).strip():
            raise ValueError("accept requires intent evidence")
        if result.get("strength") == "inferred" and mode != "auto":
            result["decision"] = "would_accept"
    return result


def _sentences(text):
    return [s for s in re.split(r"[.!?]+", text) if s.strip()]


def grade_delivery(text, recipient_name="", goal_terms=()):
    """Stage-two delivery grade: start at 10, deduct 2 to 4 per criterion."""
    deductions = []
    score = 10

    def deduct(points, criterion, reason):
        nonlocal score
        score -= points
        deductions.append({"criterion": criterion, "points": points, "reason": reason})

    low = text.lower()
    words = text.split()
    if goal_terms:
        if not any(term.lower() in low for term in goal_terms):
            deduct(3, "goal_progression", "draft names none of the goal terms")
    elif not re.search(r"\b(done|ready|due|scheduled|confirmed|booked|finished|arrives|report|result)\b", low):
        deduct(3, "goal_progression", "no concrete outcome or goal reference")
    if recipient_name:
        if recipient_name.lower() not in low and "you" not in low and "your" not in low:
            deduct(2, "personalisation", "no recipient-specific reference")
    elif "you" not in low and "your" not in low:
        deduct(2, "personalisation", "generic broadcast wording")
    if not any(hint in low for hint in NEXT_STEP_HINTS):
        deduct(2, "proactive_tone", "no next step or actionable anchor")
    if len(words) > 50:
        deduct(3, "concise", f"{len(words)} words exceeds 50")
    elif len(_sentences(text)) > 2 and len(words) > 30:
        deduct(2, "concise", "more than two sentences and over 30 words")
    leaks = [marker for marker in LEAK_MARKERS if marker in low or marker in text]
    if leaks:
        deduct(4 if len(leaks) > 1 else 3, "natural_format", f"metadata leakage: {leaks}")
    return {"score": max(0, score), "deductions": deductions,
            "passed": score >= 7 and not any(d["criterion"] == "natural_format" for d in deductions)}


def consistency_filter(entries):
    """Drop inconsistent judge-calibration entries; never repair them."""
    kept, dropped, by_input = [], [], {}
    for entry in entries:
        key = (entry.get("input") or "").strip().lower()
        by_input.setdefault(key, set()).add(entry.get("human_label"))
    for entry in entries:
        reasons = []
        if entry.get("human_label") not in ("fire", "silent", "slow"):
            reasons.append("label outside the allowed set")
        if not entry.get("provenance"):
            reasons.append("missing provenance")
        if not entry.get("rationale"):
            reasons.append("missing rationale")
        key = (entry.get("input") or "").strip().lower()
        if len(by_input[key]) > 1:
            reasons.append("duplicate input with disagreeing human label")
        if reasons:
            dropped.append({**entry, "drop_reasons": reasons})
        else:
            kept.append(entry)
    return kept, dropped


def judge_agreement(entries, judge_fn):
    kept, _ = consistency_filter(entries)
    if not kept:
        return {"n": 0, "agreement": None}
    agree = sum(1 for entry in kept if judge_fn(entry["input"]) == entry["human_label"])
    return {"n": len(kept), "agreement": agree / len(kept)}


class LaneLedger:
    """Append-only JSONL ledger for fires, silence, feedback, and retries."""

    def __init__(self, path):
        self.path = path

    def record(self, record):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def rows(self):
        if not os.path.isfile(self.path):
            return []
        with open(self.path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def record_feedback(self, fire_id, outcome):
        if outcome not in ("accept", "reject", "ignore-timeout"):
            raise ValueError("feedback outcome must be accept, reject, or ignore-timeout")
        return self.record({"verdict": "feedback", "fire_id": fire_id, "outcome": outcome})

    def record_reformulation(self, origin_event, what_changed):
        if not what_changed:
            raise ValueError("a reformulation must name what changed")
        with locked(self.path):
            prior = [r for r in self.rows() if r.get("verdict") == "reformulation"
                     and r.get("origin_event") == origin_event]
            if prior:
                raise ValueError("at most one reformulation per origin event")
            return self.record({"verdict": "reformulation", "origin_event": origin_event,
                                "what_changed": what_changed})

    def audit_silence(self, sample_n=5):
        rows = self.rows()
        silent = [r for r in rows if r.get("verdict") in ("silent", "slow")]
        return {"counts": {v: sum(1 for r in rows if r.get("verdict") == v)
                           for v in sorted({r.get("verdict") for r in rows})},
                "silent_total": len(silent), "silent_sample": silent[-sample_n:],
                "missed_need": [r for r in silent if r.get("p_need", 0) >= 0.8]}


if __name__ == "__main__":
    print(__doc__)
