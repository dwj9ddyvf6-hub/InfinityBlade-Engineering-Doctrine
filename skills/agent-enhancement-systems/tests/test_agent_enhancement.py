#!/usr/bin/env python3
"""Package tests for the agent-enhancement mechanisms.

Run from anywhere:
    python3 tests/test_agent_enhancement.py

Every test uses temporary state. No test reads a host workspace, a network,
or a credential. A missing mechanism is a failing test, not a prose claim.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "bin")
sys.path.insert(0, os.path.abspath(BIN))


def load(name):
    path = os.path.join(BIN, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


proactive = load("proactive")
instincts = load("instincts")
memory_core = load("memory_core")
skill_lab = load("skill_lab")
reliability = load("reliability")
authority = load("authority")
why = load("why")
freshness = load("freshness")
operations = load("operations")


class ProactiveTests(unittest.TestCase):
    def test_timeline_pricing_and_prism_gate(self):
        result = proactive.score_timeline([
            {"label": "MUST", "fires": 2},
            {"label": "MAY", "fires": 1},
            {"label": "MUST-NOT", "fires": 1},
            {"label": "OTHER", "fires": 1},
        ])
        self.assertEqual(result["benefit"], 6)
        self.assertEqual(result["cost"], 9)
        self.assertEqual(result["verdict_at"](1.0), "SILENCE")
        cfg = {"lane": "demo", "C_FA": 1, "C_FN": 9, "margin": 0.05,
               "min_interval": 60, "max_fires_per_window": 2, "mode": "auto"}
        self.assertEqual(proactive.decide_lane(cfg, 0.9, 1.0, now=100)["verdict"], "fire")
        observe = dict(cfg, mode="observe")
        self.assertEqual(proactive.decide_lane(observe, 0.9, 1.0, now=100)["verdict"], "would_accept")
        with self.assertRaises(ValueError):
            proactive.decide_lane({}, 0.5, 0.5)

    def test_assessment_shape_delivery_and_silence_audit(self):
        assessment = {
            "candidate_id": "c1", "strength": "inferred", "decision": "accept",
            "intent_evidence": "deadline is tomorrow",
            "rules_judged": [
                {"rule_id": "urgent", "verdict": "match", "evidence": "due tomorrow"},
                {"rule_id": "duplicate", "verdict": "no_match", "evidence": "no prior fire"},
            ],
        }
        checked = proactive.validate_assessment(["urgent", "duplicate"], assessment, mode="observe")
        self.assertEqual(checked["decision"], "would_accept")
        bad = json.loads(json.dumps(assessment))
        bad["rules_judged"] = bad["rules_judged"][:1]
        with self.assertRaises(ValueError):
            proactive.validate_assessment(["urgent", "duplicate"], bad, mode="auto")
        grade = proactive.grade_delivery("Your report is ready. Open it when convenient.", goal_terms=("report",))
        self.assertEqual(grade["score"], 10)
        leaky = proactive.grade_delivery("lane: demo tau=0.5 origin_event=e1", goal_terms=("report",))
        self.assertIn("natural_format", {d["criterion"] for d in leaky["deductions"]})
        with tempfile.TemporaryDirectory() as td:
            ledger = proactive.LaneLedger(os.path.join(td, "lane.jsonl"))
            ledger.record({"verdict": "silent", "origin_event": "e1", "p_need": 1.0})
            ledger.record({"verdict": "fire", "origin_event": "e2", "fire_id": "f2"})
            audit = ledger.audit_silence()
            self.assertEqual(audit["silent_total"], 1)
            self.assertEqual(audit["missed_need"][0]["origin_event"], "e1")
            ledger.record_reformulation("e1", "narrowed the recipient")
            with self.assertRaises(ValueError):
                ledger.record_reformulation("e1", "second attempt")


class InstinctTests(unittest.TestCase):
    def unit(self, **kw):
        base = {"id": "i1", "trigger": "before merging code", "action": "run the full gate",
                "domain": "code", "confidence": 0.85, "observations": 12,
                "contexts": ["repo-a"], "evidence": ["run-1"], "scope": "project",
                "status": "active", "success_rate": 0.9, "contradicted": False,
                "summary": "Run the full gate before merging code.", "created_on": "2026-11-01"}
        base.update(kw)
        return base

    def test_confidence_promotion_import_and_injection(self):
        self.assertEqual(instincts.confidence_for_count(4), 0.5)
        self.assertEqual(instincts.confidence_for_count(8), 0.7)
        self.assertEqual(instincts.confidence_for_count(20), 0.85)
        self.assertEqual(instincts.confidence_for_count(2, strong_source=True), 0.9)
        global_unit = self.unit(contexts=["repo-a", "repo-b"])
        self.assertTrue(instincts.promotion_decision(global_unit)["eligible"])
        weak = self.unit(id="weak", confidence=0.5, trigger="when tired", action="guess")
        frozen = self.unit(id="frozen", contradicted=True, trigger="old rule", action="stop")
        result = instincts.build_injection([global_unit, weak, frozen], now="2026-11-02")
        self.assertEqual(result["injected"], ["i1"])
        self.assertEqual({x["id"] for x in result["rejected"]}, {"weak", "frozen"})
        imported = instincts.import_instinct(
            json.dumps(self.unit(id="ext")).encode(), "https://example.org/unit.json", now="2026-11-02")
        self.assertEqual(imported["status"], "pending")
        self.assertEqual(imported["landing"], "inherited-only")
        with self.assertRaises(ValueError):
            instincts.import_instinct(b"{}", "http://127.0.0.1/unit.json")
        clusters = instincts.cluster_skill_candidates([global_unit])
        self.assertTrue(clusters[0]["human_gate_required"])
        events = [instincts.capture_event({"id": f"e{i}", "actor": "worker", "trigger": "before merging code",
                                           "action": "run the full gate", "domain": "code",
                                           "api_key": "do-not-store"})
                  for i in range(3)]
        self.assertEqual(events[0]["api_key"], "REDACTED")
        candidates = instincts.extract_candidates(events)
        self.assertEqual(candidates[0]["confidence"], 0.5)
        self.assertEqual(candidates[0]["status"], "pending")
        with self.assertRaises(ValueError):
            instincts.capture_event({"actor": "observer"}, observer="observer")


class MemoryTests(unittest.TestCase):
    def fact(self, fid, text, **kw):
        base = {"id": fid, "text": text, "bucket": "work", "entities": ["fee walk"],
                "status": "current", "inferred": False, "review": "not_required",
                "valid_from": "2026-11-01", "valid_until": None, "learned_on": "2026-11-01"}
        base.update(kw)
        return base

    def test_profile_graph_review_correction_erasure_and_recall(self):
        with tempfile.TemporaryDirectory() as td:
            store = memory_core.MemoryStore(os.path.join(td, "store"))
            store.initialize()
            for i in range(8):
                store.add_profile_fact("static", "preferences", f"Standing preference number {i} is recorded.")
            with self.assertRaises(ValueError):
                store.add_profile_fact("static", "preferences", "One fact too many for the profile cap.")
            a = self.fact("a", "The fee walk pages through every fee record by using an opaque token on each request.")
            b = self.fact("b", "The fee walk now pages through every fee record by token and never advances by date.")
            store.add_fact(a); store.add_fact(b)
            store.apply_edge("b", "a", "updates", "2026-11-03")
            facts = {f["id"]: f for f in store.list_facts()}
            self.assertEqual(facts["a"]["status"], "superseded")
            self.assertEqual(facts["a"]["valid_until"], "2026-11-03")
            c = self.fact("c", "The operator probably prefers token paging when reconciling a long fee history for accuracy and completeness.", inferred=True, review="pending")
            store.add_fact(c); store.apply_edge("c", "b", "derives", "2026-11-03")
            self.assertEqual([x["id"] for x in store.review_queue()], ["c"])
            store.review("c", "approve", "2026-11-03")
            successor = store.propose_correction("b", "The fee walk pages by opaque token and treats a fee already netted in fills as counted once.", "2026-11-04")
            self.assertEqual({f["id"]: f for f in store.list_facts()}["b"]["status"], "current")
            store.apply_correction(successor, "2026-11-04")
            facts = {f["id"]: f for f in store.list_facts()}
            self.assertEqual(facts["b"]["status"], "superseded")
            self.assertEqual(store.recall("fee walk token")["tier"], "supported")
            self.assertEqual(store.recall("zxqw platypus")["tier"], "not present")
            closest = store.recall("operator")
            self.assertEqual(closest["tier"], "closest-only")
            self.assertLessEqual(len(closest["previews"]), 3)
            preview = store.semantic_forget_preview("operator prefers")
            result = store.forget_semantic(preview, "2026-11-04")
            self.assertEqual(result["c"], "forgotten")
            self.assertEqual(store.forget_by_id(["c"], "2026-11-04")["c"], "already_forgotten")
            audit = store.audit_corpus()
            self.assertIn("junk_rate", audit)

    def test_future_normalisation_operations_and_demotion(self):
        fact = memory_core.normalize_future_fact(
            {"id": "plan", "text": "Ship the report Friday.", "deadline": "2026-11-06"}, "2026-11-03")
        self.assertEqual(fact["valid_from"], "2026-11-03")
        self.assertIsNone(fact["valid_until"])
        scored = memory_core.score_operations([
            {"op": "add", "target": "x", "after": "token paging works", "evidence": "token paging works"},
            {"op": "add", "target": "y", "after": "invented claim", "evidence": ""},
        ])
        self.assertEqual(scored["overall"], "FAIL")
        with tempfile.TemporaryDirectory() as td:
            store = memory_core.MemoryStore(os.path.join(td, "store")); store.initialize()
            lesson = self.fact("lesson", "A session lesson becomes permanent only after a named reviewer accepts it into the store.")
            with self.assertRaises(ValueError):
                store.promote_session_lesson(lesson, False, "reviewer", "2026-11-03")
            store.promote_session_lesson(lesson, True, "reviewer", "2026-11-03")
            migrated = memory_core.MemoryStore.migrate_from(os.path.join(td, "store"), os.path.join(td, "copy"))
            self.assertEqual(migrated["retrievable"], 1)
            store.add_fact(self.fact("old", "A standing fact that has not been retrieved during the recent review window at all."))
            self.assertIn("old", {row["id"] for row in store.demotion_candidates("2026-11-20")})


class SkillLabTests(unittest.TestCase):
    def test_lint_cost_eval_and_untouched_final(self):
        good = "---\nname: demo-skill\ndescription: Use when testing a demo skill thoroughly.\nversion: 1.0.0\ncapabilities: read, write\n---\n# Demo\n"
        self.assertEqual(skill_lab.lint_skill_text(good), [])
        self.assertTrue(skill_lab.lint_skill_text(good.replace("demo-skill", "Bad_Name")))
        self.assertTrue(skill_lab.skill_size("x" * 20000)["blocked"])
        self.assertTrue(skill_lab.token_cost("x" * 4000, "d" * 100)["fails_review"])
        eval_set = {"reference_solution": "known", "isolated_trials": True, "judge_unknown_exit": True,
                    "cases": [{"id": "p", "kind": "should"}, {"id": "n", "kind": "should-not"}]}
        self.assertEqual(skill_lab.validate_eval_set(eval_set), [])
        cases = [{"query": "run it", "expect": "trigger", "split": "validation"},
                 {"query": "ignore it", "expect": "no-trigger", "split": "validation"},
                 {"query": "final run", "expect": "trigger", "split": "final"},
                 {"query": "final ignore", "expect": "no-trigger", "split": "final"}]
        preds = {"validation": {"run it": [True, True, False], "ignore it": [False, False, True]},
                 "final": {"final run": [True, True, True], "final ignore": [False, False, False]}}
        self.assertEqual(skill_lab.score_predictions(cases, preds, "validation")["accuracy"], 1.0)
        with tempfile.TemporaryDirectory() as td:
            ledger = os.path.join(td, "final.json")
            first = skill_lab.run_final_test(cases, preds, "candidate-1", ledger)
            self.assertEqual(first["accuracy"], 1.0)
            with self.assertRaises(ValueError):
                skill_lab.run_final_test(cases, preds, "candidate-1", ledger)
        rel = skill_lab.reliability({"a": [True, True, False], "b": [True, True, True]}, k=3)
        self.assertEqual(rel["pass_at_k"], 1.0)
        self.assertEqual(rel["pass_pow_k"], 0.5)

    def test_scan_adoption_directory_fragment_and_f7(self):
        with tempfile.TemporaryDirectory() as td:
            bad = os.path.join(td, "bad.py")
            with open(bad, "w") as handle:
                handle.write('api_key = "ABCDEFGHIJKLMNOP1234"\n')
            scan = skill_lab.scan_config([td])
            self.assertLess(scan["score"], 100)
            self.assertEqual(skill_lab.scan_staged_text("ordinary text"), [])
            manifest = {"review_status": 1, "publisher_binding": 1, "commit_integrity": 1,
                        "manifest_integrity": 1, "domain_proof": 1, "metadata_quality": 1,
                        "taxonomy": 1, "provenance": 1}
            adopted = skill_lab.adoption_scan(manifest)
            self.assertEqual(adopted["score"], 28)
            missing = skill_lab.adoption_scan({})
            self.assertEqual(missing["score"], 0)
            frag = os.path.join(td, "intro")
            with open(frag, "w") as handle:
                handle.write("hello")
            import hashlib
            pin = hashlib.sha256(b"hello").hexdigest()[:16]
            self.assertEqual(skill_lab.fragment_lint("{{fragment:intro@%s}}" % pin, td), [])
            desc = os.path.join(td, "DIRECTORY.md")
            with open(desc, "w") as handle:
                handle.write("Abstract: Demo directory for tests.\n\nOverview: This directory holds temporary fixtures used only by the package tests and should be opened only when debugging them.\n")
            self.assertEqual(skill_lab.directory_description_check(td), [])
            clean = os.path.join(td, "clean"); mutant = os.path.join(td, "mutant")
            os.mkdir(clean); os.mkdir(mutant)
            with open(os.path.join(clean, "check.py"), "w") as handle:
                handle.write("print('ok')\n")
            with open(os.path.join(mutant, "check.py"), "w") as handle:
                handle.write("raise SystemExit(1)\n")
            result = skill_lab.f7_check(clean, mutant, [sys.executable, "check.py"])
            self.assertTrue(result["accepted"])


class ReliabilityTests(unittest.TestCase):
    def test_capsules_cover_and_metric_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "capsules.jsonl")
            caps = reliability.EvidenceCapsules(path)
            caps.record("agent", "read", "SE0", "file", ts=1)
            caps.record("agent", "publish", "SE3", "page", ts=2)
            self.assertTrue(caps.verify()["ok"])
            plan = caps.replay_plan()
            self.assertEqual([x["seq"] for x in plan["replayable"]], [1])
            self.assertEqual([x["seq"] for x in plan["refused"]], [2])
            with self.assertRaises(ValueError):
                caps.record("agent", "pay", "SE4", "account")
            ok, uncovered, ambiguous = reliability.unique_cover(
                ["tests"], [{"id": "e", "covers": ["tests"]}])
            self.assertTrue(ok)
            self.assertEqual(reliability.metric_record(3, "measured_this_run")["provenance"], "measured_this_run")
            with self.assertRaises(ValueError):
                reliability.metric_record(3, "cached")


class AuthorityTests(unittest.TestCase):
    def test_mandate_handoff_checkpoint_recovery_and_fence(self):
        mandate = authority.Mandate.create(["read", "write"], "owner", policy_version=2)
        self.assertTrue(authority.Mandate.revalidate(mandate, 2, ["read"]))
        with self.assertRaises(ValueError):
            authority.Mandate.revalidate(mandate, 2, ["read", "publish"])
        with tempfile.TemporaryDirectory() as td:
            store = authority.HandoffStore(td)
            hid, token = store.create("summary", ttl_s=60, now=100)
            store.claim(hid, "worker", now=100)
            with self.assertRaises(ValueError):
                store.claim(hid, "other", now=100)
            self.assertEqual(store.deliver(hid, token, "worker", now=101), "summary")
            with self.assertRaises(ValueError):
                store.deliver(hid, token, "worker", now=102)
        checkpoint = {"objective": "ship", "state": "ready", "evidence": "tests",
                      "decisions": "use sqlite", "pending": "review", "generation": 1,
                      "expires": 200}
        self.assertEqual(authority.validate_checkpoint(checkpoint, now=100), [])
        plan = authority.recovery_plan({"read": ["a"], "unread": ["b"]})
        self.assertEqual(plan["requeue"], ["b"])
        self.assertIn("inspect", plan["note"].lower())
        token = authority.make_fence_token("run-1")
        fence = authority.FenceFilter(token)
        payload = "safe" + token + "hidden"
        out = fence.feed(payload[:6]) + fence.feed(payload[6:]) + fence.flush()
        self.assertNotIn("hidden", out)
        standing = authority.peer_standing([{"kind": "defect"}, {"kind": "defect"}, {"kind": "defect"}, {"kind": "defect"}])
        self.assertEqual(standing["access"], "read-only")


class WhyAndFreshnessTests(unittest.TestCase):
    def test_why_exemplars_and_fragments(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "why.jsonl")
            entry = why.new_entry("Use token paging", [{"alternative": "date paging", "why_lost": "drops ties"}],
                                  "complete read", "decision", "test", "ties recur", "memory_core.py")
            why.append_entry(path, entry)
            self.assertEqual([e["id"] for e in why.injection_view(path)], [entry["id"]])
            bad = dict(entry); bad.pop("id")
            with self.assertRaises(ValueError):
                why.append_entry(path, bad)
            registry = why.FragmentRegistry(os.path.join(td, "fragments"))
            h = registry.put_bytes(b"shared context", "pack")
            self.assertEqual(registry.get_bytes(h[:10]), b"shared context")
            self.assertIn(h[:16], registry.cite("pack"))
            exemplar = {"task_class": "repair", "situation": "test fails", "approach": "revert proof", "why_it_worked": "isolated cause"}
            self.assertEqual(why.validate_exemplar(exemplar), [])

    def test_freshness_forms(self):
        self.assertEqual(freshness.validate_fact({"kind": "timeless", "text": "IDs are hashes."}), [])
        self.assertTrue(freshness.validate_fact({"kind": "dated", "text": "3 open rows"}))
        pointer = {"kind": "pointer", "text": "count", "target": "ledger.json", "last_observed": 3, "as_of": "2026-11-03"}
        self.assertEqual(freshness.validate_fact(pointer), [])
        findings = freshness.lint_text("There are 3 open defects.", reference_date="2026-11-04")
        self.assertTrue(any(f["code"] == "FRESH-1" for f in findings))
        refreshed = freshness.refresh_on_read(pointer, True, "2026-11-04", contract_declared=True)
        self.assertEqual(refreshed["as_of"], "2026-11-04")
        unchanged = freshness.refresh_on_read(pointer, True, "2026-11-04", contract_declared=False)
        self.assertEqual(unchanged["as_of"], "2026-11-03")


class OperationsTests(unittest.TestCase):
    def test_ids_redaction_outbound_and_receipts(self):
        self.assertEqual(operations.deterministic_id(["a", 1]), operations.deterministic_id(["a", 1]))
        redacted = operations.redact({"api_key": "x", "nested": {"note": "keep"}, "prompt": "text"})
        self.assertEqual(redacted["api_key"], "REDACTED")
        self.assertEqual(redacted["nested"]["note"], "keep")
        with tempfile.TemporaryDirectory() as td:
            gate = operations.OutboundGate(os.path.join(td, "receipts.jsonl"),
                                           caps={"short": {"words": 5, "chars": 40}},
                                           open_question="Approve?",
                                           transport=lambda **kwargs: {"id": "fixture-ack"})
            receipt = gate.send("short", "Ready now.", "result", "evt-1", "owner",
                                {"outcome_status": "completed"})
            self.assertTrue(receipt["sent"])
            duplicate = gate.send("short", "Ready again.", "result", "evt-1", "owner",
                                  {"outcome_status": "completed"})
            self.assertEqual(duplicate["status"], "duplicate_suppressed")
            with self.assertRaises(ValueError):
                gate.send("short", "six words are in this text", "result", "evt-2", "owner",
                          {"outcome_status": "completed"})
            with self.assertRaises(ValueError):
                gate.send("short", "Question?", "attention", "evt-3", "owner", {"question": "Other?"})

    def test_effect_queue_routing_slots_near_miss_and_approvals(self):
        with tempfile.TemporaryDirectory() as td:
            queue = operations.EffectQueue(os.path.join(td, "effects.db"))
            gen = queue.enqueue("send", "m1", {"body": 1}, revision=1)
            self.assertEqual(queue.enqueue("send", "m1", {"body": 2}, revision=1), "stale")
            queue.record_rate_limited("send", "m1", gen, retry_after=10)
            row = queue.get("send", "m1")
            self.assertEqual(row["attempts"], 0)
            self.assertEqual(row["infra_errors"], 1)
            receipt = queue.issue_receipt("send", "m1", gen)
            gen2 = queue.enqueue("send", "m1", {"body": 2}, revision=2)
            self.assertFalse(queue.complete("send", "m1", gen2, receipt=receipt))
            queue.close()
            slots = operations.SlotGuard(os.path.join(td, "slots.json"), worker_cap=1)
            slots.reserve_worker("w1")
            with self.assertRaises(ValueError):
                slots.reserve_worker("w2")
            slots.reserve_human("owner")
            self.assertTrue(operations.route_followup("owner-1", True)["routed"])
            self.assertFalse(operations.route_followup("owner-1", False)["routed"])
            ledger = operations.NearMissLedger(os.path.join(td, "near.jsonl"))
            ledger.record("gate-a", "threshold", "score 0.4 for 'secret'")
            self.assertIn("<n>", ledger.report()["samples"]["gate-a"][0])
            approvals = operations.ApprovalStore(os.path.join(td, "approvals.jsonl"), generation=1)
            target = {"path": "docs/x.md"}
            approvals.record("publish", target, b"v1", now=1000)
            self.assertEqual(approvals.check("publish", [target], b"v1", now=1001), "authorized_unique")
            self.assertEqual(approvals.check("publish", [target], b"v2", now=1001), "drifted")
            self.assertEqual(approvals.check("unpublish", [target], b"v1", now=1001), "out_of_scope")


if __name__ == "__main__":
    unittest.main(verbosity=2)
