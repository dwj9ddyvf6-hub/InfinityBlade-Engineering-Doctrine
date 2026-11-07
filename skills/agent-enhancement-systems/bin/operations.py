#!/usr/bin/env python3
"""Disciplines 13 to 18: outbound gates, IDs, effects, routing, learning.

The send path, identity layer, durable effect queue, owner routing, near-miss
ledger, and content-bound approvals share one property: each is enforced in
code at the boundary where the act happens, not described in a prompt.

Standard library only.
"""
from functools import wraps
from itertools import islice
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from _storage import atomic_text, locked


# ---------------------------------------------------------------- IDs (14)

def deterministic_id(parts):
    """Truncated SHA-256 of the canonical serialisation of the defining parts."""
    canon = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32]


def record_id(record):
    if isinstance(record.get("id"), str) and record["id"]:
        return record["id"]
    return deterministic_id(record)


def check_stream(path):
    seen, duplicates, total = {}, [], 0
    with open(path, encoding="utf-8") as handle:
        for i, line in enumerate(handle, 1):
            if not line.strip():
                continue
            total += 1
            rid = record_id(json.loads(line))
            if rid in seen:
                duplicates.append((i, rid, seen[rid]))
            else:
                seen[rid] = i
    return total, len(seen), duplicates


def revision_event_id(source_id, revision_stamp):
    """An edit is a new event by design when the revision stamp is in the ID."""
    return deterministic_id(["event", source_id, revision_stamp])


# ------------------------------------------------------------- redaction (13/14)

SENSITIVE_SUBSTRINGS = ("password", "secret", "token", "api_key", "apikey", "credential",
                        "private_key", "authorization", "cookie", "session")
CONTENT_KEYS = {"prompt", "question", "query", "selection"}
MAX_DEPTH = 8


def _key_sensitive(key):
    lowered = str(key).lower()
    return any(part in lowered for part in SENSITIVE_SUBSTRINGS) or lowered in CONTENT_KEYS


def redact(obj, _depth=0, _seen=None):
    """Key-based diagnostic redaction; not a general personal-data detector."""
    ancestors = set() if _seen is None else _seen
    if _depth > MAX_DEPTH:
        return "REDACTED_TOO_DEEP"
    if isinstance(obj, (dict, list, tuple)):
        if id(obj) in ancestors:
            return "REDACTED_CIRCULAR_REFERENCE"
        ancestors = ancestors | {id(obj)}
        if isinstance(obj, dict):
            return {k: ("REDACTED" if _key_sensitive(k) else redact(v, _depth + 1, ancestors))
                    for k, v in obj.items()}
        return [redact(value, _depth + 1, ancestors) for value in obj]
    return obj


def _synchronized(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with locked(self.path):
            self._reload()
            return method(self, *args, **kwargs)
    return wrapper

# ------------------------------------------------------------ outbound (13)

DEFAULT_CAPS = {"chat": {"words": 500, "chars": 20000},
                "short": {"words": 50, "chars": 320},
                "routing_note": {"words": 30, "chars": 240}}
PURPOSES = ("result", "attention", "answer", "notification")


class OutboundGate:
    """Purpose-gated sends with permanent receipts and hard caps.

    One acknowledgement per origin event: the first text wins and a repeat
    returns duplicate_suppressed without writing a second send receipt.
    """

    def __init__(self, receipts_path, caps=None, open_question=None, transport=None):
        self.path = receipts_path
        self.caps = caps or DEFAULT_CAPS
        self.open_question = open_question
        self.transport = transport

    def _receipts(self):
        if not os.path.isfile(self.path):
            return []
        with open(self.path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _append(self, receipt):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, sort_keys=True) + "\n")

    def _check_purpose(self, purpose, context):
        if purpose not in PURPOSES:
            raise ValueError(f"purpose missing or not allowed: {purpose!r}")
        if purpose == "result" and context.get("outcome_status") not in ("ready", "completed"):
            raise ValueError("result purpose requires a ready or completed outcome")
        if purpose == "attention":
            if not self.open_question or context.get("question") != self.open_question:
                raise ValueError("attention purpose requires the exact current open question")
        if purpose == "answer" and not context.get("answer_ready"):
            raise ValueError("answer purpose requires a reported answer")
        if purpose == "notification" and not context.get("origin_event"):
            raise ValueError("notification purpose requires its origin event")

    def send(self, surface, text, purpose, origin_event, recipient, context=None):
        context = dict(context or {})
        context.setdefault("origin_event", origin_event)
        if surface not in self.caps:
            raise ValueError(f"unknown surface {surface!r}: fail closed")
        if not origin_event:
            raise ValueError("origin_event required")
        if not recipient:
            raise ValueError("recipient required")
        if not text or not text.strip():
            raise ValueError("empty text")
        self._check_purpose(purpose, context)
        words = len(text.split())
        if words > self.caps[surface]["words"]:
            raise ValueError(f"word cap exceeded on {surface}: {words} > {self.caps[surface]['words']}")
        if len(text) > self.caps[surface]["chars"]:
            raise ValueError(f"character cap exceeded on {surface}: {len(text)} > {self.caps[surface]['chars']}")
        receipt = {"id": deterministic_id(["send", surface, origin_event, recipient, text]),
                   "surface": surface, "purpose": purpose, "origin_event": origin_event,
                   "recipient": recipient, "words": words, "sent": False,
                   "text_sha256": hashlib.sha256(text.encode()).hexdigest()}
        if self.transport is None:
            return {**receipt, "status": "ready", "reason": "validated only; no transport configured"}
        with locked(self.path):
            prior = [r for r in self._receipts() if r.get("origin_event") == origin_event
                     and (r.get("sent") or r.get("status") in ("in_flight", "outcome_unknown"))]
            if prior:
                return {"sent": False, "status": "duplicate_suppressed", "receipt_id": prior[0]["id"],
                        "reason": "origin already acknowledged or unresolved; reconcile before retrying"}
            self._append({**receipt, "status": "in_flight"})
        try:
            acknowledgement = self.transport(surface=surface, text=text, recipient=recipient,
                                             idempotency_key=receipt["id"])
            if not isinstance(acknowledgement, dict) or not (acknowledgement.get("id") or acknowledgement.get("receipt_id")):
                raise ValueError("transport must return an acknowledgement ID")
        except Exception as exc:
            result = {**receipt, "status": "outcome_unknown", "error_type": type(exc).__name__,
                      "reason": "transport may have acted; reconcile against its receipt before retrying"}
        else:
            result = {**receipt, "sent": True, "status": "sent",
                      "transport_receipt": redact(acknowledgement)}
        with locked(self.path):
            self._append(result)
        return result


# --------------------------------------------------------- effect queue (15)

QUEUE_SCHEMA = """CREATE TABLE IF NOT EXISTS effects(
 kind TEXT NOT NULL, key TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}',
 generation INTEGER NOT NULL DEFAULT 1, state TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0, infra_errors INTEGER NOT NULL DEFAULT 0,
 revision INTEGER NOT NULL DEFAULT 0, queued_at REAL NOT NULL DEFAULT 0,
 next_at REAL NOT NULL DEFAULT 0, updated_at REAL NOT NULL DEFAULT 0,
 receipt TEXT, last_error TEXT, PRIMARY KEY(kind, key))"""


class RetryableEffectError(Exception):
    """Host confirms no uncertain external effect; retry is safe for this failure."""


class EffectQueue:
    """Durable, generation-guarded side-effect queue backed by SQLite."""

    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(QUEUE_SCHEMA)
        self.db.commit()
        self.ran = False
        self.skipped = []

    def enqueue(self, kind, key, payload=None, revision=None):
        now = time.time()
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT generation, revision, queued_at FROM effects WHERE kind=? AND key=?",
                                  (kind, key)).fetchone()
            if row and revision is not None and revision <= row[1]:
                return "stale"
            generation = (row[0] + 1) if row else 1
            queued_at = row[2] if row else now
            self.db.execute(
                "INSERT INTO effects(kind,key,payload,generation,state,attempts,infra_errors,revision,queued_at,next_at,updated_at,receipt) "
                "VALUES(?,?,?,?,'pending',0,0,?,?,?,?,'') ON CONFLICT(kind,key) DO UPDATE SET "
                "payload=excluded.payload,generation=excluded.generation,state='pending',revision=excluded.revision,"
                "attempts=0,infra_errors=0,next_at=excluded.next_at,last_error=NULL,updated_at=excluded.updated_at,receipt=''",
                (kind, key, json.dumps(payload or {}), generation, revision or 0, queued_at, now, now))
        return generation

    def get(self, kind, key):
        row = self.db.execute(
            "SELECT kind,key,payload,generation,state,attempts,infra_errors,revision,queued_at,receipt,next_at,last_error "
            "FROM effects WHERE kind=? AND key=?", (kind, key)).fetchone()
        if not row:
            return None
        return {"kind": row[0], "key": row[1], "payload": json.loads(row[2]), "generation": row[3],
                "state": row[4], "attempts": row[5], "infra_errors": row[6], "revision": row[7],
                "queued_at": row[8], "receipt": row[9], "next_at": row[10], "last_error": row[11]}

    def issue_receipt(self, kind, key, generation):
        receipt = f"rcpt-{kind}-{key}-{generation}"
        cursor = self.db.execute("UPDATE effects SET receipt=? WHERE kind=? AND key=? AND generation=?",
                        (receipt, kind, key, generation))
        self.db.commit()
        if cursor.rowcount != 1:
            raise ValueError("cannot issue receipt for an absent or stale generation")
        return receipt

    def complete(self, kind, key, generation, receipt=None):
        if receipt is not None:
            cursor = self.db.execute("DELETE FROM effects WHERE kind=? AND key=? AND generation=? AND receipt=?",
                                     (kind, key, generation, receipt))
        else:
            cursor = self.db.execute("DELETE FROM effects WHERE kind=? AND key=? AND generation=?",
                                     (kind, key, generation))
        self.db.commit()
        return cursor.rowcount == 1

    def defer_later(self, kind, key, generation, delay_s=60):
        cursor = self.db.execute(
            "UPDATE effects SET state='later',next_at=?,updated_at=? WHERE kind=? AND key=? AND generation=?",
            (time.time() + delay_s, time.time(), kind, key, generation))
        self.db.commit()
        return cursor.rowcount == 1

    def fail(self, kind, key, generation, error="", max_attempts=3):
        """Explicit host declaration that a known failure is safe to retry."""
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            cursor = self.db.execute(
                "UPDATE effects SET state=CASE WHEN attempts+1>=? THEN 'failed' ELSE 'pending' END,"
                "attempts=attempts+1,last_error=?,next_at=?,updated_at=? "
                "WHERE kind=? AND key=? AND generation=?",
                (max_attempts, str(error), time.time(), time.time(), kind, key, generation))
            row = self.get(kind, key)
        if cursor.rowcount and row["state"] == "failed":
            self.skipped.append({"kind": kind, "key": key, "last_error": str(error),
                                 "state": "skipped", "terminal": True})
        return cursor.rowcount == 1

    def record_rate_limited(self, kind, key, generation, retry_after=None, base=2.0, cap=300.0):
        row = self.get(kind, key)
        pause = min(cap, base * (2 ** row["infra_errors"])) if row else base
        if retry_after is not None:
            pause = max(pause, retry_after)
        cursor = self.db.execute(
            "UPDATE effects SET state='later',infra_errors=infra_errors+1,next_at=?,updated_at=? "
            "WHERE kind=? AND key=? AND generation=?", (time.time() + pause, time.time(), kind, key, generation))
        self.db.commit()
        return cursor.rowcount == 1

    def run_next(self, handler):
        """Atomically claim due work. The handler must explicitly complete/defer it.

        Unacknowledged running work stays reserved after a crash; the host must
        reconcile its external outcome. It is never blindly replayed.
        """
        self.ran = True
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT kind,key,generation FROM effects WHERE state IN ('pending','later') "
                                  "AND next_at<=? ORDER BY queued_at,kind,key LIMIT 1", (time.time(),)).fetchone()
            if not row:
                return None
            kind, key, generation = row
            self.db.execute("UPDATE effects SET state='running',updated_at=? WHERE kind=? AND key=? AND generation=?",
                            (time.time(), kind, key, generation))
            item = self.get(kind, key)
        try:
            handler(item)
        except RetryableEffectError as exc:
            self.fail(kind, key, generation, error=repr(exc))
            return "failed:" + key
        except Exception as exc:
            # The handler may have acted before losing its acknowledgement.
            # Ordinary exceptions cannot establish that replay is safe.
            self.db.execute("UPDATE effects SET state='outcome_unknown',last_error=?,updated_at=? "
                            "WHERE kind=? AND key=? AND generation=?",
                            (type(exc).__name__, time.time(), kind, key, generation))
            self.db.commit()
            return "outcome_unknown:" + key
        return "ok:" + key

    def stop(self):
        if not self.ran:
            return None
        remaining = self.db.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
        return "partial" if remaining else "completed"

    def close(self):
        self.db.close()


def outbox_append(path, record):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def outbox_pending(path):
    sent = 0
    marker = path + ".sent"
    if os.path.exists(marker):
        with open(marker, encoding="utf-8") as handle:
            sent = int(handle.read().strip() or 0)
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    return [json.loads(line) for line in lines[sent:] if line.strip()], len(lines)


# ------------------------------------------------------------- routing (16)

def route_followup(owner, sender_authorized):
    if not sender_authorized:
        return {"routed": False, "reason": "authorization check failed on the bypass: refused even though an owner exists"}
    if not owner:
        return {"routed": False, "reason": "no live owner: normal triage applies"}
    return {"routed": True, "owner": owner, "reason": "routed to live owner; authorization checked"}


class SlotGuard:
    """Reserve worker slots before work starts; one extra human slot only."""

    def __init__(self, state_path, worker_cap=4):
        if not 1 <= worker_cap <= 16:
            raise ValueError("worker_cap must be between 1 and 16")
        self.path = state_path
        self.worker_cap = worker_cap
        self.state = {"workers": [], "human_slot_used_by": None}
        self._reload()

    def _reload(self):
        self.state = {"workers": [], "human_slot_used_by": None}
        if os.path.isfile(self.path):
            with open(self.path, encoding="utf-8") as handle:
                self.state = json.load(handle)

    def _save(self):
        atomic_text(self.path, json.dumps(self.state))

    @_synchronized
    def reserve_worker(self, job_id):
        if job_id in self.state["workers"]:
            return True
        if len(self.state["workers"]) >= self.worker_cap:
            raise ValueError(f"worker cap {self.worker_cap} reached; workers may not use the human slot")
        self.state["workers"].append(job_id)
        self._save()
        return True

    @_synchronized
    def reserve_human(self, request_id):
        if self.state["human_slot_used_by"] not in (None, request_id):
            raise ValueError("human slot already in use: the plus-one is exactly one")
        self.state["human_slot_used_by"] = request_id
        self._save()
        return True

    @_synchronized
    def release(self, job_id):
        if job_id in self.state["workers"]:
            self.state["workers"].remove(job_id)
        if self.state["human_slot_used_by"] == job_id:
            self.state["human_slot_used_by"] = None
        self._save()
        return True


# ---------------------------------------------------------- near misses (17)

MAX_LAWS = 4096
MAX_REPORTED = 512
MAX_SAMPLES = 4
MAX_TEXT = 400
GATES = {"threshold", "scope", "authority", "freshness", "cost", "other"}


def skeleton(text):
    value = re.sub(r"\b\d+(\.\d+)?\b", "<n>", str(text))
    value = re.sub(r"['\"][^'\"]*['\"]", "<s>", value)
    return value[:MAX_TEXT]


class NearMissLedger:
    """Bounded diagnostics-only ledger. It can never prove impossibility."""

    def __init__(self, path):
        self.path = path
        self.rows = []

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as handle:
                self.rows = [json.loads(line) for line in islice((line for line in handle if line.strip()), MAX_LAWS)]
        return self

    def _reload(self):
        self.rows = []
        self.load()

    @_synchronized
    def record(self, law_id, gate, premise):
        if gate not in GATES:
            raise ValueError(f"gate must be a coarse class in {sorted(GATES)}")
        if len(self.rows) >= MAX_LAWS:
            return False
        row = {"law": str(law_id)[:MAX_TEXT], "gate": gate, "skeleton": skeleton(premise)}
        self.rows.append(row)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return True

    def report(self):
        rows = self.rows[:MAX_REPORTED]
        by_gate = {}
        samples = {}
        for row in rows:
            by_gate[row["gate"]] = by_gate.get(row["gate"], 0) + 1
            samples.setdefault(row["law"], [])
            if len(samples[row["law"]]) < MAX_SAMPLES:
                samples[row["law"]].append(row["skeleton"])
        return {"count": len(rows), "by_gate": by_gate, "samples": samples,
                "non_authority": "diagnostics only: no ranking, selection, rejection, or impossibility inference"}


# ------------------------------------------------------------ approvals (18)

class ApprovalStore:
    """Approvals bound to action, resolved target, and exact content hash."""

    def __init__(self, path, generation=0):
        self.path = path
        self.generation = generation
        self.rows = []
        self._reload()

    def _reload(self):
        self.rows = []
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as handle:
                self.rows = [json.loads(line) for line in handle if line.strip()]

    def _save(self):
        atomic_text(self.path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in self.rows))

    @staticmethod
    def content_hash(data):
        return hashlib.sha256(data).hexdigest()

    @_synchronized
    def record(self, action, target, content, ttl_days=30, now=None):
        now = time.time() if now is None else now
        row = {"action": action, "target": target, "hash": self.content_hash(content),
               "generation": self.generation, "expires": now + ttl_days * 86400,
               "revoked": False, "used": False}
        self.rows.append(row)
        self._save()
        return row

    @_synchronized
    def revoke(self, action, target):
        for row in self.rows:
            if row["action"] == action and row["target"] == target:
                row["revoked"] = True
        self._save()

    @_synchronized
    def check(self, action, candidates, content, now=None):
        now = time.time() if now is None else now
        matches = [r for r in self.rows if r["action"] == action and r["target"] in candidates]
        if not matches:
            return "out_of_scope"
        valid = [r for r in matches if not r["revoked"] and not r["used"]
                 and r["expires"] > now and r["generation"] == self.generation]
        if not valid:
            return "authorization_invalid"
        distinct_targets = {json.dumps(c, sort_keys=True) for c in candidates}
        valid_targets = {json.dumps(r["target"], sort_keys=True) for r in valid}
        if len(distinct_targets) > 1 and len(valid_targets) > 1:
            return "requires_selection"
        if not any(r["hash"] == self.content_hash(content) for r in valid):
            return "drifted"
        return "authorized_unique"

    @_synchronized
    def authorize_and_consume(self, action, candidates, content, now=None):
        verdict = ApprovalStore.check.__wrapped__(self, action, candidates, content, now=now)
        if verdict != "authorized_unique":
            return verdict
        now = time.time() if now is None else now
        for row in self.rows:
            if (row["action"] == action and row["target"] in candidates
                    and row["hash"] == self.content_hash(content) and not row["revoked"]
                    and not row["used"] and row["expires"] > now and row["generation"] == self.generation):
                row["used"] = True
                self._save()
                return verdict
        raise RuntimeError("approval changed inside transaction")

    @_synchronized
    def consume(self, action, target):
        for row in self.rows:
            if row["action"] == action and row["target"] == target and not row["used"]:
                row["used"] = True
        self._save()


if __name__ == "__main__":
    print(__doc__)
