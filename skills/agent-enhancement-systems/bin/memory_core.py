#!/usr/bin/env python3
"""Disciplines 4 and 5: profile-plus-graph memory and honest recall.

The store is one directory owned by the adopting host:

    <store>/profile.json   standing facts, capped at 8 static + 8 dynamic
    <store>/facts.jsonl    dynamic facts with typed edges and validity stamps
    <store>/retrievals.jsonl
    <store>/erasure/       receipts and tombstones written by forgetting

No second store is created. Facts are JSON objects so a host can inspect,
diff, and migrate them without a database service. Writes that change two
facts together stage the full replacement in memory, validate it, then write
once. Standard library only.
"""
import hashlib
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from operations import NearMissLedger, deterministic_id
from _storage import atomic_text, bounded_blocks

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


class MemoryStore:
    def __init__(self, root):
        self.root = root
        self.facts_path = os.path.join(root, "facts.jsonl")
        self.profile_path = os.path.join(root, "profile.json")
        self.retrievals_path = os.path.join(root, "retrievals.jsonl")

    def initialize(self):
        os.makedirs(self.root, exist_ok=True)
        if not os.path.isfile(self.facts_path):
            with open(self.facts_path, "w", encoding="utf-8"):
                pass
        if not os.path.isfile(self.profile_path):
            self._write_json(self.profile_path, {"static": [], "dynamic": []})
        if not os.path.isfile(self.retrievals_path):
            with open(self.retrievals_path, "w", encoding="utf-8"):
                pass
        return self

    @staticmethod
    def _write_json(path, data):
        atomic_text(path, json.dumps(data, indent=1, sort_keys=True))

    def _read_facts(self):
        if not os.path.isfile(self.facts_path):
            return []
        with open(self.facts_path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _write_facts(self, facts):
        errors = self._validate_facts(facts)
        if errors:
            raise ValueError(f"memory transaction blocked: {errors}")
        atomic_text(self.facts_path, "".join(json.dumps(f, sort_keys=True) + "\n" for f in facts))

    @staticmethod
    def _validate_facts(facts):
        errors = []
        total = 0
        seen = set()
        for fact in facts:
            fid = fact.get("id")
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

    def validate_store(self):
        return self._validate_facts(self._read_facts())

    def add_profile_fact(self, kind, bucket, text):
        if kind not in PROFILE_CAPS:
            raise ValueError("profile kind must be static or dynamic")
        with open(self.profile_path, encoding="utf-8") as handle:
            profile = json.load(handle)
        if len(profile[kind]) >= PROFILE_CAPS[kind]:
            raise ValueError(f"profile cap reached: {kind} holds at most {PROFILE_CAPS[kind]} facts")
        profile[kind].append({"bucket": bucket, "text": text})
        self._write_json(self.profile_path, profile)
        return profile

    def profile(self):
        with open(self.profile_path, encoding="utf-8") as handle:
            return json.load(handle)

    def promote_session_lesson(self, lesson, accepted, reviewer, on_date):
        """The named promotion gate from working memory to permanent memory."""
        if not accepted:
            raise ValueError("only accepted lessons cross into permanent memory")
        fact = dict(lesson)
        fact.update(status="current", learned_on=on_date,
                    provenance={"promoted_by": reviewer, "promotion": "session-lesson",
                                "accepted": True, "date": on_date})
        return self.add_fact(fact)

    @classmethod
    def migrate_from(cls, source_root, target_root, replace=False):
        """Copy a prior-format store, validate it, and prove retrievability."""
        source = cls(source_root)
        target = cls(target_root).initialize()
        if not replace and (target._read_facts() or any(target.profile().values())):
            raise ValueError("target store is nonempty; explicit replace=True is required")
        facts = source._read_facts()
        target._write_facts(facts)
        profile = source.profile()
        target._write_json(target.profile_path, profile)
        retrievable = 0
        for fact in facts:
            if any(hit["id"] == fact["id"] for hit in target.search(fact["id"])):
                retrievable += 1
        return {"facts": len(facts), "retrievable": retrievable,
                "errors": target.validate_store()}

    def add_fact(self, fact):
        if fact.get("id") in self._tombstones():
            raise ValueError("forgotten fact id cannot be resurrected")
        facts = self._read_facts()
        if any(existing["id"] == fact.get("id") for existing in facts):
            raise ValueError(f"fact id {fact.get('id')} already exists")
        facts.append(dict(fact))
        self._write_facts(facts)
        return fact["id"]

    def list_facts(self):
        return self._read_facts()

    def _fact_map(self, facts=None):
        return {fact["id"]: fact for fact in (facts if facts is not None else self._read_facts())}

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
            new.update(status="current", valid_from=new.get("valid_from", on_date))
            target.update(status="superseded", valid_until=target.get("valid_until") or on_date)
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

    def review_queue(self):
        facts = self._read_facts()
        support = self._support_counts(facts)
        pending = [{"id": f["id"], "support": support[f["id"]]} for f in facts
                   if f.get("review") == "pending"]
        return sorted(pending, key=lambda row: (-row["support"], row["id"]))

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

    def search(self, query, top_n=20):
        facts = self._read_facts()
        q_tokens = _tokens(query)
        q_lower = query.lower()
        entity_counts = {}
        for fact in facts:
            for entity in fact.get("entities", []):
                entity_counts[entity.lower()] = entity_counts.get(entity.lower(), 0) + 1
        hits = []
        for fact in facts:
            if fact.get("status") in ("proposed", "superseded") or fact.get("opt_out_search"):
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
                if link in by_id and link not in seen and by_id[link].get("status") not in ("proposed", "superseded") and not by_id[link].get("opt_out_search"):
                    seen.add(link)
                    ranked.append({"id": link, "score": 0.0, "via": "thread", "thread_depth": depth + 1,
                                   "inferred": bool(by_id[link].get("inferred") and by_id[link].get("review") != "approved"), "text": by_id[link]["text"]})
                    frontier.append((link, depth + 1))
        return ranked

    def recall(self, query, top_n=20):
        hits = self.search(query, top_n)
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
            hits = self.search(query, top_n * 2)
            ranked = [hit for hit in hits if hit["via"] == "ranked"]
        previews = [{"id": hit["id"], "preview": hit["text"][:PREVIEW_CHARS],
                     "note": "related only; not claimed relevant"} for hit in ranked[:PREVIEW_MAX]]
        return {"tier": "closest-only", "confidence": confidence, "hits": [], "previews": previews,
                "exploration_rounds": rounds, "store_state": "ready"}

    def build_context(self, query, budget_chars=8000):
        hits = self.search(query)
        return bounded_blocks([(hit["id"], f"[{hit['id']}]\n{hit['text']}") for hit in hits], budget_chars)

    def record_retrieval(self, ids, on_date):
        with open(self.retrievals_path, "a", encoding="utf-8") as handle:
            for fid in ids:
                handle.write(json.dumps({"id": fid, "date": on_date}) + "\n")

    def demotion_candidates(self, reference_date, days=14):
        retrieved = set()
        if os.path.isfile(self.retrievals_path):
            with open(self.retrievals_path, encoding="utf-8") as handle:
                lines = handle.readlines()
            for line in lines:
                if not line.strip():
                    continue
                row = json.loads(line)
                if _days_between(row["date"], reference_date) <= days:
                    retrieved.add(row["id"])
        return [{"id": f["id"], "reason": "standing fact with zero retrievals in the window; review, never silent deletion"}
                for f in self._read_facts() if f.get("status") == "current" and f["id"] not in retrieved]

    def _tombstones(self):
        path = os.path.join(self.root, "erasure", "tombstones.jsonl")
        out = set()
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                lines = handle.readlines()
            for line in lines:
                if line.strip():
                    out.add(json.loads(line)["id"])
        return out

    def forget_by_id(self, ids, on_date, index_path=None):
        facts = self._read_facts()
        by_id = self._fact_map(facts)
        gone = self._tombstones()
        results, removed = {}, []
        for fid in ids:
            if fid in by_id:
                results[fid] = "forgotten"; removed.append(fid)
            elif fid in gone:
                results[fid] = "already_forgotten"
            else:
                results[fid] = "not_found"
        if removed:
            index_cleaned = []
            kept = None
            if index_path and os.path.isfile(index_path):
                with open(index_path, encoding="utf-8") as handle:
                    index = json.load(handle)
                if not isinstance(index, dict) or any(not isinstance(v, str) for v in index.values()):
                    raise ValueError("erasure index must be an object mapping strings to fact IDs")
                removed_ids = set(removed)
                kept = {k: v for k, v in index.items() if k not in removed_ids and v not in removed_ids}
                index_cleaned = sorted(set(index) - set(kept))
            self._write_facts([f for f in facts if f["id"] not in removed])
            if kept is not None:
                self._write_json(index_path, kept)
            erasure = os.path.join(self.root, "erasure")
            os.makedirs(erasure, exist_ok=True)
            receipt = {"date": on_date, "results": {fid: results[fid] for fid in removed},
                       "index_cleaned": index_cleaned}
            receipt_name = f"erasure-{on_date}-{deterministic_id([on_date] + removed)[:8]}.json"
            with open(os.path.join(erasure, receipt_name), "w", encoding="utf-8") as handle:
                json.dump(receipt, handle, indent=1)
            with open(os.path.join(erasure, "tombstones.jsonl"), "a", encoding="utf-8") as handle:
                for fid in removed:
                    handle.write(json.dumps({"id": fid, "date": on_date, "receipt": receipt_name}) + "\n")
            results["_receipt"] = os.path.join(erasure, receipt_name)
        return results

    def semantic_forget_preview(self, query):
        return sorted({hit["id"] for hit in self.search(query) if hit["via"] == "ranked"})

    def forget_semantic(self, preview_ids, on_date, index_path=None):
        """Delete exactly the previewed IDs. The match is never re-run here."""
        return self.forget_by_id(list(preview_ids), on_date, index_path=index_path)

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
