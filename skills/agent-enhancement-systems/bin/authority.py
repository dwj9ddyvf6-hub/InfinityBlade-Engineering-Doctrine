#!/usr/bin/env python3
"""Discipline 9: compaction and delegation as authority boundaries.

Summaries carry context, never authority. This module supplies the portable
pieces a host can actually enforce: an immutable mandate revalidated at
resume, a one-shot handoff capability store outside any tool registry,
bounded checkpoints, a recovery plan that does not replay read inputs,
split-safe fence stripping, and a mechanical peer-standing score.

Standard library only.
"""
import hashlib
import json
import os
import re
import secrets
import time

CHECKPOINT_BOUNDS = {"objective": 500, "state": 2000, "evidence": 2000,
                     "decisions": 1000, "pending": 1000}
CHECKPOINT_TOTAL = 6000
RECOVERY_NOTE = ("Recovery: inspect what the prior attempt may already have done "
                 "before acting. Requeue only inputs the interrupted attempt never read.")


class Mandate:
    """An immutable scope grant. Revalidation can narrow, never widen."""

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
        if not handoff_id or "/" in handoff_id or ".." in handoff_id:
            raise ValueError("bad handoff id")
        return os.path.join(self.directory, handoff_id + ".json")

    def _load(self, handoff_id):
        path = self._path(handoff_id)
        if not os.path.isfile(path):
            raise ValueError(f"unknown handoff {handoff_id!r}")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, record):
        path = self._path(record["id"])
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
        os.replace(tmp, path)

    def create(self, summary, ttl_s=900, now=None, admission_strength="explicit"):
        if not summary or not summary.strip():
            raise ValueError("empty summary rejected")
        if admission_strength not in ("explicit", "inferred", "not_admitted"):
            raise ValueError("admission_strength must be explicit, inferred, or not_admitted")
        now = time.time() if now is None else now
        token = secrets.token_urlsafe(32)
        record = {"id": "ho-" + secrets.token_hex(8),
                  "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                  "summary": summary, "created": now, "expires": now + ttl_s,
                  "admission_strength": admission_strength, "waiter": None, "state": "open"}
        self._save(record)
        return record["id"], token

    def claim(self, handoff_id, waiter, now=None):
        now = time.time() if now is None else now
        record = self._load(handoff_id)
        if record["state"] != "open":
            raise ValueError("handoff is not open")
        if now > record["expires"]:
            record["state"] = "expired"; self._save(record)
            raise ValueError("handoff expired")
        if record["waiter"] is not None and record["waiter"] != waiter:
            raise ValueError("second waiter rejected: exactly one waiter")
        record["waiter"] = waiter
        self._save(record)
        return True

    def deliver(self, handoff_id, token, waiter, now=None):
        now = time.time() if now is None else now
        record = self._load(handoff_id)
        if record["state"] != "open":
            raise ValueError("handoff already consumed: second delivery rejected")
        if now > record["expires"]:
            record["state"] = "expired"; self._save(record)
            raise ValueError("handoff expired")
        if hashlib.sha256(token.encode()).hexdigest() != record["token_sha256"]:
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
    original = list(history)
    try:
        compacted = transform(list(history))
    except Exception:
        return {"history": original, "restored": True, "ok": False}
    return {"history": compacted, "restored": False, "ok": True}


def peer_standing(events, floor=70):
    """Standing is mechanical: repeated defects lower it; below floor is read-only."""
    weights = {"defect": 10, "severe_defect": 25, "clean_run": 2}
    score = 100
    for event in events:
        kind = event.get("kind")
        if kind == "clean_run":
            score = min(100, score + weights[kind])
        else:
            score -= weights.get(kind, 10)
    return {"score": max(0, score), "access": "write" if score >= floor else "read-only",
            "floor": floor, "restore": "a human restores standing below the floor"}


if __name__ == "__main__":
    print(__doc__)
