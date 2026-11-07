"""Full-corpus reading remains resumable, source-bound and honest about coverage."""
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

TOOLS = next(p / "tools" for p in Path(__file__).resolve().parents if (p / "tools/read_repository.py").is_file())
spec = importlib.util.spec_from_file_location("repo_reading", TOOLS / "read_repository.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ExhaustiveReadingTests(unittest.TestCase):
    def setUp(self):
        clean_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        clean_env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TEMPLATE_DIR="")
        environment = patch.dict(os.environ, clean_env, clear=True)
        environment.start(); self.addCleanup(environment.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.ledger = self.base / "private" / "reading.sqlite"
        self.git("init", "-q")
        self.git("config", "user.name", "Reading Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "README.md").write_text("# Read all of this\n" + "αβγδ important source\n" * 35, encoding="utf-8")
        (self.repo / "AGENTS.md").write_text("Read the source and retain its meaning.\n")
        (self.repo / "empty.txt").write_bytes(b"")
        self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.DEVNULL)

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-qm", "fixture source")

    def init(self):
        return reader.init(self.repo, self.ledger, chunk_bytes=256)

    def session(self):
        value = reader.Reading(self.repo, self.ledger)
        self.addCleanup(value.close)
        return value

    def test_full_queue_preserves_exact_bytes_unicode_and_empty_files(self):
        self.init()
        reconstructed = {}
        while True:
            session = self.session()
            part = session.next()
            if part.get("reading_queue_exhausted"):
                break
            self.assertLessEqual(len(part["content"].encode()), 256)
            reconstructed[part["path"]] = reconstructed.get(part["path"], b"") + part["content"].encode()
            session.ack(part["receipt_id"], "Source contract understood; connect it to the next example.")
        for path, content in reconstructed.items():
            self.assertEqual(content, (self.repo / path).read_bytes())
        status = self.session().status()
        self.assertEqual(status["files_total"], 3)
        self.assertTrue(status["all_files_accounted_for"])
        self.assertTrue(status["all_files_read_as_text"])
        self.assertFalse(status["semantic_comprehension_verified"])

    def test_issued_chunk_does_not_count_until_acknowledged_and_resume_is_exact(self):
        self.init()
        first = self.session().next()
        self.assertEqual(first["path"], "AGENTS.md")
        self.assertEqual(self.session().next()["receipt_id"], first["receipt_id"])
        self.assertEqual(self.session().status()["files_remaining"], 3)
        self.session().ack(first["receipt_id"], "Learned the entry requirement.")
        second = self.session().next()
        self.assertNotEqual(first["receipt_id"], second["receipt_id"])
        self.assertEqual(self.session().status()["files_remaining"], 2)

    def test_unknown_or_blank_ack_cannot_claim_coverage_and_repeat_is_idempotent(self):
        self.init()
        session = self.session()
        with self.assertRaises(ValueError): session.ack("invented", "Read it")
        part = session.next()
        with self.assertRaises(ValueError): session.ack(part["receipt_id"], " ")
        session.ack(part["receipt_id"], "Learned it")
        self.assertTrue(session.ack(part["receipt_id"], "Duplicate attempt")["already_acknowledged"])
        self.assertEqual(session.status()["notes_recorded"], 1)

    def test_worktree_and_later_commits_cannot_change_pinned_reads(self):
        initial = self.init()
        (self.repo / "AGENTS.md").write_text("replacement source")
        (self.repo / "private-untracked.txt").write_text("never include")
        part = self.session().next()
        self.assertIn("retain its meaning", part["content"])
        self.assertEqual(self.session().status()["files_total"], 3)
        self.commit()
        status = self.session().status()
        self.assertFalse(status["current_head_matches_reading_revision"])
        self.assertEqual(status["commit"], initial["commit"])

    def test_binary_cannot_disappear_or_pass_by_metadata_alone(self):
        (self.repo / "image.bin").write_bytes(b"\x00\x01opaque bytes")
        self.commit(); self.init()
        part = self.session().next("image.bin")
        self.assertTrue(part["format_review_required"])
        report = self.base / "review.json"
        data = {"source_git_blob": part["source"]["blob"], "reader": "Fixture format reader", "summary": "Reviewed every declared element", "coverage": "complete", "parts_reviewed": ["all visual elements"], "unread_parts": ["one unread element"]}
        report.write_text(json.dumps(data))
        with self.assertRaises(ValueError): self.session().review("image.bin", report)
        data["unread_parts"] = []
        report.write_text(json.dumps(data))
        self.session().review("image.bin", report)
        status = self.session().status()
        self.assertEqual(status["external_review_attestations"], 1)
        self.assertFalse(status["all_files_read_as_text"])
        self.assertEqual(status["files_remaining"], 3)

    def test_external_review_cannot_bypass_readable_text(self):
        self.init()
        part = self.session().next()
        report = self.base / "review.json"
        report.write_text(json.dumps({"source_git_blob": part["blob"], "coverage": "complete", "reader": "pretend reader", "summary": "skipped", "parts_reviewed": ["all"], "unread_parts": []}))
        with self.assertRaisesRegex(ValueError, "Readable text"):
            self.session().review(part["path"], report)

    def test_incomplete_utf8_at_eof_is_external_review_not_a_zero_progress_loop(self):
        for name, content in [("incomplete.txt", b"prefix\xe2"), ("binary.bin", b"\0\xe2")]:
            (self.repo / name).write_bytes(content)
        self.commit(); self.init()
        for name in ("incomplete.txt", "binary.bin"):
            part = self.session().next(name)
            self.assertTrue(part["format_review_required"])
            self.assertNotIn("receipt_id", part)
            report = self.base / "external.json"
            report.write_text(json.dumps({"source_git_blob": part["source"]["blob"], "coverage": "complete", "reader": "byte inspector", "summary": "Read complete malformed sequence", "parts_reviewed": ["all bytes"], "unread_parts": []}))
            self.session().review(name, report)
        self.assertEqual(self.session().status()["external_review_attestations"], 2)

    def test_no_overwrite_or_ledger_inside_source_and_missing_ledger_is_not_created(self):
        with self.assertRaises(ValueError): reader.init(self.repo, self.repo / "notes.db")
        with self.assertRaises(ValueError): reader.Reading(self.repo, self.ledger)
        self.assertFalse(self.ledger.exists())
        self.init()
        original = self.ledger.read_bytes()
        with self.assertRaises(ValueError): self.init()
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_cursor_and_notes_tampering_are_detected_by_full_status(self):
        self.init()
        s = self.session(); part = s.next(); s.ack(part["receipt_id"], "Learned the entrypoint")
        with sqlite3.connect(self.ledger) as db:
            db.execute("UPDATE entries SET state='read',cursor=50 WHERE path='README.md'")
        with self.assertRaisesRegex(ValueError, "cursor"):
            self.session().status()

    def test_chunk_notes_remain_retrievable_with_bounded_pagination(self):
        self.init()
        s = self.session()
        for _ in range(3):
            part = s.next(); s.ack(part["receipt_id"], "Connected this passage to its source contract")
        page = s.notes(limit=1)
        self.assertEqual(len(page["notes"]), 1)
        self.assertEqual(page["matching_notes"], 3)
        self.assertEqual(page["next_offset"], 1)
        self.assertNotEqual(page["notes"], s.notes(offset=1, limit=1)["notes"])

    def test_symlinks_are_read_as_git_targets_without_following(self):
        if not hasattr(os, "symlink"): self.skipTest("symlink fixture unavailable")
        secret = self.base / "outside.txt"; secret.write_text("outside content must not be read")
        (self.repo / "pointer").symlink_to(secret)
        self.commit(); self.init()
        part = self.session().next("pointer")
        self.assertEqual(part["source_mode"], "120000")
        self.assertEqual(part["content"], str(secret))
        self.assertNotIn("outside content", part["content"])

    def test_invalid_cursor_is_rejected_before_a_source_read(self):
        self.init()
        with sqlite3.connect(self.ledger) as db:
            db.execute("UPDATE entries SET cursor=-1,state='reading' WHERE path='README.md'")
        with patch.object(reader, "source_slice", side_effect=AssertionError("must not read invalid offset")):
            with self.assertRaisesRegex(ValueError, "cursor"):
                self.session().next("README.md")

    def test_explicit_repository_ignores_ambient_git_directory_and_replacements(self):
        alternate = self.base / "other"; alternate.mkdir()
        for args in [("init", "-q"), ("config", "user.name", "Reading Fixture"),
                     ("config", "user.email", "fixture@example.invalid")]:
            subprocess.run(["git", "-C", str(alternate), *args], check=True, capture_output=True)
        (alternate / "different.txt").write_text("must not appear")
        subprocess.run(["git", "-C", str(alternate), "add", "--all"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(alternate), "commit", "-qm", "other fixture"], check=True, capture_output=True)
        with patch.dict(os.environ, {"GIT_DIR": str(alternate / ".git"), "GIT_WORK_TREE": str(alternate)}):
            self.init(); part = self.session().next()
        self.assertEqual(part["path"], "AGENTS.md")
        original = self.git("rev-parse", "HEAD:AGENTS.md").decode().strip()
        replacement = self.git("rev-parse", "HEAD:README.md").decode().strip()
        self.git("replace", original, replacement)
        self.assertEqual(self.session().next()["content"], (self.repo / "AGENTS.md").read_text())

    def test_subdirectory_entry_cannot_store_private_ledger_inside_repository(self):
        nested = self.repo / "docs"; nested.mkdir()
        with self.assertRaisesRegex(ValueError, "outside"):
            reader.init(nested, self.repo / "private-notes.sqlite")
        self.assertFalse((self.repo / "private-notes.sqlite").exists())

    def test_pending_receipt_binds_source_identity_and_line_positions(self):
        self.init(); session = self.session(); part = session.next()
        original = json.loads(session.db.execute("SELECT pending FROM entries WHERE path=?", (part["path"],)).fetchone()[0])
        for key, value in [("blob", "0" * 40), ("commit", "0" * 40), ("next_line", 999), ("end_byte", 0)]:
            changed = deepcopy(original); changed["receipt"][key] = value
            changed["id"] = reader.digest(changed["receipt"])
            with session.db:
                session.db.execute("UPDATE entries SET pending=? WHERE path=?", (reader.canonical(changed), part["path"]))
            with self.subTest(key=key), self.assertRaises(ValueError):
                session.ack(changed["id"], "A malformed receipt must not advance coverage")
        self.assertEqual(session.status()["notes_recorded"], 0)

    def test_rehashed_notes_still_require_possible_pinned_source_coverage(self):
        self.init(); session = self.session(); part = session.next(); session.ack(part["receipt_id"], "Read the complete entry")
        original = dict(session.db.execute("SELECT * FROM notes").fetchone())
        record = json.loads(original["record"])
        for key, value in [("blob", "0" * 40), ("commit", "0" * 40), ("end_byte", record["end_byte"] + 1)]:
            changed = deepcopy(record); changed[key] = value
            receipt = reader.digest({k: v for k, v in changed.items() if k not in {"note", "noted_at"}})
            with session.db:
                session.db.execute("UPDATE notes SET record=?,receipt=?,hash=?", (reader.canonical(changed), receipt, reader.digest([original["previous"], changed])))
                session.db.execute("UPDATE entries SET cursor=? WHERE path=?", (changed["end_byte"], part["path"]))
            with self.subTest(key=key), self.assertRaises(ValueError):
                session.status()
        # This checks structural consistency, not an authentication claim about a ledger owner.

    def test_status_and_notes_use_a_consistent_concurrent_snapshot(self):
        self.init()
        with sqlite3.connect(self.ledger) as db:
            db.execute("PRAGMA journal_mode=WAL")
        observer = self.session(); writer = self.session(); part = writer.next()
        original = observer.verify_notes
        def read_then_ack():
            original()
            writer.ack(part["receipt_id"], "A concurrent reader finishes this chunk")
        with patch.object(observer, "verify_notes", read_then_ack):
            snapshot = observer.status()
        self.assertEqual(snapshot["files_remaining"], 3)
        self.assertEqual(snapshot["notes_recorded"], 0)
        self.assertEqual(observer.status()["files_remaining"], 2)
        part = writer.next()
        with patch.object(observer, "verify_notes", read_then_ack):
            page = observer.notes()
        self.assertEqual(page["matching_notes"], 1)
        self.assertEqual(observer.notes()["matching_notes"], 2)

    def test_concurrent_resumes_acknowledge_each_chunk_once(self):
        self.init()
        def read_to_end(worker):
            session = reader.Reading(self.repo, self.ledger)
            try:
                for _ in range(100):
                    part = session.next()
                    if part.get("reading_queue_exhausted"):
                        return
                    session.ack(part["receipt_id"], f"Worker {worker} read the full issued source chunk")
                raise AssertionError("bounded fixture did not finish")
            finally:
                session.close()
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(read_to_end, range(3)))
        status = self.session().status()
        self.assertTrue(status["all_files_read_as_text"])
        self.assertEqual(status["acknowledged_source_bytes"], sum(p.stat().st_size for p in self.repo.iterdir() if p.is_file()))
        self.assertEqual(status["notes_recorded"], len(self.session().notes(limit=100)["notes"]))


if __name__ == "__main__":
    unittest.main()
