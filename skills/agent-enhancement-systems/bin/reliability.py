#!/usr/bin/env python3
"""Discipline 7 evidence layer: hash-chained capsules and honest metrics.

A capsule records what was declared about a consequential action. It is not
containment and it does not prove the action was safe. Replay refuses SE3
and SE4 classes and fails closed on a broken chain.

Standard library only.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from _storage import locked

CLASSES = ("SE0", "SE1", "SE2", "SE3", "SE4")
REPLAYABLE = ("SE0", "SE1", "SE2")


def _hash(body):
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest()


class EvidenceCapsules:
    def __init__(self, path):
        self.path = path

    def _read(self):
        if not os.path.isfile(self.path):
            return []
        with open(self.path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def record(self, actor, action, effect_class, target, detail=None, ts=None, allow_se4=False):
        if effect_class not in CLASSES:
            raise ValueError(f"effect_class must be one of {CLASSES}")
        if effect_class == "SE4" and not allow_se4:
            raise ValueError("SE4 is forbidden in record mode unless a trusted caller allows it")
        with locked(self.path):
            rows = self._read()
            if not self._verify_rows(rows)["ok"]:
                raise ValueError("cannot append to an invalid capsule chain")
            capsule = {"seq": len(rows) + 1, "ts": ts if ts is not None else datetime.now(timezone.utc).isoformat(), "actor": actor, "action": action,
                       "effect_class": effect_class, "target": target, "detail": detail or {},
                       "prev": rows[-1]["hash"] if rows else "GENESIS"}
            capsule["hash"] = _hash(capsule)
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(capsule, sort_keys=True) + "\n")
            return capsule

    @staticmethod
    def _verify_rows(rows):
        previous = "GENESIS"
        for i, capsule in enumerate(rows, 1):
            if not isinstance(capsule, dict):
                return {"ok": False, "entries": len(rows), "error": {"seq": i, "code": "BAD_RECORD"}}
            if capsule.get("effect_class") not in CLASSES:
                return {"ok": False, "entries": len(rows), "error": {"seq": i, "code": "BAD_CLASS"}}
            if capsule.get("seq") != i:
                return {"ok": False, "entries": len(rows), "error": {"seq": i, "code": "SEQ_GAP"}}
            if capsule.get("prev") != previous:
                return {"ok": False, "entries": len(rows), "error": {"seq": i, "code": "CHAIN_BREAK"}}
            body = {k: v for k, v in capsule.items() if k != "hash"}
            if _hash(body) != capsule.get("hash"):
                return {"ok": False, "entries": len(rows), "error": {"seq": i, "code": "HASH_MISMATCH"}}
            previous = capsule["hash"]
        return {"ok": True, "entries": len(rows), "error": None}

    def verify(self):
        try:
            rows = self._read()
        except (ValueError, OSError):
            return {"ok": False, "entries": None, "error": {"code": "UNREADABLE_CHAIN"}}
        return self._verify_rows(rows)

    def replay_plan(self):
        rows = self._read()
        result = self._verify_rows(rows)
        if not result["ok"]:
            raise ValueError(f"replay fails closed: {result['error']}")
        return {"replayable": [c for c in rows if c["effect_class"] in REPLAYABLE],
                "refused": [{"seq": c["seq"], "effect_class": c["effect_class"],
                             "reason": "SE3 and above are refused in replay"}
                            for c in rows if c["effect_class"] not in REPLAYABLE]}


def unique_cover(obligations, evidence):
    uncovered, ambiguous = [], []
    for obligation in obligations:
        candidates = [row for row in evidence if obligation in row.get("covers", [])]
        if not candidates:
            uncovered.append(obligation)
        elif len(candidates) > 1:
            ambiguous.append(obligation)
    return (not uncovered and not ambiguous), uncovered, ambiguous


def metric_record(value, provenance):
    """A headline metric must say whether it was measured or replayed."""
    if provenance not in ("measured_this_run", "replayed"):
        raise ValueError("metric provenance must be measured_this_run or replayed")
    return {"value": value, "provenance": provenance}


def closure_check(claim, record):
    """Mechanical closure hygiene: a cited PR or release must exist/merge."""
    kind = claim.get("cites")
    if kind == "pull_request":
        ok = bool(record and record.get("merged"))
        return {"ok": ok, "reason": "PR merged" if ok else "cited PR is not merged or does not exist"}
    if kind == "release":
        ok = bool(record and record.get("exists"))
        return {"ok": ok, "reason": "release exists" if ok else "cited release does not exist"}
    return {"ok": True, "reason": "no mechanical closure citation to check"}


if __name__ == "__main__":
    print(__doc__)
