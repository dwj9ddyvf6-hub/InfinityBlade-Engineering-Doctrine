"""Outcome-oracle counterexamples: no live processes, network or model calls."""
from copy import deepcopy
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evaluate_task as evaluator


class ArtifactEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.content = b'{"balance":5,"settled":true,"orders":[{"id":"o-1"}],"a/b":{"~key":null}}\n'
        self.fixture_content = b'{"starting_balance":0,"deposit":5}\n'
        (self.artifacts / "state.json").write_bytes(self.content)
        self.case = {
            "schema_version": 1, "case_id": "receipt-final-state",
            "fixture": {"id": "synthetic-state-v1", "sha256": evaluator.digest(self.fixture_content)},
            "acceptance": [{"id": "state", "subject": "synthetic-settlement", "description": "Final balance and order are settled", "boundary": "local-artifact", "checks": [
                {"id": "balance", "kind": "json_equals", "path": "state.json", "pointer": "/balance", "expected": 5},
                {"id": "settled", "kind": "json_equals", "path": "state.json", "pointer": "/settled", "expected": True},
                {"id": "no-leak", "kind": "path_absent", "path": "secret.txt"},
                {"id": "inventory", "kind": "inventory_equals", "expected": ["state.json"]}]}]}

    def evaluate(self, case=None, artifacts=None, **kwargs):
        return evaluator.evaluate(case or self.case, artifacts or self.artifacts, **kwargs)

    def plan(self):
        raw = json.dumps(self.case, indent=2).encode()
        (self.root / "case.json").write_bytes(raw)
        (self.root / "fixture.json").write_bytes(self.fixture_content)
        config = {"model": "fixture-model", "host": "fixture-host", "tools_sha256": "2" * 64,
                  "system_sha256": "3" * 64, "budget": {"output_tokens": 1000}, "seed": 7}
        trials = {}
        for variant in ("baseline", "candidate"):
            path = self.root / variant
            path.mkdir(exist_ok=True)
            (path / "state.json").write_bytes(self.content)
            trials[variant] = {"trial_id": variant + "-1", "status": "completed", "treatment_revision": variant + "-rev",
                               "observed_at": "2026-11-07T00:00:00Z", "artifacts": variant,
                               "configuration": deepcopy(config), "case_sha256": evaluator.digest(raw),
                               "fixture_sha256": self.case["fixture"]["sha256"],
                               "metrics": {"elapsed_seconds": 3, "output_tokens": None}}
        return {"schema_version": 1, "experiment_id": "paired-fixture", "pairs": [{"pair_id": "first", "case": "case.json", "fixture": "fixture.json", **trials}]}

    def test_actual_state_and_hashes_are_checked_without_rewriting_sources(self):
        before = (self.artifacts / "state.json").read_bytes()
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["coverage"]["checks"], 4)
        self.assertEqual(result["observed_files"]["state.json"]["sha256"], evaluator.digest(before))
        self.assertEqual((self.artifacts / "state.json").read_bytes(), before)
        (self.artifacts / "state.json").write_text('{"balance":4,"settled":true}')
        failed = self.evaluate()
        self.assertEqual(failed["status"], "FAIL")
        self.assertEqual(failed["acceptance"][0]["checks"][0]["observed"]["value"], 4)

    def test_claimed_green_does_not_make_wrong_artifact_pass(self):
        record = {"acceptance": [{"id": "state", "subject": "synthetic-settlement", "boundary": "local-artifact", "status": "PASS"}], "overall_status": "GREEN"}
        (self.artifacts / "state.json").write_text('{"balance":1,"settled":true}')
        result = self.evaluate(task_record=record)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["claim_supported_at_declared_boundary"])
        record["acceptance"].append({"id": "silently-dropped"})
        with self.assertRaisesRegex(ValueError, "exactly"):
            self.evaluate(task_record=record)

    def test_missing_expected_output_fails_but_missing_bundle_is_unverified(self):
        (self.artifacts / "state.json").unlink()
        result = self.evaluate()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("state.json", result["observed_absent_paths"])
        self.assertEqual(self.evaluate(artifacts=self.root / "unavailable")["status"], "UNVERIFIED")

    def test_declared_absence_and_inventory_detect_unexpected_effects(self):
        (self.artifacts / "secret.txt").write_text("synthetic forbidden output")
        result = self.evaluate()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual([c["status"] for c in result["acceptance"][0]["checks"]][-2:], ["FAIL", "FAIL"])

    def test_strict_json_rejects_ambiguous_duplicate_and_nonfinite_data(self):
        for payload in [b'{"balance":0,"balance":5,"settled":true}', b'{"balance":NaN}', b'{"balance":1e999}', b'not JSON']:
            with self.subTest(payload=payload):
                (self.artifacts / "state.json").write_bytes(payload)
                self.assertEqual(self.evaluate()["status"], "FAIL")
        with self.assertRaises(ValueError):
            evaluator.strict_json(b'{"case_id":"one","case_id":"two"}')

    def test_boolean_is_not_one_and_json_pointer_escapes_are_exact(self):
        case = deepcopy(self.case)
        checks = case["acceptance"][0]["checks"]
        checks[0].update(pointer="/settled", expected=1)
        self.assertEqual(self.evaluate(case)["status"], "FAIL")
        checks[0].update(pointer="/a~1b/~0key", expected=None)
        self.assertEqual(self.evaluate(case)["status"], "PASS")
        for pointer in ("/orders/00", "/orders/-", "/orders/-1", "/orders/9"):
            checks[0].update(pointer=pointer, expected={"id": "o-1"})
            self.assertEqual(self.evaluate(case)["status"], "FAIL")
        checks[0].update(pointer="/a~2b", expected=None)
        with self.assertRaisesRegex(ValueError, "Pointer"):
            self.evaluate(case)

    def test_hash_and_text_checks_keep_their_declared_scope(self):
        case = deepcopy(self.case)
        case["acceptance"][0]["checks"] = [
            {"id": "hash", "kind": "file_sha256", "path": "state.json", "expected": evaluator.digest(self.content)},
            {"id": "literal", "kind": "text_contains", "path": "state.json", "expected": '"settled":true'}]
        self.assertEqual(self.evaluate(case)["status"], "PASS")
        (self.artifacts / "state.json").write_bytes(self.content + b" ")
        self.assertEqual(self.evaluate(case)["status"], "FAIL")

    def test_empty_duplicate_or_executable_oracles_are_refused(self):
        variants = []
        case = deepcopy(self.case); case["acceptance"] = []; variants.append(case)
        case = deepcopy(self.case); case["acceptance"].append(deepcopy(case["acceptance"][0])); variants.append(case)
        case = deepcopy(self.case); case["acceptance"][0]["checks"] = []; variants.append(case)
        case = deepcopy(self.case); case["acceptance"][0]["checks"][0]["kind"] = "shell"; variants.append(case)
        case = deepcopy(self.case); case["acceptance"][0]["checks"][0]["path"] = "../outside"; variants.append(case)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.evaluate(value)

    def test_symlink_and_inspection_limit_never_produce_pass(self):
        (self.artifacts / "state.json").unlink()
        (self.root / "outside.json").write_bytes(self.content)
        (self.artifacts / "state.json").symlink_to(self.root / "outside.json")
        self.assertEqual(self.evaluate()["status"], "UNVERIFIED")
        (self.artifacts / "state.json").unlink()
        (self.artifacts / "state.json").write_bytes(self.content)
        self.assertEqual(self.evaluate(max_bytes=4)["status"], "UNVERIFIED")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO fixture")
    def test_fifo_observation_never_blocks(self):
        (self.artifacts / "state.json").unlink()
        os.mkfifo(self.artifacts / "state.json")
        self.assertEqual(self.evaluate()["status"], "UNVERIFIED")

    def test_changed_artifact_during_readback_invalidates_verdict(self):
        original = evaluator.Observation.confirm
        def move(snapshot):
            (self.artifacts / "state.json").write_text('{"balance":7}')
            return original(snapshot)
        with patch.object(evaluator.Observation, "confirm", move):
            result = self.evaluate()
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["stability"]["status"], "UNVERIFIED")

    def test_inventory_race_is_unverified_without_crashing_or_dropping_checks(self):
        with patch.object(evaluator.Observation, "inventory", side_effect=FileNotFoundError("racing fixture")):
            result = self.evaluate()
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["coverage"]["checks"], 4)

    def test_pairing_regrades_artifacts_and_retains_regressions(self):
        plan = self.plan()
        (self.root / "candidate/state.json").write_text('{"balance":1,"settled":true}')
        plan["pairs"][0]["candidate"]["forged_result"] = {"status": "PASS"}
        result = evaluator.compare(plan, self.root)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["paired_outcomes"]["regressed"], 1)
        self.assertEqual(result["absolute_pass_rate_change_percentage_points"], -100)
        self.assertIsNone(result["cost_differences_candidate_minus_baseline"]["output_tokens"]["mean"])
        self.assertEqual(result["cost_differences_candidate_minus_baseline"]["output_tokens"]["missing_comparable_pairs"], 1)

    def test_configuration_drift_and_missing_pairs_are_not_silently_pooled(self):
        plan = self.plan()
        plan["pairs"][0]["candidate"]["configuration"]["model"] = "different-model"
        plan["pairs"].append({"pair_id": "not-run", "case": "case.json", "fixture": "fixture.json"})
        result = evaluator.compare(plan, self.root)
        self.assertEqual(result["coverage"], {"planned_pairs": 2, "comparable_pairs": 0, "excluded_or_unverified_pairs": 2})
        self.assertIsNone(result["absolute_pass_rate_change_percentage_points"])
        self.assertEqual(result["status"], "PARTIAL")

    def test_trial_errors_dates_costs_duplicates_and_tampered_case_are_explicit(self):
        plan = self.plan()
        candidate = plan["pairs"][0]["candidate"]
        candidate.update(status="error", reason="fixture transport unavailable")
        self.assertEqual(evaluator.compare(plan, self.root)["status"], "PARTIAL")
        candidate.update(status="completed")
        for key, value in [("observed_at", "2026-99-99"), ("case_sha256", "0" * 64), ("fixture_sha256", "0" * 64),
                           ("metrics", {"cost_usd": float("nan")}), ("metrics", {"cost_usd": 10**1000}),
                           ("metrics", {"output_tokens": True}), ("metrics", {"characters_as_tokens": 12})]:
            changed = deepcopy(plan); changed["pairs"][0]["candidate"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                evaluator.compare(changed, self.root)
        changed = deepcopy(plan); changed["pairs"][0]["candidate"]["configuration"]["budget"]["output_tokens"] = 10**1000
        with self.assertRaisesRegex(ValueError, "evaluation range"):
            evaluator.compare(changed, self.root)
        changed = deepcopy(plan); changed["pairs"].append(deepcopy(changed["pairs"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate pair"):
            evaluator.compare(changed, self.root)
        candidate["trial_id"] = plan["pairs"][0]["baseline"]["trial_id"]
        with self.assertRaisesRegex(ValueError, "Duplicate trial"):
            evaluator.compare(plan, self.root)

    def test_fixture_bytes_and_record_boundary_cannot_be_swapped(self):
        plan = self.plan()
        (self.root / "fixture.json").write_text('{"different":"input"}')
        with self.assertRaisesRegex(ValueError, "Observed fixture bytes"):
            evaluator.compare(plan, self.root)
        record = {"acceptance": [{"id": "state", "subject": "synthetic-settlement", "boundary": "live-service"}], "overall_status": "GREEN"}
        with self.assertRaisesRegex(ValueError, "subjects and boundaries"):
            self.evaluate(task_record=record)

    def test_cli_reports_raw_case_hash_and_refuses_invalid_input(self):
        path = self.root / "case.json"
        raw = json.dumps(self.case).encode()
        path.write_bytes(raw)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = evaluator.main(["check", "--case", str(path), "--artifacts", str(self.artifacts)])
        self.assertEqual(code, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["case_sha256"], evaluator.digest(raw))
        path.write_text('{"schema_version":1,"acceptance":[]}')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(evaluator.main(["check", "--case", str(path), "--artifacts", str(self.artifacts)]), 2)


if __name__ == "__main__":
    unittest.main()
