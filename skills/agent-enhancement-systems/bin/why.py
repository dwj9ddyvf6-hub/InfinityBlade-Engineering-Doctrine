#!/usr/bin/env python3
"""Discipline 11: record the why, not just the what.

A rationale entry carries the decision, the alternatives it beat and why
they lost, the evidence grade, and the trigger that reopens it. Identity is
a stable UUID. Superseded entries are never injected as current context.
Reusable context is addressed by content hash in the fragment registry.

Standard library only.
"""
import hashlib
import json
import os
import re
from _storage import atomic_text, locked
import time
import uuid

TYPES = ("decision", "workaround", "incident", "constraint", "undefined")
STATUSES = ("active", "superseded", "open", "needs-review", "pending-confirmation")
EVIDENCE = ("confirmed", "inferred", "unknown")


def new_entry(decision, rejected, reason, type_, source, revisit_when, see,
              evidence="unknown", pending_confirmation=True):
    return {"id": str(uuid.uuid4()), "decision": decision, "rejected": rejected,
            "reason": reason, "type": type_, "status": "active", "evidence": evidence,
            "source": source, "revisit_when": revisit_when, "see": see,
            "pending_confirmation": bool(pending_confirmation)}


def validate_entry(entry):
    errors = []
    if not isinstance(entry, dict):
        return ["entry is not an object"]
    try:
        uuid.UUID(str(entry.get("id", "")))
    except Exception:
        errors.append("id missing or not a UUID")
    if not entry.get("decision"):
        errors.append("decision missing")
    rejected = entry.get("rejected")
    if not isinstance(rejected, list) or not rejected:
        errors.append("rejected alternatives missing")
    else:
        for row in rejected:
            if not isinstance(row, dict) or not row.get("alternative") or not row.get("why_lost"):
                errors.append("each rejected alternative needs alternative and why_lost")
                break
    if not entry.get("reason"):
        errors.append("reason missing")
    if entry.get("type") not in TYPES:
        errors.append(f"type must be one of {TYPES}")
    if entry.get("type") == "undefined" and not entry.get("type_reason"):
        errors.append("undefined type requires type_reason")
    if entry.get("status") not in STATUSES:
        errors.append(f"status must be one of {STATUSES}")
    if entry.get("status") == "superseded" and not entry.get("superseded_by"):
        errors.append("superseded entry requires superseded_by")
    if entry.get("status") == "superseded" and entry.get("superseded_by") == "none" \
            and not entry.get("superseded_by_note"):
        errors.append("superseded_by none requires superseded_by_note")
    if entry.get("evidence") not in EVIDENCE:
        errors.append(f"evidence must be one of {EVIDENCE}")
    for field in ("source", "revisit_when", "see"):
        if not entry.get(field):
            errors.append(f"{field} missing")
    return errors


def append_entry(path, entry):
    errors = validate_entry(entry)
    if errors:
        raise ValueError(f"rationale entry refused: {errors}")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry["id"]


def _file_digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def load_store(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def injection_view(path):
    return [entry for entry in load_store(path) if entry.get("status") == "active"]


def validate_exemplar(exemplar):
    errors = []
    for field in ("task_class", "situation", "approach", "why_it_worked"):
        if not exemplar.get(field):
            errors.append(f"exemplar {field} missing")
    return errors


def evaluate_experience(records):
    """Experience-memory eval shape: score knowledge classes over trajectories."""
    classes = ("static_state", "dynamic_state", "workflow", "environment_gotchas", "premise_awareness")
    counts = {name: 0 for name in classes}
    for record in records:
        if record.get("class") in counts and record.get("correct"):
            counts[record["class"]] += 1
    totals = {name: sum(1 for r in records if r.get("class") == name) for name in classes}
    return {"scores": {name: (counts[name] / totals[name] if totals[name] else None) for name in classes},
            "totals": totals}


class FragmentRegistry:
    """Content-addressed reusable context, stored once under its SHA-256."""

    def __init__(self, registry):
        self.registry = registry
        self.objects = os.path.join(registry, "objects")
        self.index_path = os.path.join(registry, "index.json")

    def _index(self):
        if os.path.isfile(self.index_path):
            with open(self.index_path, encoding="utf-8") as handle:
                return json.load(handle)
        return {}

    def _save(self, index):
        os.makedirs(self.objects, exist_ok=True)
        tmp = self.index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(index, handle, indent=1, sort_keys=True)
        os.replace(tmp, self.index_path)

    def put_bytes(self, data, name):
        digest = hashlib.sha256(data).hexdigest()
        os.makedirs(self.objects, exist_ok=True)
        dest = os.path.join(self.objects, digest)
        if not os.path.isfile(dest):
            with open(dest + ".tmp", "wb") as handle:
                handle.write(data)
            os.replace(dest + ".tmp", dest)
        index = self._index()
        record = index.get(digest, {"names": [], "size": len(data), "stored_at": time.time()})
        if name not in record["names"]:
            record["names"].append(name)
        index[digest] = record
        self._save(index)
        return digest

    def resolve(self, prefix):
        if not isinstance(prefix, str) or not re.fullmatch(r"[a-f0-9]{8,64}", prefix):
            raise ValueError("fragment address must be an 8-to-64 character lowercase SHA-256 prefix")
        matches = [h for h in self._index() if h.startswith(prefix)]
        if len(matches) != 1:
            raise KeyError(f"hash prefix matches {len(matches)} objects")
        return matches[0]

    def get_bytes(self, hash_or_prefix):
        digest = self.resolve(hash_or_prefix)
        path = os.path.join(self.objects, digest)
        if os.path.islink(path):
            raise ValueError("fragment object must not be a symlink")
        with open(path, "rb") as handle:
            data = handle.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("fragment content hash mismatch")
        return data

    def cite(self, name):
        matches = [digest for digest, record in self._index().items() if name in record["names"]]
        if len(matches) != 1:
            raise KeyError(f"fragment name resolves to {len(matches)} versions; cite the exact hash")
        return "{{fragment:%s@%s}}" % (name, matches[0][:16])

    def verify(self):
        bad = []
        for digest in self._index():
            path = os.path.join(self.objects, digest)
            if not os.path.isfile(path):
                bad.append((digest, "missing object"))
            elif _file_digest(path) != digest:
                bad.append((digest, "hash mismatch"))
        return bad


if __name__ == "__main__":
    print(__doc__)
