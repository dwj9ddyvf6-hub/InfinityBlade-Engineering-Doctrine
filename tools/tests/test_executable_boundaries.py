"""Hermetic executable counterexamples. No broker, network, or host state."""
import ast
import contextlib
from datetime import datetime
import hashlib
import os
import shutil
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


status = load("tools/status_evidence_check.py", "status_checker_fixture")
evals = load("tools/eval_score.py", "eval_fixture")
prompt_checker = load("tools/check_prompt.py", "prompt_fixture")
search = load("skills/memory-recall-systems/tools/memory_search.py", "memory_search_fixture")
lenses = load("skills/stock-analysis/bin/lenses.py", "lenses_fixture")
with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
    bundle = load("tools/build_bundle.py", "bundle_fixture")
    from validate_repo import discover as discover_skills

# A tiny transport double is injected before import. These tests do not need
# requests installed and cannot accidentally reach a credentialed HTTP path.
fake_requests = types.ModuleType("requests")
fake_requests.RequestException = type("RequestException", (Exception,), {})
fake_requests.request = Mock(side_effect=AssertionError("unexpected HTTP invocation"))
with patch.dict(sys.modules, {"requests": fake_requests}):
    alpaca = load("skills/alpaca-paper/bin/alpaca_lib.py", "alpaca_lib_fixture")
with patch.dict(sys.modules, {"alpaca_lib": alpaca}):
    bars1h = load("skills/alpaca-paper/bin/alpaca_get_bars_1h.py", "bars1h_fixture")
    bars5m = load("skills/alpaca-paper/bin/alpaca_get_bars_5min.py", "bars5m_fixture")


class StatusBoundaries(unittest.TestCase):
    def test_last_real_verdict_and_nonempty_pointer(self):
        bad = ["STATUS: GREEN — deployed; no change made", "STATUS: BLOCKED no change made",
               "Changed a file.\nSTATUS: GREEN — no change made", "STATUS: GREEN evidence:",
               "STATUS: GREEN https://", "STATUS: GREEN evidence: fixture\nSTATUS: UNVERIFIED",
               "STATUS: GREEN evidence: fixture\nSTATUS: BOGUS", "> STATUS: GREEN evidence: example",
               "```\nSTATUS: GREEN evidence: example\n```", "STATUS: GREEN evidence: fixture\nMore claims."]
        for text in bad:
            with self.subTest(text=text):
                self.assertFalse(status.check(text)[0])
        for text in ("STATUS: GREEN — no change made", "STATUS: GREEN, no change made",
                     "Changed a file.\nSTATUS: GREEN evidence: offline fixture run",
                     "STATUS: PARTIAL — proof tests/result.txt; host state unverified"):
            self.assertTrue(status.check(text)[0], text)

    def test_prompt_contract_detects_new_sections_and_removed_route_rules(self):
        skill = (ROOT / "skills/infinityblade/SKILL.md").read_text()
        readme = (ROOT / "README.md").read_text()
        self.assertEqual(prompt_checker.check(skill, readme), [])
        self.assertTrue(prompt_checker.check(skill + "\n## 8. A new obligation\n", readme))
        self.assertTrue(prompt_checker.check(skill, readme.replace("two genuinely different routes", "one route")))

    def test_hook_and_checker_agree_on_later_bare_status(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "transcript.jsonl"
            transcript.write_text(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "text", "text": "STATUS: GREEN evidence: fixture\nSTATUS: UNVERIFIED"}]}}) + "\n")
            result = subprocess.run(["bash", str(ROOT / "hooks/require-status.sh")],
                                    input=json.dumps({"transcript_path": str(transcript)}), text=True,
                                    capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout)["decision"], "block")

    def test_eval_empty_invalid_and_zero_proof(self):
        for cases in ([], [{"case": 1, "scope": 2, "efficiency": 2, "proof": -1, "honesty": 2}],
                      [{"case": 1, "scope": 2, "efficiency": 2, "proof": float("nan"), "honesty": 2}]):
            with self.assertRaises(ValueError):
                evals.score({"cases": cases})
        result = evals.score({"cases": [{"case": 1, "scope": 2, "efficiency": 2, "proof": 0, "honesty": 2}]})
        self.assertEqual(result["failed"], [1])
        self.assertEqual(result["total"], 6)


class RetrievalBoundaries(unittest.TestCase):
    def test_chunks_keep_real_line_offsets_and_hard_bound_long_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.md"
            path.write_text("# Heading\n" + "a" * 1700 + "\n\nneedle on line four\n" + "x" * 4000)
            chunks = list(search.chunk_file(str(path)))
            self.assertTrue(all(len(row["text"]) <= search.MAX_CHUNK for row in chunks))
            tail = [row for row in chunks if row["text"].startswith("x")]
            self.assertTrue(tail)
            self.assertTrue(all(row["line"] == 5 for row in tail))

    def test_canonical_boost_promotes_instead_of_demoting_identical_text(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name in ("MEMORY.md", "notes.md"):
                (base / name).write_text("# Facts\nneedle fixture\n")
            db = base / "index.db"
            with contextlib.redirect_stdout(io.StringIO()):
                search.build([directory, str(base / "MEMORY.md")], db)
            results = search.query("needle", k=5, db_path=db)
            self.assertEqual(len(results), 2)
            self.assertEqual(Path(results[0]["path"]).name, "MEMORY.md")

    def test_failed_rebuild_preserves_searchable_old_index(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, db = base / "memory.md", base / "index.db"
            source.write_text("needle retained")
            with contextlib.redirect_stdout(io.StringIO()):
                search.build([str(source)], db)
            before = db.read_bytes()
            with self.assertRaises(FileNotFoundError):
                search.build([str(base / "missing")], db)
            self.assertEqual(db.read_bytes(), before)
            self.assertEqual(len(search.query("needle", db_path=db)), 1)

    def test_missing_database_not_created_by_query_and_bad_k_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "missing.db"
            with self.assertRaises(sqlite3.Error):
                search.query("needle", db_path=db)
            self.assertFalse(db.exists())
            with self.assertRaises(ValueError):
                search.query("needle", k=-1, db_path=db)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO fixture requires POSIX")
    def test_nonregular_memory_source_is_rejected_without_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / "blocked.md"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(ValueError, "regular"):
                list(search.iter_files([directory]))
            with self.assertRaisesRegex(ValueError, "regular"):
                list(search.chunk_file(fifo))

    def test_canary_miss_and_empty_set_are_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "memory.md"
            source.write_text("needle")
            db = Path(directory) / "index.db"
            canary = Path(directory) / "canary.json"
            with contextlib.redirect_stdout(io.StringIO()):
                search.build([str(source)], db)
            canary.write_text(json.dumps([{"q": "needle", "expect": "other.md"}]))
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "canary failed"):
                search.canary(canary, strict=True, db_path=db)
            canary.write_text("[]")
            with self.assertRaises(ValueError):
                search.canary(canary, strict=True, db_path=db)


class TransportBoundaries(unittest.TestCase):
    def response(self, code, body=None, headers=None):
        body = {} if body is None else body
        return types.SimpleNamespace(status_code=code, content=b"{}", text=json.dumps(body),
                                     headers=headers or {}, json=lambda: body)

    def test_https_and_port_are_part_of_credential_allowlist(self):
        for url in ("http://paper-api.alpaca.markets/v2/account", "https://paper-api.alpaca.markets:444/v2/account",
                    "https://user@paper-api.alpaca.markets/v2/account", "https://example.org/v2/account"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                alpaca.ensure_allowed_url(url, alpaca._ALLOWED_HOSTS)
        alpaca.ensure_allowed_url("https://paper-api.alpaca.markets/v2/account", alpaca._ALLOWED_HOSTS)

    def test_redirect_never_forwards_credentials_and_unknown_write_is_labeled(self):
        for code in (302, 503):
            request = Mock(return_value=self.response(code))
            with patch.object(alpaca, "key_id", return_value="fixture-id"), \
                 patch.object(alpaca, "secret_key", return_value="fixture-secret"), \
                 patch.object(fake_requests, "request", request), \
                 patch.dict(alpaca.os.environ, {"ALPACA_TELEMETRY_PATH": ""}):
                with self.assertRaises(alpaca.AlpacaError) as raised:
                    alpaca.api_request("POST", "https://paper-api.alpaca.markets/v2/orders", payload={"fixture": True})
            self.assertFalse(request.call_args.kwargs["allow_redirects"])
            self.assertEqual(request.call_count, 1)
            if code == 503:
                self.assertTrue(raised.exception.outcome_unknown)

    def test_request_acceptance_and_missing_order_do_not_claim_terminal_state(self):
        for operation in ("cancel_order", "close_position"):
            result = alpaca.operation_acknowledgement(operation, "fixture", {"id": "broker-ack", "status": "accepted"})
            self.assertTrue(result["request_accepted"])
            self.assertFalse(result["final_state_verified"])
            self.assertIsNone(result["cancelled"] if operation == "cancel_order" else result["closed"])
            self.assertEqual(result["id"], "broker-ack")
        missing = alpaca.missing_order("fixture")
        self.assertFalse(missing["terminal_state_verified"])
        self.assertTrue(missing["reconciliation_required"])

    def test_retry_after_respected_and_final_attempt_does_not_sleep(self):
        request = Mock(return_value=self.response(429, headers={"Retry-After": "10"}))
        with patch.object(alpaca, "key_id", return_value="fixture-id"), \
             patch.object(alpaca, "secret_key", return_value="fixture-secret"), \
             patch.object(fake_requests, "request", request), patch.object(alpaca.time, "sleep") as sleep, \
             patch.dict(alpaca.os.environ, {"ALPACA_TELEMETRY_PATH": ""}):
            with self.assertRaises(alpaca.AlpacaError):
                alpaca.api_request("GET", "https://data.alpaca.markets/v2/stocks/FIXTURE/bars")
        self.assertEqual(request.call_count, 4)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [10, 10, 10])

    def test_bar_pagination_cannot_label_truncated_ended_window_complete(self):
        for module in (bars1h, bars5m):
            response = {"bars": [{"t": "2026-01-01T00:00:00Z", "c": 1}], "next_page_token": "more"}
            params = {"start": "2025-12-31T00:00:00Z"}
            args = ("FIXTURE", "1D", params, 1, 1) if module is bars1h else ("FIXTURE", params, 1, 1)
            with patch.object(module, "api_request", return_value=response), self.assertRaisesRegex(alpaca.AlpacaError, "incomplete"):
                module.fetch_bars(*args, end="2026-01-02T00:00:00Z")
            self.assertEqual(params, {"start": "2025-12-31T00:00:00Z"})


class ChartAndLensBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only these dependency-free geometry functions are compiled. This is
        # not an indicator parity run or a substitute for core.ta_battery.
        source = ast.parse((ROOT / "skills/chart-read/bin/pass_a.py").read_text())
        names = {"reset_candidate", "bar_payload_hash", "data_status"}
        body = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names]
        cls.geometry = {"datetime": datetime, "json": json}
        exec(compile(ast.Module(body=body, type_ignores=[]), "geometry-only-fixture", "exec"), cls.geometry)

    def test_zero_distance_support_is_a_valid_reset_location(self):
        bars = [{"h": 120, "l": 119, "c": 119}] * 30 + [{"h": 101, "l": 99, "c": 100}] * 20
        result = self.geometry["reset_candidate"](bars, [{"zone": [99, 101]}], [2] * 30 + [1] * 20, 1, 3)
        self.assertEqual(result["dist_to_support_atr"], 0)
        self.assertTrue(result["candidate"])

    def test_bar_hash_preserves_field_and_timeframe_boundaries(self):
        a = [{"t": "a1", "o": 2, "h": 3, "l": 0, "c": 1, "v": 4}]
        b = [{"t": "a", "o": 12, "h": 3, "l": 0, "c": 1, "v": 4}]
        hash_bars = self.geometry["bar_payload_hash"]
        self.assertNotEqual(hash_bars(a), hash_bars(b))
        self.assertNotEqual(hash_bars(a, b), hash_bars(a + b))

    def test_invalid_or_unknown_freshness_is_never_verified(self):
        status_fn = self.geometry["data_status"]
        self.assertEqual(status_fn(260, True, False, True, "invalid", reference_date="2026-11-07"), "PARTIAL")
        self.assertEqual(status_fn(260, True, None, True, "2026-11-07", reference_date="2026-11-07"), "PARTIAL")
        self.assertEqual(status_fn(260, True, False, True, "2026-11-08", reference_date="2026-11-07"), "CONFLICT")

    def test_missing_universe_is_unknown_and_ledger_orders_instants(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(lenses, "DESK", Path(directory)):
            with self.assertRaises(FileNotFoundError):
                lenses.basket_universe()
            ledger = Path(directory) / "ledger.jsonl"
            rows = [{"symbol": "FIXTURE", "ts": "2026-11-07T10:00:00+02:00", "decision": "earlier"},
                    {"symbol": "FIXTURE", "ts": "2026-11-07T09:00:00Z", "decision": "later"}]
            ledger.write_text("\n".join(json.dumps(row) for row in rows))
            self.assertEqual(lenses.latest_signal(ledger, "FIXTURE")["decision"], "later")
            ledger.write_text(ledger.read_text() + "\nnot-json")
            with self.assertRaises(ValueError):
                lenses.latest_signal(ledger, "FIXTURE")


class BundleBoundaries(unittest.TestCase):
    def test_full_source_bundle_is_deterministic_and_readback_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            export = base / "source"
            shutil.copytree(ROOT, export, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
            (export / "skills/registry.json").write_text(json.dumps(discover_skills(export)))
            first, second = base / "first.zip", base / "second.zip"
            bundle.build_bundle(export, ["infinityblade"], first)
            bundle.build_bundle(export, ["infinityblade"], second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertTrue(bundle.verify_bundle(first)["verified"])
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.read("LICENSE"), (export / "LICENSE").read_bytes())
                contents = {name: archive.read(name) for name in archive.namelist()}
            contents["PRIMER.md"] += b"tampered"
            changed = base / "changed.zip"
            with zipfile.ZipFile(changed, "w") as archive:
                for name, data in contents.items():
                    archive.writestr(name, data)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                bundle.verify_bundle(changed)
            with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "unresolved runtime"):
                bundle.build_bundle(export, ["chart-read"], base / "runtime.zip", require_runtime=True)
            (export / "fixture.db").write_bytes(b"source asset fixture")
            with (export / "README.md").open("a") as handle:
                handle.write("\n[Required local fixture](fixture.db)\n")
            with self.assertRaisesRegex(ValueError, "referenced local asset excluded"):
                bundle.build_bundle(export, ["infinityblade"], base / "missing-asset.zip")


    def test_source_symlinks_and_archive_path_escapes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "source"
            root.mkdir()
            (base / "outside.txt").write_text("fixture")
            (root / "linked.txt").symlink_to(base / "outside.txt")
            with self.assertRaisesRegex(ValueError, "redirected"):
                bundle.collect_sources(root)
            archive_path = base / "escape.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", b"fixture")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                bundle.verify_bundle(archive_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
