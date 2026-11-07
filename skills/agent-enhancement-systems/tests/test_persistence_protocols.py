"""Independent crash, concurrency and stale-generation contracts.

All child processes run explicit fixture code over temporary directories;
none executes a broker, service, model or external transport.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import select
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

BIN = Path(__file__).resolve().parents[1] / "bin"
sys.path.insert(0, str(BIN))
import _storage
import authority
import freshness
import instincts
import memory_core
import operations
import proactive
import reliability
import skill_lab
import why


def fact(identifier, text="fixture", **extra):
    return {"id": identifier, "kind": "note", "text": text, "status": "current", **extra}


class MemoryTransactions(unittest.TestCase):
    def test_concurrent_process_writers_retain_every_fact_and_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            script = """
import sys
sys.path.insert(0, sys.argv[1])
from memory_core import MemoryStore
store = MemoryStore(sys.argv[2]).initialize()
for n in range(8):
    store.add_fact({'id': sys.argv[3] + '-' + str(n), 'kind': 'note', 'text': 'fixture', 'status': 'current'})
"""
            workers = [subprocess.Popen([sys.executable, "-B", "-c", script, str(BIN), directory, str(i)],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(6)]
            for worker in workers:
                _, error = worker.communicate(timeout=15)
                self.assertEqual(worker.returncode, 0, error.decode())
            store = memory_core.MemoryStore(directory)
            self.assertEqual({f["id"] for f in store.list_facts()}, {f"{i}-{n}" for i in range(6) for n in range(8)})
            self.assertEqual(store.validate_store(), [])

    def test_process_death_after_erasure_commit_recovers_before_read_and_blocks_resurrection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            private = fact("erased-id", "private fixture payload")
            store.add_fact(private)
            store.add_fact(fact("retained", "retained fixture", links=["erased-id"]))
            store.record_retrieval(["erased-id", "retained"], "2026-11-07")
            store.add_profile_fact("static", "fixture", "linked private profile", source_fact_id="erased-id")
            store.add_profile_fact("static", "fixture", "unlinked standing fact")
            index = Path(directory) / "index.json"
            index.write_text(json.dumps({"private index key": "erased-id", "safe": "retained"}))
            script = """
import os, sys
sys.path.insert(0, sys.argv[1])
import memory_core
original = memory_core.atomic_text
def interrupted(path, text):
    original(path, text)
    if str(path).endswith('/facts.jsonl'):
        os._exit(72)
memory_core.atomic_text = interrupted
memory_core.MemoryStore(sys.argv[2]).forget_by_id(['erased-id'], '2026-11-07', sys.argv[3])
"""
            killed = subprocess.run([sys.executable, "-B", "-c", script, str(BIN), directory, str(index)],
                                    capture_output=True, timeout=10)
            self.assertEqual(killed.returncode, 72, killed.stderr.decode())
            journal = Path(directory) / ".pending-transaction.json"
            self.assertTrue(journal.is_file())
            self.assertNotIn("private fixture payload", journal.read_text())
            self.assertNotIn("private index key", journal.read_text())
            reopened = memory_core.MemoryStore(directory)
            self.assertEqual(reopened.list_facts(), [fact("retained", "retained fixture", links=[])])
            self.assertFalse(journal.exists())
            self.assertEqual(json.loads(index.read_text()), {"safe": "retained"})
            self.assertEqual(reopened.profile()["static"], [{"bucket": "fixture", "text": "unlinked standing fact"}])
            self.assertNotIn("erased-id", Path(reopened.retrievals_path).read_text())
            self.assertEqual(reopened.forget_by_id(["erased-id"], "2026-11-07")["erased-id"], "already_forgotten")
            with self.assertRaisesRegex(ValueError, "resurrected"):
                reopened.add_fact(private)

    def test_precommit_failure_preserves_old_state_and_corrupt_journal_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            original = fact("one", "keep until commit")
            store.add_fact(original)
            with patch.object(store, "_write_json", side_effect=OSError("fixture disk failure")):
                with self.assertRaises(OSError):
                    store.forget_by_id(["one"], "2026-11-07")
            self.assertEqual(store.list_facts(), [original])
            Path(store.journal_path).write_text(json.dumps({"schema_version": 1, "writes": [
                {"path": store.facts_path, "text": "", "sha256": "wrong"}]}))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                store.list_facts()
            self.assertIn("keep until commit", Path(store.facts_path).read_text())

    def test_migration_preserves_erasure_and_never_overwrites_target_prohibitions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = memory_core.MemoryStore(Path(directory) / "source").initialize()
            source.add_fact(fact("erased")); source.forget_by_id(["erased"], "2026-11-07")
            source.add_fact(fact("visible", "searchable fixture"))
            target_path = Path(directory) / "target"
            receipt = memory_core.MemoryStore.migrate_from(source.root, target_path)
            self.assertEqual(receipt["erasure_tombstones_preserved"], 1)
            target = memory_core.MemoryStore(target_path)
            with self.assertRaisesRegex(ValueError, "resurrected"):
                target.add_fact(fact("erased"))
            target.forget_by_id(["visible"], "2026-11-07")
            with self.assertRaisesRegex(ValueError, "resurrect"):
                memory_core.MemoryStore.migrate_from(source.root, target.root, replace=True)
            self.assertEqual(target.list_facts(), [])

    def test_temporal_retrieval_and_thread_expansion_use_same_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            store.add_fact(fact("old", "needle old", status="superseded", valid_from="2026-01-01", valid_until="2026-06-01"))
            store.add_fact(fact("current", "needle current", valid_from="2026-06-01", links=["future", "expired"]))
            store.add_fact(fact("future", "future note", valid_from="2099-01-01"))
            store.add_fact(fact("expired", "old note", valid_until="2020-01-01"))
            self.assertEqual([h["id"] for h in store.search("needle", as_of="2026-05-01")], ["old"])
            self.assertEqual([h["id"] for h in store.search("needle", as_of="2026-06-01")], ["current"])
            self.assertEqual([h["id"] for h in store.search("needle")], ["current"])
            with self.assertRaises(ValueError):
                store.add_fact(fact("bad", valid_from="not-date"))
            with self.assertRaises(ValueError):
                store.search("needle", top_n=0)

    def test_future_retrieval_does_not_hide_demotion_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            store.add_fact(fact("one"))
            store.record_retrieval(["one"], "2099-01-01")
            self.assertEqual([x["id"] for x in store.demotion_candidates("2026-11-07")], ["one"])

    def test_dated_successor_transition_uses_effective_date_and_preserves_known_expiry(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            store.add_fact(fact("old", "needle old", valid_from="2020-01-01"))
            store.add_fact(fact("future", "needle future", valid_from="2099-01-01"))
            store.apply_edge("future", "old", "updates", "2026-11-07")
            self.assertEqual([h["id"] for h in store.search("needle", as_of="2026-11-07")], ["old"])
            self.assertEqual([h["id"] for h in store.search("needle", as_of="2099-01-01")], ["future"])
            store.add_fact(fact("finite", "bounded predecessor", valid_from="2020-01-01", valid_until="2027-01-01"))
            store.add_fact(fact("later", "bounded successor", valid_from="2099-01-01"))
            store.apply_edge("later", "finite", "updates", "2026-11-07")
            self.assertEqual({f["id"]: f for f in store.list_facts()}["finite"]["valid_until"], "2027-01-01")
            store.add_fact(fact("overlap", "overlap predecessor", valid_until="2099-01-01"))
            store.add_fact(fact("earlier", "overlap successor", valid_from="2027-01-01"))
            store.apply_edge("earlier", "overlap", "updates", "2026-11-07")
            self.assertEqual([h["id"] for h in store.search("overlap", as_of="2027-01-01")], ["earlier"])

    def test_correction_cannot_resurrect_erased_id_and_future_update_preserves_current_fact(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            store.add_fact(fact("one", "needle predecessor"))
            text = "A correction supplies a complete independent statement with enough words to satisfy the stored extraction contract."
            correction = store.propose_correction("one", text, "2026-11-07")
            store.forget_by_id([correction], "2026-11-07")
            with self.assertRaisesRegex(ValueError, "resurrected"):
                store.propose_correction("one", text, "2026-11-07")
            store.add_fact(fact("successor", "needle future"))
            store.apply_edge("successor", "one", "updates", "2099-01-01")
            self.assertEqual([hit["id"] for hit in store.search("needle")], ["one"])
            self.assertEqual([hit["id"] for hit in store.search("needle", as_of="2099-01-01")], ["successor"])
            store.add_fact(fact("inference", "needle uncertain", inferred=True, review="pending"))
            self.assertIn("inferred, review pending", store.build_context("needle")["text"])


class QueueTransactions(unittest.TestCase):
    def test_legacy_active_rows_upgrade_without_losing_generation_or_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "queue.sqlite")
            legacy = sqlite3.connect(path)
            legacy.execute(operations.QUEUE_SCHEMA)
            legacy.execute("INSERT INTO effects(kind,key,payload,generation,state,revision) VALUES(?,?,?,?,'running',?)",
                           ("effect", "legacy", json.dumps({"original": "intent"}), 7, 4))
            legacy.commit()
            legacy.close()
            queue = operations.EffectQueue(path)
            try:
                self.assertEqual(queue.get("effect", "legacy")["generation"], 7)
                retry = queue.reconcile("effect", "legacy", 7, "not_applied", "fixture receiver absent; legacy worker stopped")
                self.assertEqual(retry["generation"], 8)
                self.assertEqual(queue.get("effect", "legacy")["payload"], {"original": "intent"})
                self.assertTrue(queue.complete("effect", "legacy", 8))
                self.assertEqual(queue.enqueue("effect", "legacy", revision=4), "stale")
                self.assertEqual(queue.enqueue("effect", "legacy", revision=5), 9)
            finally:
                queue.close()

    def test_completed_and_cancelled_generations_never_reuse_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "queue.sqlite")
            queue = operations.EffectQueue(path)
            first = queue.enqueue("effect", "one", revision=1)
            old_receipt = queue.issue_receipt("effect", "one", first)
            self.assertFalse(queue.complete("effect", "one", first))
            self.assertTrue(queue.complete("effect", "one", first, old_receipt))
            queue.close()
            queue = operations.EffectQueue(path)
            try:
                self.assertEqual(queue.enqueue("effect", "one", revision=1), "stale")
                second = queue.enqueue("effect", "one", revision=2)
                self.assertGreater(second, first)
                self.assertFalse(queue.complete("effect", "one", first, old_receipt))
                self.assertTrue(queue.cancel("effect", "one", second, "fixture cancelled before claim"))
                third = queue.enqueue("effect", "one", revision=3)
                self.assertGreater(third, second)
                self.assertFalse(queue.complete("effect", "one", second))
                self.assertEqual([x["event"] for x in queue.history("effect", "one")],
                                 ["enqueued", "receipt-issued", "completed", "enqueued", "cancelled", "enqueued"])
            finally:
                queue.close()

    def test_unknown_effect_requires_evidence_then_has_working_recovery_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = operations.EffectQueue(str(Path(directory) / "queue.sqlite"))
            try:
                generation = queue.enqueue("effect", "one", {"value": 1})
                def lost_ack(_):
                    raise TimeoutError("fixture")
                queue.run_next(lost_ack)
                with self.assertRaisesRegex(ValueError, "reconcile"):
                    queue.enqueue("effect", "one", {"value": 2})
                for call in (queue.defer_later, queue.record_rate_limited, queue.fail):
                    self.assertFalse(call("effect", "one", generation))
                self.assertFalse(queue.cancel("effect", "one", generation, "cannot drop uncertain work"))
                with self.assertRaises(ValueError):
                    queue.reconcile("effect", "one", generation, "not_applied", "")
                reconciled = queue.reconcile("effect", "one", generation, "not_applied", "receiver read: absent; old worker stopped")
                self.assertGreater(reconciled["generation"], generation)
                self.assertFalse(queue.complete("effect", "one", generation))
                seen = []
                queue.run_next(lambda item: seen.append(item["payload"]))
                self.assertEqual(seen, [{"value": 1}])
                self.assertTrue(queue.reconcile("effect", "one", reconciled["generation"], "applied", "receiver receipt fixture-1"))
                self.assertIsNone(queue.get("effect", "one"))
                self.assertGreater(queue.enqueue("effect", "one", {"value": 2}), generation)
            finally:
                queue.close()

    def test_terminal_failure_cannot_be_reopened_by_delayed_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = operations.EffectQueue(str(Path(directory) / "queue.sqlite"))
            try:
                generation = queue.enqueue("effect", "one")
                queue.fail("effect", "one", generation, max_attempts=1)
                self.assertFalse(queue.defer_later("effect", "one", generation, 0))
                self.assertFalse(queue.record_rate_limited("effect", "one", generation, 0))
                self.assertFalse(queue.fail("effect", "one", generation, max_attempts=10))
                self.assertIsNone(queue.run_next(lambda _: self.fail("terminal work ran")))
                for value in (float("nan"), float("inf"), -1, True):
                    with self.assertRaises(ValueError):
                        queue.defer_later("effect", "one", generation, value)
            finally:
                queue.close()

    def test_separate_connections_claim_each_due_effect_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "queue.sqlite")
            queue = operations.EffectQueue(path)
            for i in range(12):
                queue.enqueue("effect", str(i))
            queue.close()
            def consume(_):
                local = operations.EffectQueue(path)
                seen = []
                try:
                    def handler(row):
                        seen.append(row["key"])
                        local.complete(row["kind"], row["key"], row["generation"])
                    while local.run_next(handler) is not None:
                        pass
                finally:
                    local.close()
                return seen
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                seen = [x for batch in pool.map(consume, range(4)) for x in batch]
            self.assertCountEqual(seen, [str(i) for i in range(12)])


class OtherPersistenceBoundaries(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, "fork"), "fork ownership applies to POSIX hosts")
    def test_forked_child_cannot_inherit_parent_lock_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            read_fd, write_fd = os.pipe()
            child = None
            try:
                with _storage.locked(Path(directory) / "state"):
                    child = os.fork()
                    if child == 0:
                        try:
                            os.close(read_fd)
                            os.write(write_fd, b"started\n")
                            with _storage.locked(Path(directory) / "state"):
                                os.write(write_fd, b"acquired\n")
                            os._exit(0)
                        except BaseException:
                            os._exit(1)
                    os.close(write_fd)
                    write_fd = None
                    self.assertTrue(select.select([read_fd], [], [], 5)[0])
                    self.assertEqual(os.read(read_fd, 8), b"started\n")
                    self.assertFalse(select.select([read_fd], [], [], 0.1)[0])
                self.assertTrue(select.select([read_fd], [], [], 5)[0])
                self.assertEqual(os.read(read_fd, 9), b"acquired\n")
            finally:
                os.close(read_fd)
                if write_fd is not None:
                    os.close(write_fd)
                if child:
                    _, status = os.waitpid(child, 0)
                    self.assertEqual(os.waitstatus_to_exitcode(status), 0)

    def test_proactive_numeric_contract_blocks_invalid_caps_and_preserves_valid_lanes(self):
        config = {"C_FA": 1, "C_FN": 1, "min_interval": 5,
                  "max_fires_per_window": 2, "mode": "auto", "margin": 0.1}
        self.assertEqual(proactive.decide_lane(config, 0.8, 1.0, now=10)["verdict"], "fire")
        self.assertEqual(proactive.decide_lane(config, 0.8, 1.0, now=10, history=[9])["verdict"], "blocked")
        self.assertEqual(proactive.decide_lane({**config, "mode": "observe"}, 0.8, 1.0, now=10)["verdict"], "would_accept")
        self.assertEqual(proactive.decide_lane(config, 0.45, 1.0, now=10)["verdict"], "slow")
        self.assertEqual(proactive.decide_lane(config, 0.1, 1.0, now=10)["verdict"], "silent")
        for field, value in (("min_interval", float("nan")), ("max_fires_per_window", float("inf")),
                             ("window_s", 0), ("margin", -1), ("margin", True)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                proactive.decide_lane({**config, field: value}, 0.8, 1.0, now=10)
        with self.assertRaises(ValueError):
            proactive.decide_lane(config, True, 1.0, now=10)
        with self.assertRaises(ValueError):
            proactive.decide_lane(config, 0.8, 1.0, now=10, history=[float("nan")])
        self.assertEqual(proactive.tau(1e308, 1e308, 1.0), 0.5)

    def test_eval_contract_requires_actual_booleans_and_accepts_valid_balanced_set(self):
        data = {"reference_solution": "fixture", "isolated_trials": True, "judge_unknown_exit": True,
                "cases": [{"kind": "should"}, {"kind": "should-not"}]}
        self.assertEqual(skill_lab.validate_eval_set(data), [])
        for field in ("isolated_trials", "judge_unknown_exit"):
            for value in ("false", "true", 1, []):
                with self.subTest(field=field, value=value):
                    self.assertTrue(skill_lab.validate_eval_set({**data, field: value}))

    def test_freshness_propagates_real_container_age_and_requires_a_calendar_stamp(self):
        text = ("# Snapshot 2020-01-01\nCurrent cash is 50\n"
                "## Fresh subsection 2026-11-07\nCurrent cash is 60\n"
                "## Older sibling\nCurrent cash is 70\n"
                "# Undated sibling\nCurrent cash is 80 as of today\n")
        findings = freshness.lint_text(text, reference_date="2026-11-07")
        self.assertEqual([(f["code"], f["line"]) for f in findings],
                         [("FRESH-2", 2), ("FRESH-2", 6), ("FRESH-1", 8)])
        invalid = freshness.lint_text("# Snapshot 2026-02-30\nCurrent cash is 1", reference_date="2026-11-07")
        self.assertEqual([(f["code"], f["line"]) for f in invalid], [("FRESH-4", 1), ("FRESH-1", 2)])
        self.assertEqual(freshness.lint_text("# Snapshot 2026-11-07\n## Child\nCurrent cash is 50", reference_date="2026-11-07"), [])

    def test_outbound_stale_reconciliation_and_callback_cannot_settle_new_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            entered, release = threading.Event(), threading.Event()
            calls = []
            def transport(**kwargs):
                calls.append(kwargs)
                if len(calls) == 1:
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError("fixture callback was not released")
                raise TimeoutError("fixture acknowledgement lost")
            gate = operations.OutboundGate(str(Path(directory) / "outbound.jsonl"), transport=transport)
            args = ("chat", "Ready", "result", "event", "recipient", {"outcome_status": "ready"})
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                original = pool.submit(gate.send, *args)
                self.assertTrue(entered.wait(5))
                attempt_one = gate._receipts()[-1]["id"]
                try:
                    gate.reconcile("event", attempt_one, "not_applied", "fixture receiver observation")
                    retry = gate.send(*args)
                    self.assertNotEqual(retry["id"], attempt_one)
                    self.assertEqual(calls[0]["idempotency_key"], calls[1]["idempotency_key"])
                    self.assertFalse(gate.reconcile("event", attempt_one, "applied", "stale fixture", {"id": "old"}))
                finally:
                    release.set()
                self.assertTrue(original.result(timeout=5)["superseded_result"])
            self.assertEqual(gate.send(*args)["receipt_id"], retry["id"])
            self.assertTrue(gate.reconcile("event", retry["id"], "applied", "receiver receipt", {"id": "current"})["sent"])

    def test_atomic_approval_consumption_and_handoff_delivery_have_one_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "approvals.jsonl")
            operations.ApprovalStore(path).record("publish", "fixture-target", b"approved", now=10)
            def authorize(_):
                return operations.ApprovalStore(path).authorize_and_consume("publish", iter(["fixture-target"]), b"approved", now=11)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                verdicts = list(pool.map(authorize, range(8)))
            self.assertEqual(verdicts.count("authorized_unique"), 1)
            self.assertEqual(verdicts.count("authorization_invalid"), 7)
            handoff = authority.HandoffStore(str(Path(directory) / "handoffs"))
            handoff_id, token = handoff.create("fixture summary", now=10)
            def deliver(i):
                try:
                    return handoff.deliver(handoff_id, token, str(i), now=11)
                except ValueError:
                    return "refused"
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(deliver, range(8)))
            self.assertEqual(results.count("fixture summary"), 1)
            self.assertEqual(results.count("refused"), 7)

    def test_approval_lifetime_is_finite_and_exact_expiry_is_not_authorized(self):
        with tempfile.TemporaryDirectory() as directory:
            store = operations.ApprovalStore(str(Path(directory) / "approvals.jsonl"))
            for ttl in (float("inf"), float("nan"), True, 0, -1, 1e308):
                with self.assertRaises(ValueError):
                    store.record("publish", "fixture-target", b"approved", ttl_days=ttl, now=10)
            store.record("publish", "fixture-target", b"approved", ttl_days=1, now=10)
            self.assertEqual(store.check("publish", ["fixture-target"], b"approved", now=86410), "authorization_invalid")
            for now in (float("inf"), float("nan"), True):
                with self.assertRaises(ValueError):
                    store.authorize_and_consume("publish", ["fixture-target"], b"approved", now=now)

    def test_outbound_confirmation_releases_retry_or_retains_delivery_dedup(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def transport(**kwargs):
                calls.append(kwargs)
                if len(calls) == 1:
                    raise TimeoutError("fixture")
                return {"id": "receiver-2"}
            gate = operations.OutboundGate(str(Path(directory) / "outbound.jsonl"), transport=transport)
            args = ("chat", "Ready", "result", "event", "recipient", {"outcome_status": "ready"})
            result = gate.send(*args)
            self.assertEqual(result["status"], "outcome_unknown")
            self.assertFalse(gate.reconcile("event", "wrong-attempt", "not_applied", "fixture"))
            gate.reconcile("event", result["id"], "not_applied", "old worker stopped; receiver confirms absent")
            self.assertTrue(gate.send(*args)["sent"])
            self.assertEqual(gate.send(*args)["status"], "duplicate_suppressed")
            self.assertEqual(len(calls), 2)

    def test_capsule_write_failure_preserves_prior_chain_and_concurrent_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "capsules.jsonl")
            capsules = reliability.EvidenceCapsules(path)
            capsules.record("fixture", "first", "SE0", "source")
            with patch.object(_storage.os, "replace", side_effect=OSError("fixture disk failure")):
                with self.assertRaises(OSError):
                    capsules.record("fixture", "uncommitted", "SE0", "source")
            self.assertEqual(capsules.verify()["entries"], 1)
            def append(i):
                reliability.EvidenceCapsules(path).record("fixture", str(i), "SE0", "source")
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(append, range(20)))
            self.assertEqual(capsules.verify(), {"ok": True, "entries": 21, "error": None})

    def test_fragment_registry_retains_concurrent_names_and_refuses_corrupt_existing_object(self):
        with tempfile.TemporaryDirectory() as directory:
            def put(i):
                return why.FragmentRegistry(directory).put_bytes(b"one shared fragment", str(i))
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                hashes = list(pool.map(put, range(20)))
            registry = why.FragmentRegistry(directory)
            self.assertEqual(len(set(hashes)), 1)
            self.assertEqual(set(registry._index()[hashes[0]]["names"]), {str(i) for i in range(20)})
            Path(registry.objects, hashes[0]).write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "differs"):
                registry.put_bytes(b"one shared fragment", "new name")

    def test_nonfinite_authority_and_procedural_scores_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            handoffs = authority.HandoffStore(directory)
            for invalid in (float("nan"), float("inf"), True):
                with self.assertRaises(ValueError):
                    handoffs.create("fixture", ttl_s=invalid, now=0)
            identifier, token = handoffs.create("fixture", now=0)
            with self.assertRaises(ValueError):
                handoffs.deliver(identifier, token, "worker", now=float("nan"))
        unit = {"id": "one", "trigger": "fixture", "action": "fixture", "domain": "test",
                "evidence": ["fixture"], "summary": "fixture", "confidence": .9,
                "success_rate": float("nan"), "scope": "project", "status": "active"}
        self.assertEqual(instincts.build_injection([unit])["injected"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
