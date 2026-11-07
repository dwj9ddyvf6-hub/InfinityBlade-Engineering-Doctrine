"""Offline counterexamples for real boundary failures; all state is temporary."""
import concurrent.futures
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BIN = Path(__file__).resolve().parents[1] / "bin"
sys.path.insert(0, str(BIN))
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


def instinct(status="active"):
    return {"id": "fixture", "trigger": "read fixture", "action": "check fixture", "domain": "test",
            "evidence": ["observation"], "summary": "A complete fixture summary.", "confidence": .9,
            "success_rate": 1, "scope": "project", "status": status}


class MemoryBoundaries(unittest.TestCase):
    def test_link_expansion_cannot_bypass_search_opt_out(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            store.add_fact(fact("public", "needle", links=["private", "reviewed"]))
            store.add_fact(fact("private", "secret fixture", opt_out_search=True))
            store.add_fact(fact("reviewed", "reviewed inference", inferred=True, review="approved"))
            hits = store.search("needle")
            self.assertEqual([row["id"] for row in hits], ["public", "reviewed"])
            self.assertFalse(hits[-1]["inferred"])
            self.assertNotIn("secret fixture", store.build_context("needle")["text"])

    def test_injection_budget_includes_omission_footer(self):
        unit = instinct()
        snapshot = copy.deepcopy(unit)
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            store.add_fact(fact("one", "needle " * 100))
            for budget in (0, 1, 50, 100, 250, 8000):
                with self.subTest(budget=budget):
                    result = instincts.build_injection([unit], budget_chars=budget)
                    self.assertLessEqual(len(result["text"]), budget)
                    self.assertEqual(result["used_chars"], len(result["text"]))
                    self.assertEqual(len(result["injected"]) + len(result["omitted"]), 1)
                    result = store.build_context("needle", budget_chars=budget)
                    self.assertLessEqual(len(result["text"]), budget)
                    self.assertEqual(len(result["included"]) + len(result["omitted"]), 1)
        self.assertEqual(unit, snapshot)

    def test_frozen_and_imported_pending_units_need_review(self):
        for status in ("frozen", "pending"):
            unit = instinct(status)
            self.assertEqual(instincts.build_injection([unit])["injected"], [])
            self.assertEqual(instincts.cluster_skill_candidates([unit]), [])
        payload = json.dumps(instinct()).encode()
        imported = instincts.import_instinct(payload, "https://example.org/instinct.json", now="2026-11-07")
        self.assertEqual(instincts.build_injection([imported])["injected"], [])

    def test_forgetting_preflights_index_and_prevents_resurrection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            original = fact("one", "retained fixture", source={"path": "fixture.md", "line": 7})
            store.add_fact(original)
            index = Path(directory) / "index.json"
            index.write_text(json.dumps({"one": {"nested": "unsupported"}}))
            with self.assertRaises(ValueError):
                store.forget_by_id(["one"], "2026-11-07", str(index))
            self.assertEqual(store.list_facts(), [original])
            store.forget_by_id(["one"], "2026-11-07")
            with self.assertRaisesRegex(ValueError, "resurrected"):
                store.add_fact(original)

    def test_corrections_keep_provenance_and_reject_competing_successors(self):
        with tempfile.TemporaryDirectory() as directory:
            store = memory_core.MemoryStore(directory).initialize()
            source = {"url": "https://example.org/evidence", "line": 7}
            store.add_fact(fact("one", "original", source=source))
            text = "This corrected fact contains enough explicit context to retain the required minimum number of words for review."
            first = store.propose_correction("one", text, "2026-11-07")
            second = store.propose_correction("one", text + " Another revision.", "2026-11-07")
            store.apply_correction(first, "2026-11-07")
            with self.assertRaises(ValueError):
                store.apply_correction(second, "2026-11-07")
            self.assertEqual(store.list_facts()[0]["source"], source)
            with self.assertRaises(ValueError):
                store.apply_edge(first, first, "updates", "2026-11-07")

    def test_migration_refuses_to_overwrite_existing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            source = memory_core.MemoryStore(str(Path(directory) / "source")).initialize()
            target = memory_core.MemoryStore(str(Path(directory) / "target")).initialize()
            source.add_fact(fact("source"))
            target.add_fact(fact("valuable"))
            with self.assertRaises(ValueError):
                memory_core.MemoryStore.migrate_from(source.root, target.root)
            self.assertEqual(target.list_facts()[0]["id"], "valuable")


class AuthorityBoundaries(unittest.TestCase):
    def test_nested_compaction_failure_preserves_original_and_caller(self):
        history = [{"content": ["original"]}]
        def mutate_then_fail(candidate):
            candidate[0]["content"].append("uncommitted")
            raise ValueError("fixture")
        result = authority.transactional_compact(history, mutate_then_fail, 1, 1)
        self.assertFalse(result["ok"])
        self.assertEqual(history, [{"content": ["original"]}])
        self.assertEqual(result["history"], history)

    def test_clean_runs_do_not_restore_quarantined_write_access(self):
        events = [{"kind": "defect"}] * 4 + [{"kind": "clean_run"}] * 30
        self.assertEqual(authority.peer_standing(events)["access"], "read-only")
        events.append({"kind": "human_restore", "reviewer": "fixture-reviewer", "evidence": "review-1"})
        self.assertEqual(authority.peer_standing(events)["access"], "write")

    def test_handoff_exact_expiry_and_concurrent_single_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            store = authority.HandoffStore(directory)
            expired, token = store.create("expired", ttl_s=1, now=0)
            with self.assertRaises(ValueError):
                store.deliver(expired, token, "waiter", now=1)
            identifier, token = store.create("one delivery", ttl_s=10, now=0)
            def deliver(_):
                try:
                    return authority.HandoffStore(directory).deliver(identifier, token, "waiter", now=1)
                except ValueError:
                    return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(deliver, range(8)))
            self.assertEqual(results.count("one delivery"), 1)
            with self.assertRaises(ValueError):
                store._path("..\\outside")

    def test_fragment_registry_rejects_path_escape_and_changed_object(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = why.FragmentRegistry(directory)
            digest = registry.put_bytes(b"fixture", "fixture")
            with self.assertRaises(ValueError):
                registry.get_bytes("/" + "x" * 80)
            Path(registry.objects, digest).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                registry.get_bytes(digest)


class DurableOperations(unittest.TestCase):
    def test_validation_without_transport_never_claims_send(self):
        with tempfile.TemporaryDirectory() as directory:
            gate = operations.OutboundGate(str(Path(directory) / "receipts"))
            result = gate.send("chat", "Result ready", "result", "event", "recipient", {"outcome_status": "ready"})
            self.assertFalse(result["sent"])
            self.assertEqual(result["status"], "ready")

    def test_transport_unknown_suppresses_unsafe_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def transport(**kwargs):
                calls.append(kwargs)
                raise TimeoutError("acknowledgement lost")
            gate = operations.OutboundGate(str(Path(directory) / "receipts"), transport=transport)
            args = ("chat", "Result ready", "result", "event", "recipient", {"outcome_status": "ready"})
            self.assertEqual(gate.send(*args)["status"], "outcome_unknown")
            self.assertEqual(gate.send(*args)["status"], "duplicate_suppressed")
            self.assertEqual(len(calls), 1)

    def test_queue_honors_backoff_and_reserves_until_acknowledged(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = operations.EffectQueue(str(Path(directory) / "queue.db"))
            try:
                with patch.object(operations.time, "time", return_value=100):
                    generation = queue.enqueue("effect", "one")
                    queue.record_rate_limited("effect", "one", generation, retry_after=10)
                    self.assertIsNone(queue.run_next(lambda _: self.fail("ran before due")))
                seen = []
                with patch.object(operations.time, "time", return_value=111):
                    self.assertEqual(queue.run_next(lambda row: seen.append(row)), "ok:one")
                    self.assertIsNone(queue.run_next(lambda _: self.fail("claimed twice")))
                self.assertEqual(queue.stop(), "partial")
                self.assertTrue(queue.complete("effect", "one", generation))
                self.assertEqual(queue.stop(), "completed")
                self.assertEqual(len(seen), 1)
            finally:
                queue.close()

    def test_failures_retry_to_bound_then_stay_terminal_across_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "queue.db")
            queue = operations.EffectQueue(path)
            generation = queue.enqueue("effect", "one")
            def failing(_):
                raise operations.RetryableEffectError("deterministic fixture rejection")
            for expected in (1, 2, 3):
                self.assertEqual(queue.run_next(failing), "failed:one")
                self.assertEqual(queue.get("effect", "one")["attempts"], expected)
            queue.close()
            queue = operations.EffectQueue(path)
            try:
                self.assertIsNone(queue.run_next(failing))
                self.assertEqual(queue.get("effect", "one")["state"], "failed")
                newer = queue.enqueue("effect", "one", revision=1)
                self.assertEqual(newer, generation + 1)
                self.assertEqual(queue.get("effect", "one")["attempts"], 0)
                self.assertFalse(queue.fail("effect", "one", generation))
                self.assertEqual(queue.get("effect", "one")["attempts"], 0)
            finally:
                queue.close()

    def test_handler_that_acted_then_raised_is_never_automatically_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "queue.db")
            queue = operations.EffectQueue(path)
            queue.enqueue("send", "one")
            sent = []
            def acted_then_failed(row):
                sent.append(row["key"])
                raise TimeoutError("acknowledgement lost after external effect")
            self.assertEqual(queue.run_next(acted_then_failed), "outcome_unknown:one")
            queue.close()
            queue = operations.EffectQueue(path)
            try:
                self.assertEqual(queue.get("send", "one")["state"], "outcome_unknown")
                self.assertIsNone(queue.run_next(acted_then_failed))
                self.assertEqual(sent, ["one"])
            finally:
                queue.close()

    def test_two_stale_slot_instances_cannot_exceed_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "slots.json")
            first, second = operations.SlotGuard(path, 1), operations.SlotGuard(path, 1)
            first.reserve_worker("one")
            with self.assertRaises(ValueError):
                second.reserve_worker("two")

    def test_approval_reloads_revocation_and_consumes_exact_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "approvals.jsonl")
            first, second = operations.ApprovalStore(path), operations.ApprovalStore(path)
            first.record("publish", "target", b"old", now=100)
            first.record("publish", "target", b"new", now=100)
            self.assertEqual(second.authorize_and_consume("publish", ["target"], b"new", now=101), "authorized_unique")
            self.assertEqual(first.check("publish", ["target"], b"new", now=101), "drifted")
            first.revoke("publish", "target")
            self.assertEqual(second.check("publish", ["target"], b"old", now=101), "authorization_invalid")

    def test_redaction_handles_tuple_and_shared_alias_without_false_cycle(self):
        shared = {"note": "keep"}
        result = operations.redact({"a": shared, "b": shared, "nested": ({"api_key": "fixture"},)})
        self.assertEqual(result["a"], result["b"])
        self.assertEqual(result["nested"][0]["api_key"], "REDACTED")

    def test_capsules_reject_tampered_chain_and_report_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capsules.jsonl"
            capsules = reliability.EvidenceCapsules(str(path))
            capsules.record("fixture", "read", "SE0", "fixture.txt")
            row = json.loads(path.read_text())
            row["target"] = "changed.txt"
            path.write_text(json.dumps(row) + "\n")
            with self.assertRaises(ValueError):
                capsules.record("fixture", "read", "SE0", "another.txt")
            with self.assertRaises(ValueError):
                capsules.replay_plan()
            path.write_text("not-json\n")
            self.assertFalse(capsules.verify()["ok"])


class ScoringAndFreshness(unittest.TestCase):
    def test_auto_lane_never_bypasses_missing_rate_caps(self):
        with self.assertRaises(ValueError):
            proactive.decide_lane({"C_FA": 1, "C_FN": 10, "mode": "auto"}, .99, .9)
        with self.assertRaises(ValueError):
            proactive.tau(float("nan"), 1, .5)
        with self.assertRaises(ValueError):
            proactive.score_timeline([{"label": "MUST", "fires": True}])

    def test_conflicting_calibration_labels_drop_both(self):
        entries = [{"input": "same", "human_label": label, "provenance": "fixture", "rationale": "fixture"}
                   for label in ("fire", "silent")]
        kept, dropped = proactive.consistency_filter(entries)
        self.assertEqual(kept, [])
        self.assertEqual(len(dropped), 2)

    def test_truthy_strings_and_out_of_range_scores_do_not_pass(self):
        cases = [{"query": "fixture", "expect": "trigger", "split": "final"}]
        with self.assertRaises(ValueError):
            skill_lab.score_predictions(cases, {"final": {"fixture": ["false"] * 3}}, "final")
        with self.assertRaises(ValueError):
            skill_lab.adoption_scan({"review_status": 2})
        with self.assertRaises(ValueError):
            skill_lab.reliability({"fixture": [True]}, k=0)
        self.assertTrue(skill_lab.validate_trajectory({"tool_sequence": ["read"], "actual_calls": [{"tool": "read"}, {"tool": "send"}]}))

    def test_balanced_means_equal_counts_and_file_sizes_measure_bytes(self):
        data = {"reference_solution": "fixture", "isolated_trials": True, "judge_unknown_exit": True,
                "cases": [{"kind": "should"}] * 3 + [{"kind": "should-not"}]}
        self.assertTrue(skill_lab.validate_eval_set(data))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skill.md"
            path.write_bytes(b"x" * 20001)
            self.assertTrue(skill_lab.skill_size(str(path))["blocked"])

    def test_multiple_dispositions_and_invalid_dates_fail_explicitly(self):
        with self.assertRaises(ValueError):
            freshness.aged_disposition("freshness-action: retire; freshness-action: re-observe")
        result = freshness.lint_text("status has 5 rows as of 2026-99-99", reference_date="2026-11-07")
        self.assertEqual(result[0]["code"], "FRESH-4")
        self.assertTrue(freshness.validate_fact({"kind": "dated", "as_of": "not-a-date"}))
        self.assertEqual(freshness.lint_text("# As of 2026-11-07\n## Child\nstatus has 5 rows", reference_date="2026-11-07"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
