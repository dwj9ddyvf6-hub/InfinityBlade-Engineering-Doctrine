#!/usr/bin/env python3
"""Disciplines 4 and 5: profile-plus-graph memory and honest recall.

The store is one directory owned by the adopting host:

    <store>/profile.json   standing facts, capped at 8 static + 8 dynamic
    <store>/facts.jsonl    dynamic facts with typed edges and validity stamps
    <store>/retrievals.jsonl
    <store>/erasure/       receipts and tombstones written by forgetting

Facts remain inspectable JSON. A single store lock serializes cooperating
readers/writers; a private write-ahead journal completes interrupted multi-file
operations before any public read or write. The journal stores replacement
content, never the erased fact payload. Standard library only.
"""
import hashlib
import json
import os
import re
import sys
from datetime import date
from functools import wraps
from contextlib import ExitStack
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from operations import NearMissLedger, deterministic_id
from _storage import atomic_text, bounded_blocks, locked, read_text, sync_directory

TOK = re.compile(r"[a-z0-9]+")
EDGES = ("updates", "extends", "derives")
PROFILE_CAPS = {"static": 8, "dynamic": 8}
TOTAL_CORE_CHARS = 65536
PER_FACT_CHARS = 20000
SUPPORTED_MIN = 2.0
PREVIEW_MAX = 3
PREVIEW_CHARS = 240
NEAR_DUP_JACCARD = 0.8


def _tokens(text):
    return set(TOK.findall((text or "").lower()))


def _days_between(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def normalize_future_fact(fact, stated_on):
    """A plan's deadline is not its true-until. True-from is the stated date."""
    result = dict(fact)
    result["valid_from"] = stated_on
    result["valid_until"] = None
    return result


def score_operation(op):
    kind = op.get("op")
    evidence = op.get("evidence") or ""
    after = op.get("after") or ""
    if kind not in ("add", "update", "delete"):
        return {"target": op.get("target"), "op": kind, "verdict": "FAIL", "reason": "unknown operation"}
    if not evidence.strip():
        return {"target": op.get("target"), "op": kind, "verdict": "UNMEASURED",
                "reason": "no evidence; UNMEASURED is never a pass"}
    if kind == "delete":
        ok = bool(re.search(r"successor|tombstone|moved to|replaced by|retired into", evidence, re.I))
        return {"target": op.get("target"), "op": kind,
                "verdict": "PASS" if ok else "FAIL",
                "reason": "deletion names its successor or tombstone" if ok else "deletion names no successor or tombstone"}
    after_tokens, evidence_tokens = _tokens(after), _tokens(evidence)
    grounding = len(after_tokens & evidence_tokens) / len(after_tokens) if after_tokens else 1.0
    if grounding < 0.5:
        return {"target": op.get("target"), "op": kind, "verdict": "FAIL",
                "reason": f"grounding {grounding:.2f} below 0.50"}
    return {"target": op.get("target"), "op": kind, "verdict": "PASS", "reason": f"grounding {grounding:.2f}"}


def score_operations(ops):
    rows = [score_operation(op) for op in ops]
    overall = "PASS"
    if any(row["verdict"] in ("FAIL", "UNMEASURED") for row in rows):
        overall = "FAIL"
    elif any(row["verdict"] == "WARN" for row in rows):
        overall = "WARN"
    return {"operations": rows, "overall": overall}


def _transaction(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with locked(self.lock_path):
            self._recover()
            return method(self, *args, **kwargs)
    return wrapped


class MemoryStore:
    def __init__(self, root):
        root = str(Path(root).resolve())
        self.root = root
        self.lock_path = os.path.join(root, ".memory")
        self.journal_path = os.path.join(root, ".pending-transaction.json")
        self.facts_path = os.path.join(root, "facts.jsonl")
        self.profile_path = os.path.join(root, "profile.json")
        self.retrievals_path = os.path.join(root, "retrievals.jsonl")

    def _recover(self):
        if not os.path.lexists(self.journal_path):
            return
        journal = json.loads(read_text(self.journal_path))
        if journal.get("schema_version") != 1 or not isinstance(journal.get("writes"), list):
            raise ValueError("invalid memory transaction journal; repair before reading")
        paths = set()
        for row in journal["writes"]:
            if not isinstance(row, dict) or not all(isinstance(row.get(k), str) for k in ("path", "text", "sha256")):
                raise ValueError("invalid journal write")
            target = Path(row["path"])
            if not target.is_absolute() or target in paths or target == Path(self.journal_path):
                raise ValueError("invalid journal destination")
            paths.add(target)
            if hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != row["sha256"]:
                raise ValueError("journal replacement hash mismatch")
        # The journal belongs to the trusted host store. Its optional external
        # index destination is the exact path explicitly supplied at erasure.
        # All replacements were preflighted before the commit record persisted.
        for row in journal["writes"]:
            atomic_text(row["path"], row["text"])
        os.unlink(self.journal_path)
        sync_directory(self.root)

    def _commit(self, replacements):
        writes = []
        for path, text in replacements.items():
            target = Path(path).absolute()
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ValueError("memory transaction target is not a regular file")
            writes.append({"path": str(target), "text": text,
                           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
        if not writes:
            return
        # Commit point. Failure after this write leaves a recoverable operation;
        # no subsequent API call exposes a partially applied view.
        self._write_json(self.journal_path, {"schema_version": 1, "writes": writes})
        self._recover()

    @_transaction
    def recover(self):
        """Complete a committed interrupted operation; no external effect runs."""
        return {"recovered": True, "pending_transaction": False}

    @_transaction
    def initialize(self):
        os.makedirs(self.root, exist_ok=True, mode=0o700)
        replacements = {}
        for path, content in ((self.facts_path, ""), (self.profile_path, json.dumps({"static": [], "dynamic": []})),
                              (self.retrievals_path, "")):
            if not os.path.lexists(path):
                replacements[path] = content
            else:
                read_text(path)  # Refuse redirected/nonregular existing state.
        self._commit(replacements)
        return self

    @staticmethod
    def _write_json(path, data):
        atomic_text(path, json.dumps(data, indent=1, sort_keys=True))

    def _read_facts(self):
        if not os.path.lexists(self.facts_path):
            return []
        return [json.loads(line) for line in read_text(self.facts_path).splitlines() if line.strip()]

    def _write_facts(self, facts):
        errors = self._validate_facts(facts)
        if errors:
            raise ValueError(f"memory transaction blocked: {errors}")
        if {fact["id"] for fact in facts} & self._tombstones():
            raise ValueError("forgotten fact id cannot be resurrected")
        atomic_text(self.facts_path, "".join(json.dumps(f, sort_keys=True) + "\n" for f in facts))

    @staticmethod
    def _validate_facts(facts):
        errors = []
        total = 0
        seen = set()
        for fact in facts:
            if not isinstance(fact, dict):
                errors.append("fact must be an object")
                continue
            fid = fact.get("id")
            if not isinstance(fid, str) or not fid:
                errors.append("fact ID must be a nonempty string")
                continue
            if not isinstance(fact.get("text"), str):
                errors.append(f"{fid}: text must be a string")
                continue
            for stamp in ("valid_from", "valid_until", "learned_on"):
                if fact.get(stamp) is not None:
                    try:
                        date.fromisoformat(fact[stamp])
                    except (TypeError, ValueError):
                        errors.append(f"{fid}: {stamp} must be an ISO date")
            if fact.get("valid_from") and fact.get("valid_until") and str(fact["valid_until"]) < str(fact["valid_from"]):
                errors.append(f"{fid}: validity interval is reversed")
            for field in ("links", "entities"):
                if field in fact and (not isinstance(fact[field], list) or any(not isinstance(x, str) for x in fact[field])):
                    errors.append(f"{fid}: {field} must be a string array")
            if not fid:
                errors.append("fact without id")
            elif fid in seen:
                errors.append(f"duplicate fact id {fid}")
            seen.add(fid)
            text = fact.get("text", "")
            total += len(text)
            if len(text) > PER_FACT_CHARS:
                errors.append(f"{fid}: fact over per-file budget")
            words = len(text.split())
            if fact.get("kind", "fact") == "fact" and not 15 <= words <= 80:
                errors.append(f"{fid}: extracted facts must be self-contained (15 to 80 words)")
            if fact.get("edge") and fact["edge"] not in EDGES:
                errors.append(f"{fid}: unknown edge {fact['edge']}")
            if fact.get("inferred") and fact.get("review") not in ("pending", "approved"):
                errors.append(f"{fid}: inferred fact must be pending or approved")
        if total > TOTAL_CORE_CHARS:
            errors.append(f"total core characters {total} exceeds {TOTAL_CORE_CHARS}")
        return errors

    @_transaction
    def validate_store(self):
        return self._validate_facts(self._read_facts())

    @_transaction
    def add_profile_fact(self, kind, bucket, text, source_fact_id=None):
        if kind not in PROFILE_CAPS:
            raise ValueError("profile kind must be static or dynamic")
        profile = json.loads(read_text(self.profile_path))
        if len(profile[kind]) >= PROFILE_CAPS[kind]:
            raise ValueError(f"profile cap reached: {kind} holds at most {PROFILE_CAPS[kind]} facts")
        row = {"bucket": bucket, "text": text}
        if source_fact_id is not None:
            if source_fact_id not in self._fact_map():
                raise ValueError("profile source_fact_id must reference a present fact")
            row["source_fact_id"] = source_fact_id
        profile[kind].append(row)
        self._write_json(self.profile_path, profile)
        return profile

    @_transaction
    def profile(self):
        return json.loads(read_text(self.profile_path))

    @_transaction
    def promote_session_lesson(self, lesson, accepted, reviewer, on_date):
        """The named promotion gate from working memory to permanent memory."""
        if accepted is not True:
            raise ValueError("only accepted lessons cross into permanent memory")
        fact = dict(lesson)
        fact.update(status="current", learned_on=on_date,
                    provenance={"promoted_by": reviewer, "promotion": "session-lesson",
                                "accepted": True, "date": on_date})
        return self.add_fact(fact)

    @classmethod
    def migrate_from(cls, source_root, target_root, replace=False):
        """Copy one consistent store snapshot, retaining erasure prohibitions."""
        source, target = cls(source_root), cls(target_root)
        if source.root == target.root:
            raise ValueError("source and target must be different stores")
        target.initialize()
        with ExitStack() as stack:
            for store in sorted((source, target), key=lambda x: x.root):
                stack.enter_context(locked(store.lock_path))
                store._recover()
            if not replace and (target._read_facts() or any(target.profile().values())):
                raise ValueError("target store is nonempty; explicit replace=True is required")
            facts = source._read_facts()
            errors = source._validate_facts(facts)
            if errors:
                raise ValueError(f"invalid source memory: {errors}")
            tombs = source._tombstone_rows() + target._tombstone_rows()
            tombs = list({row["id"]: row for row in tombs}.values())
            if {f["id"] for f in facts} & {r["id"] for r in tombs}:
                raise ValueError("migration would resurrect a forgotten fact")
            replacements = {target.facts_path: "".join(json.dumps(f, sort_keys=True) + "\n" for f in facts),
                            target.profile_path: json.dumps(source.profile()),
                            target.retrievals_path: read_text(source.retrievals_path),
                            os.path.join(target.root, "erasure", "tombstones.jsonl"):
                                "".join(json.dumps(r, sort_keys=True) + "\n" for r in tombs)}
            for receipt in Path(source.root, "erasure").glob("erasure-*.json"):
                destination = Path(target.root, "erasure", receipt.name)
                content = read_text(receipt)
                if destination.exists() and read_text(destination) != content:
                    raise ValueError("migration receipt name conflict; preserve both stores")
                replacements[str(destination)] = content
            target._commit(replacements)
            retrievable = sum(any(hit["id"] == fact["id"] for hit in target.search(fact["id"])) for fact in facts)
            return {"facts": len(facts), "retrievable": retrievable, "errors": target.validate_store(),
                    "erasure_tombstones_preserved": len(tombs)}

    @_transaction
    def add_fact(self, fact):
        errors = self._validate_facts([fact])
        if errors:
            raise ValueError(f"invalid memory fact: {errors}")
        if fact.get("id") in self._tombstones():
            raise ValueError("forgotten fact id cannot be resurrected")
        facts = self._read_facts()
        if any(existing["id"] == fact.get("id") for existing in facts):
            raise ValueError(f"fact id {fact.get('id')} already exists")
        facts.append(dict(fact))
        self._write_facts(facts)
        return fact["id"]

    @_transaction
    def list_facts(self):
        return self._read_facts()

    def _fact_map(self, facts=None):
        return {fact["id"]: fact for fact in (facts if facts is not None else self._read_facts())}

    @_transaction
    def apply_edge(self, new_id, target_id, edge, on_date):
        if new_id == target_id:
            raise ValueError("a fact cannot supersede itself")
        if edge not in EDGES:
            raise ValueError(f"edge must be one of {EDGES}")
        facts = self._read_facts()
        by_id = self._fact_map(facts)
        if new_id not in by_id or target_id not in by_id:
            raise ValueError("both edge endpoints must exist")
        new, target = by_id[new_id], by_id[target_id]
        new.update(edge=edge, supersedes=target_id,
                   learned_on=new.get("learned_on", on_date))
        if edge == "updates":
            if target.get("status") == "superseded":
                raise ValueError("target is already superseded")
            date.fromisoformat(on_date)
            effective_from = max(new.get("valid_from") or on_date, on_date)
            date.fromisoformat(effective_from)
            new.update(status="current", valid_from=effective_from)
            # Linking an already dated future successor must not create an
            # artificial gap at today's review date, nor extend a predecessor
            # beyond an independently known expiry.
            target.update(status="superseded", valid_until=min(
                target.get("valid_until") or effective_from, effective_from))
        elif edge == "derives":
            new.update(inferred=True, review=new.get("review", "pending"))
        self._write_facts(facts)
        return {"new": new_id, "target": target_id, "edge": edge}

    def _support_counts(self, facts):
        counts = {fact["id"]: 0 for fact in facts}
        for fact in facts:
            target = fact.get("supersedes")
            if target in counts:
                counts[target] += 1
            for linked in fact.get("links", []):
                if linked in counts:
                    counts[linked] += 1
        return counts

    @_transaction
    def review_queue(self):
        facts = self._read_facts()
        support = self._support_counts(facts)
        pending = [{"id": f["id"], "support": support[f["id"]]} for f in facts
                   if f.get("review") == "pending"]
        return sorted(pending, key=lambda row: (-row["support"], row["id"]))

    @_transaction
    def review(self, fact_id, decision, on_date):
        if decision not in ("approve", "decline"):
            raise ValueError("review decision must be approve or decline")
        if decision == "decline":
            return {"id": fact_id, "decision": decision,
                    "forget": self.forget_by_id([fact_id], on_date)}
        facts = self._read_facts()
        by_id = self._fact_map(facts)
        if fact_id not in by_id:
            raise ValueError("fact not found")
        by_id[fact_id]["review"] = "approved"
        self._write_facts(facts)
        return {"id": fact_id, "decision": decision}

    @_transaction
    def propose_correction(self, target_id, new_text, on_date):
        facts = self._read_facts()
        if target_id not in self._fact_map(facts):
            raise ValueError("correction target not found")
        successor_id = deterministic_id(["correction", target_id, new_text, on_date])[:16]
        successor = {"id": successor_id, "text": new_text, "bucket": "corrections",
                     "entities": [], "status": "proposed", "edge": "updates",
                     "supersedes": target_id, "inferred": False, "review": "not_required",
                     "valid_from": on_date, "valid_until": None, "learned_on": on_date}
        facts.append(successor)
        self._write_facts(facts)
        return successor_id

    @_transaction
    def apply_correction(self, successor_id, on_date):
        facts = self._read_facts()
        by_id = self._fact_map(facts)
        successor = by_id.get(successor_id)
        if not successor or successor.get("status") != "proposed":
            raise ValueError("successor is not a proposed correction")
        target = by_id.get(successor.get("supersedes"))
        if not target:
            raise ValueError("correction target not found")
        if target.get("status") == "superseded":
            raise ValueError("correction target is already superseded")
        successor.update(status="current", valid_from=on_date)
        target.update(status="superseded", valid_until=target.get("valid_until") or on_date)
        self._write_facts(facts)
        return {"applied": successor_id, "superseded": target["id"]}

    @_transaction
    def search(self, query, top_n=20, as_of=None):
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
            raise ValueError("top_n must be a positive integer")
        reference = date.fromisoformat(as_of) if as_of is not None else date.today()
        def visible(fact):
            if fact.get("status") == "proposed" or fact.get("opt_out_search"):
                return False
            if fact.get("status") == "superseded" and not fact.get("valid_until"):
                return False
            start, end = fact.get("valid_from"), fact.get("valid_until")
            return ((not start or date.fromisoformat(start) <= reference)
                    and (not end or reference < date.fromisoformat(end)))
        facts = self._read_facts()
        q_tokens = _tokens(query)
        q_lower = query.lower()
        entity_counts = {}
        for fact in facts:
            for entity in fact.get("entities", []):
                entity_counts[entity.lower()] = entity_counts.get(entity.lower(), 0) + 1
        hits = []
        for fact in facts:
            if not visible(fact):
                continue
            tokens = _tokens(fact.get("text", "") + " " + fact.get("id", ""))
            keyword = len(q_tokens & tokens)
            semantic_proxy = keyword / max(len(q_tokens), 1)
            matched_entities = [e for e in fact.get("entities", []) if e.lower() in q_lower]
            entity_boost = min(0.5, 0.25 * len(matched_entities))
            if entity_counts.get(matched_entities[0].lower(), 0) > 10 if matched_entities else False:
                entity_boost *= 0.5  # hub penalty
            score = keyword + 0.6 * semantic_proxy + entity_boost
            if score > 0:
                hits.append({"id": fact["id"], "score": round(score, 3), "via": "ranked",
                             "inferred": bool(fact.get("inferred") and fact.get("review") != "approved"),
                             "components": {"keyword": keyword,
                                            "semantic_proxy": round(semantic_proxy, 3),
                                            "entity": round(entity_boost, 3)},
                             "text": fact["text"]})
        hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
        ranked = hits[:top_n]
        seen = {hit["id"] for hit in ranked}
        by_id = self._fact_map(facts)
        frontier = [(hit["id"], 0) for hit in ranked]
        while frontier:
            fid, depth = frontier.pop(0)
            if depth >= 3:
                continue
            for link in by_id[fid].get("links", []):
                if link in by_id and link not in seen and visible(by_id[link]):
                    seen.add(link)
                    ranked.append({"id": link, "score": 0.0, "via": "thread", "thread_depth": depth + 1,
                                   "inferred": bool(by_id[link].get("inferred") and by_id[link].get("review") != "approved"), "text": by_id[link]["text"]})
                    frontier.append((link, depth + 1))
        return ranked

    @_transaction
    def recall(self, query, top_n=20, as_of=None):
        hits = self.search(query, top_n, as_of=as_of)
        ranked = [hit for hit in hits if hit["via"] == "ranked"]
        if not ranked:
            return {"tier": "not present", "confidence": 0.0, "hits": [], "previews": [],
                    "exploration_rounds": 0, "store_state": "ready" if self._read_facts() else "empty"}
        best = ranked[0]["score"]
        confidence = round(min(1.0, best / 4.0), 3)
        if best >= SUPPORTED_MIN:
            self.record_retrieval([hit["id"] for hit in ranked], date.today().isoformat())
            return {"tier": "supported", "confidence": confidence, "hits": hits, "previews": [],
                    "exploration_rounds": 0, "store_state": "ready"}
        rounds = 0
        if confidence < 0.5:
            rounds = 1
            hits = self.search(query, top_n * 2, as_of=as_of)
            ranked = [hit for hit in hits if hit["via"] == "ranked"]
        previews = [{"id": hit["id"], "preview": hit["text"][:PREVIEW_CHARS],
                     "note": "related only; not claimed relevant"} for hit in ranked[:PREVIEW_MAX]]
        return {"tier": "closest-only", "confidence": confidence, "hits": [], "previews": previews,
                "exploration_rounds": rounds, "store_state": "ready"}

    @_transaction
    def build_context(self, query, budget_chars=8000, as_of=None):
        hits = self.search(query, as_of=as_of)
        return bounded_blocks([(hit["id"], f"[{hit['id']}{'; inferred, review pending' if hit['inferred'] else ''}]\n{hit['text']}")
                               for hit in hits], budget_chars)

    @_transaction
    def record_retrieval(self, ids, on_date):
        date.fromisoformat(on_date)
        ids = list(ids)
        known = {f["id"] for f in self._read_facts()}
        if any(fid not in known for fid in ids):
            raise ValueError("retrieval must reference present facts")
        previous = read_text(self.retrievals_path)
        atomic_text(self.retrievals_path, previous + "".join(json.dumps({"id": fid, "date": on_date}) + "\n" for fid in ids))

    @_transaction
    def demotion_candidates(self, reference_date, days=14):
        date.fromisoformat(reference_date)
        if isinstance(days, bool) or not isinstance(days, int) or days < 0:
            raise ValueError("days must be a nonnegative integer")
        retrieved = set()
        if os.path.isfile(self.retrievals_path):
            for line in read_text(self.retrievals_path).splitlines():
                if line.strip():
                    row = json.loads(line)
                    if 0 <= _days_between(row["date"], reference_date) <= days:
                        retrieved.add(row["id"])
        return [{"id": f["id"], "reason": "standing fact with zero retrievals in the window; review, never silent deletion"}
                for f in self._read_facts() if f.get("status") == "current" and f["id"] not in retrieved]

    def _tombstone_rows(self):
        path = os.path.join(self.root, "erasure", "tombstones.jsonl")
        return [json.loads(line) for line in read_text(path).splitlines() if line.strip()] if os.path.lexists(path) else []

    def _tombstones(self):
        return {row["id"] for row in self._tombstone_rows()}

    @_transaction
    def forget_by_id(self, ids, on_date, index_path=None):
        date.fromisoformat(on_date)
        ids = list(dict.fromkeys(ids))
        if any(not isinstance(fid, str) or not fid for fid in ids):
            raise ValueError("forgetting requires nonempty exact string IDs")
        facts = self._read_facts()
        by_id, gone = self._fact_map(facts), self._tombstones()
        results = {fid: "forgotten" if fid in by_id else "already_forgotten" if fid in gone else "not_found" for fid in ids}
        removed = [fid for fid in ids if fid in by_id]
        if not removed:
            return results
        removed_ids = set(removed)
        replacements, index_cleaned = {}, []
        if index_path is not None:
            if Path(index_path).is_symlink():
                raise ValueError("derived index must not be a symlink")
            index_path = str(Path(index_path).resolve())
            reserved = {self.facts_path, self.profile_path, self.retrievals_path, self.journal_path}
            if index_path in reserved or Path(index_path).is_relative_to(Path(self.root, "erasure")):
                raise ValueError("derived index must not alias canonical memory state")
            index = json.loads(read_text(index_path))
            if not isinstance(index, dict) or any(not isinstance(v, str) for v in index.values()):
                raise ValueError("erasure index must be an object mapping strings to fact IDs")
            kept = {k: v for k, v in index.items() if k not in removed_ids and v not in removed_ids}
            # Receipts retain only a count, not private index keys/content.
            index_cleaned = sorted(set(index) - set(kept))
            replacements[index_path] = json.dumps(kept, sort_keys=True)
        retained = []
        for fact in facts:
            if fact["id"] in removed_ids:
                continue
            fact = dict(fact)
            if "links" in fact:
                fact["links"] = [fid for fid in fact["links"] if fid not in removed_ids]
            if fact.get("supersedes") in removed_ids:
                fact.pop("supersedes", None)
                fact.pop("edge", None)
            retained.append(fact)
        errors = self._validate_facts(retained)
        if errors:
            raise ValueError(f"invalid retained memory: {errors}")
        replacements[self.facts_path] = "".join(json.dumps(f, sort_keys=True) + "\n" for f in retained)
        retrievals = [json.loads(line) for line in read_text(self.retrievals_path).splitlines() if line.strip()]
        replacements[self.retrievals_path] = "".join(json.dumps(row, sort_keys=True) + "\n" for row in retrievals if row["id"] not in removed_ids)
        profile = self.profile()
        for kind in PROFILE_CAPS:
            profile[kind] = [row for row in profile[kind] if row.get("id") not in removed_ids and row.get("source_fact_id") not in removed_ids]
        replacements[self.profile_path] = json.dumps(profile, sort_keys=True)
        receipt_name = f"erasure-{on_date}-{deterministic_id([on_date] + sorted(removed))[:16]}.json"
        receipt = {"date": on_date, "results": {fid: results[fid] for fid in removed},
                   "index_cleaned_count": len(index_cleaned), "scope": "exact IDs, linked references, retrieval records and linked profile facts; unlinked text and external backups are not inferred"}
        replacements[os.path.join(self.root, "erasure", receipt_name)] = json.dumps(receipt, sort_keys=True)
        tombstones = self._tombstone_rows() + [{"id": fid, "date": on_date, "receipt": receipt_name} for fid in removed]
        replacements[os.path.join(self.root, "erasure", "tombstones.jsonl")] = "".join(json.dumps(row, sort_keys=True) + "\n" for row in tombstones)
        self._commit(replacements)
        results["_receipt"] = os.path.join(self.root, "erasure", receipt_name)
        return results

    @_transaction
    def semantic_forget_preview(self, query):
        return sorted({hit["id"] for hit in self.search(query) if hit["via"] == "ranked"})

    @_transaction
    def forget_semantic(self, preview_ids, on_date, index_path=None):
        """Delete exactly the previewed IDs. The match is never re-run here."""
        return self.forget_by_id(list(preview_ids), on_date, index_path=index_path)

    @_transaction
    def audit_corpus(self, near_miss_path=None):
        facts = self._read_facts()
        hashes, tokens, classes = {}, {}, {}
        for fact in facts:
            hashes[fact["id"]] = hashlib.sha256(fact["text"].encode()).hexdigest()
            tokens[fact["id"]] = _tokens(fact["text"])
            classes[fact["id"]] = "clean"
            if not fact.get("id") or not fact.get("text"):
                classes[fact["id"]] = "malformed"
        ids = sorted(hashes)
        parent = {fid: fid for fid in ids}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if hashes[a] == hashes[b] or (tokens[a] and tokens[b] and
                        len(tokens[a] & tokens[b]) / len(tokens[a] | tokens[b]) >= NEAR_DUP_JACCARD):
                    union(a, b)
        clusters = {}
        for fid in ids:
            clusters.setdefault(find(fid), []).append(fid)
        loop_clusters = []
        for members in clusters.values():
            if len(members) < 2:
                continue
            kind = "feedback_loop" if len(members) >= 3 else "duplicate"
            if kind == "feedback_loop":
                loop_clusters.append(sorted(members))
            for fid in sorted(members)[1:]:
                if classes[fid] == "clean":
                    classes[fid] = kind
        counts = {name: sum(1 for value in classes.values() if value == name)
                  for name in ("clean", "duplicate", "feedback_loop", "malformed")}
        total = len(facts)
        junk = total - counts["clean"]
        if near_miss_path and NearMissLedger is not None:
            ledger = NearMissLedger(near_miss_path).load()
            by_id = self._fact_map(facts)
            for fid, kind in classes.items():
                if kind != "clean":
                    ledger.record(f"memory-corpus:{fid}", "other", by_id[fid]["text"])
        return {"total": total, "counts": counts,
                "junk_rate": round(junk / total, 4) if total else 0.0,
                "feedback_loop_clusters": loop_clusters, "classification": classes}


if __name__ == "__main__":
    print(__doc__)
