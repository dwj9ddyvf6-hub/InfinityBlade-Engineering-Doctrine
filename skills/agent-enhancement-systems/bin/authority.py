#!/usr/bin/env python3
"""Discipline 9: compaction and delegation as authority boundaries.

Summaries carry context, never authority. This module supplies the portable
pieces a host can actually enforce: a host-held mandate revalidated at
resume, a one-shot handoff capability store outside any tool registry,
bounded checkpoints, a recovery plan that does not replay read inputs,
split-safe fence stripping, and a mechanical peer-standing score.

Standard library only.
"""
import copy
import hashlib
import json
import math
import os
import re
import secrets
import time
from _storage import atomic_text, locked, read_text

CHECKPOINT_BOUNDS = {"objective": 500, "state": 2000, "evidence": 2000,
                     "decisions": 1000, "pending": 1000}
CHECKPOINT_TOTAL = 6000
RECOVERY_NOTE = ("Recovery: inspect what the prior attempt may already have done "
                 "before acting. Requeue only inputs the interrupted attempt never read.")


class Mandate:
    """Serialized scope declaration; the host must bind it to a trusted grant.

    The returned dict is not tamper-proof. Revalidation checks narrowing and
    versions against that supplied record, not the identity of its issuer.
    Keep the canonical grant outside model-controlled summaries.
    """

    @staticmethod
    def create(scope, granted_by, policy_version=1, generation=0):
        return {"scope": sorted(set(scope)), "granted_by": granted_by,
                "policy_version": policy_version, "generation": generation,
                "immutable": True}

    @staticmethod
    def revalidate(mandate, current_policy_version, requested_scope, generation=None):
        if not mandate.get("immutable"):
            raise ValueError("mandate is not an immutable object")
        if mandate.get("policy_version") != current_policy_version:
            raise ValueError("policy changed: mandate must be re-granted, not silently carried")
        if generation is not None and mandate.get("generation") != generation:
            raise ValueError("generation mismatch: authority is not inherited from a summary")
        extra = set(requested_scope) - set(mandate.get("scope", []))
        if extra:
            raise ValueError(f"requested scope widens the mandate: {sorted(extra)}")
        return True


class HandoffStore:
    """One-shot capability store. A token delivers a summary and nothing else."""

    def __init__(self, directory):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def _path(self, handoff_id):
        if not isinstance(handoff_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", handoff_id):
            raise ValueError("bad handoff id")
        return os.path.join(self.directory, handoff_id + ".json")

    def _load(self, handoff_id):
        path = self._path(handoff_id)
        if not os.path.lexists(path):
            raise ValueError(f"unknown handoff {handoff_id!r}")
        return json.loads(read_text(path))

    def _save(self, record):
        path = self._path(record["id"])
        atomic_text(path, json.dumps(record))

    def create(self, summary, ttl_s=900, now=None, admission_strength="explicit"):
        if not summary or not summary.strip():
            raise ValueError("empty summary rejected")
        if admission_strength not in ("explicit", "inferred", "not_admitted"):
            raise ValueError("admission_strength must be explicit, inferred, or not_admitted")
        if isinstance(ttl_s, bool) or not isinstance(ttl_s, (int, float)) or not math.isfinite(ttl_s) or ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        now = time.time() if now is None else now
        self._valid_time(now)
        self._valid_time(now + ttl_s)
        token = secrets.token_urlsafe(32)
        record = {"id": "ho-" + secrets.token_hex(8),
                  "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                  "summary": summary, "created": now, "expires": now + ttl_s,
                  "admission_strength": admission_strength, "waiter": None, "state": "open"}
        self._save(record)
        return record["id"], token

    @staticmethod
    def _valid_time(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("handoff clock must be a finite number")

    @staticmethod
    def _valid_waiter(waiter):
        if not isinstance(waiter, str) or not waiter.strip():
            raise ValueError("waiter must be a nonempty identity")

    def claim(self, handoff_id, waiter, now=None):
        self._valid_waiter(waiter)
        with locked(self._path(handoff_id)):
            now = time.time() if now is None else now
            self._valid_time(now)
            record = self._load(handoff_id)
            if record["state"] != "open":
                raise ValueError("handoff is not open")
            if now >= record["expires"]:
                record["state"] = "expired"; self._save(record)
                raise ValueError("handoff expired")
            if record["waiter"] is not None and record["waiter"] != waiter:
                raise ValueError("second waiter rejected: exactly one waiter")
            record["waiter"] = waiter
            self._save(record)
            return True

    def deliver(self, handoff_id, token, waiter, now=None):
        self._valid_waiter(waiter)
        with locked(self._path(handoff_id)):
            now = time.time() if now is None else now
            self._valid_time(now)
            record = self._load(handoff_id)
            if record["state"] != "open":
                raise ValueError("handoff already consumed: second delivery rejected")
            if now >= record["expires"]:
                record["state"] = "expired"; self._save(record)
                raise ValueError("handoff expired")
            if not secrets.compare_digest(hashlib.sha256(token.encode()).hexdigest(), record["token_sha256"]):
                raise ValueError("bad token: delivery rejected")
            if record["waiter"] is not None and record["waiter"] != waiter:
                raise ValueError("not the claimed waiter")
            record.update(state="consumed", delivered_at=now, delivered_to=waiter)
            self._save(record)
            return record["summary"]

def checkpoint_key(checkpoint):
    body = {k: checkpoint.get(k) for k in CHECKPOINT_BOUNDS}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def validate_checkpoint(checkpoint, now=None):
    errors = []
    total = 0
    for field, bound in CHECKPOINT_BOUNDS.items():
        value = checkpoint.get(field)
        if not isinstance(value, str) or not value:
            errors.append(f"{field} missing")
            continue
        total += len(value)
        if len(value) > bound:
            errors.append(f"{field} over bound {bound}: reject, never silently truncate")
    if total > CHECKPOINT_TOTAL:
        errors.append(f"checkpoint total over {CHECKPOINT_TOTAL}")
    if now is not None and checkpoint.get("expires", 0) <= now:
        errors.append("checkpoint expired")
    if checkpoint.get("key") and checkpoint["key"] != checkpoint_key(checkpoint):
        errors.append("checkpoint content-hash key does not match")
    return errors


def recovery_plan(attempt):
    return {"requeue": list(attempt.get("unread", [])), "do_not_replay": list(attempt.get("read", [])),
            "note": RECOVERY_NOTE}


def make_fence_token(run_id):
    return f"<<FENCE:{run_id}:{secrets.token_hex(8)}>>"


class FenceFilter:
    """Strip fenced content from a stream without splitting the token.

    Text before the token is emitted. Once the token appears, the rest of
    the stream is fenced material and is withheld. The holdback buffer is
    sized to the token, so a token split across chunks cannot leak through.
    """

    def __init__(self, token):
        if not isinstance(token, str) or not token:
            raise ValueError("fence token must be a nonempty string")
        self.token = token
        self.buffer = ""
        self.closed = False

    def feed(self, chunk):
        if self.closed:
            return ""
        self.buffer += chunk
        index = self.buffer.find(self.token)
        if index >= 0:
            out = self.buffer[:index]
            self.buffer = ""
            self.closed = True
            return out
        keep = max(0, len(self.buffer) - (len(self.token) - 1))
        out, self.buffer = self.buffer[:keep], self.buffer[keep:]
        return out

    def flush(self):
        if self.closed:
            return ""
        out, self.buffer = self.buffer, ""
        return out


def transactional_compact(history, transform, expected_generation, current_generation):
    """Generation-checked compaction with restore-on-failure."""
    if expected_generation != current_generation:
        raise ValueError("generation mismatch: compaction refused")
    original = copy.deepcopy(history)
    try:
        compacted = transform(copy.deepcopy(history))
        if not isinstance(compacted, list):
            raise ValueError("compaction must return a history list")
    except Exception:
        return {"history": original, "restored": True, "ok": False}
    return {"history": compacted, "restored": False, "ok": True}


def peer_standing(events, floor=70):
    """Standing is mechanical: repeated defects lower it; below floor is read-only."""
    weights = {"defect": 10, "severe_defect": 25, "clean_run": 2}
    score, quarantined = 100, False
    for event in events:
        kind = event.get("kind")
        if kind == "human_restore":
            if not event.get("reviewer") or not event.get("evidence"):
                raise ValueError("human restoration requires reviewer and evidence from the trusted host")
            score, quarantined = max(score, floor), False
        elif kind == "clean_run":
            score = min(100, score + weights[kind])
        else:
            score = max(0, score - weights.get(kind, 10))
        quarantined = quarantined or score < floor
    return {"score": score, "access": "read-only" if quarantined else "write",
            "floor": floor, "restore": "a human restores standing below the floor"}


if __name__ == "__main__":
    print(__doc__)
