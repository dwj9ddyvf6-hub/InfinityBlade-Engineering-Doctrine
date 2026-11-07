"""Source identity, source preservation and honest recall after change."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("retrieval_provenance_fixture", ROOT / "skills/memory-recall-systems/tools/memory_search.py")
search = importlib.util.module_from_spec(spec); spec.loader.exec_module(search)


class RetrievalProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = self.root / "notes"; self.notes.mkdir()
        self.source = self.notes / "MEMORY.md"; self.source.write_text("# Source\nneedle alpha\n")
        self.db = self.root / "index.db"

    def build(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return search.build([self.notes], self.db, **kwargs)

    def test_changed_and_missing_sources_are_explicit_and_current_only_recovers(self):
        self.build()
        before = search.query("needle", db_path=self.db)[0]
        self.assertEqual(before["source_status"], "matches_index")
        self.source.write_text("# Source\nneedle beta\n")
        stale = search.query("needle", db_path=self.db)[0]
        self.assertEqual(stale["source_status"], "changed_since_index")
        self.assertIn("alpha", stale["text"])
        self.assertNotEqual(stale["indexed_sha256"], stale["current_sha256"])
        self.assertEqual(search.query("needle", db_path=self.db, current_only=True), [])
        self.build()
        self.assertIn("beta", search.query("needle", db_path=self.db, current_only=True)[0]["text"])
        self.source.unlink()
        self.assertEqual(search.query("needle", db_path=self.db)[0]["source_status"], "source_missing")

    def test_index_cannot_overwrite_source_or_hardlink_to_source(self):
        original = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            search.build([self.notes], self.source)
        self.assertEqual(self.source.read_bytes(), original)
        hardlink = self.root / "hardlink.db"; hardlink.hardlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            search.build([self.notes], hardlink)
        self.assertEqual(self.source.read_bytes(), original)

    def test_mid_build_source_change_preserves_old_index(self):
        self.build(); original = self.db.read_bytes()
        chunks = search.chunk_file
        def changed(path, data=None):
            self.source.write_text("changed during build")
            yield from chunks(path, data)
        with patch.object(search, "chunk_file", changed), self.assertRaisesRegex(ValueError, "source bytes changed"):
            self.build()
        self.assertEqual(self.db.read_bytes(), original)

    def test_full_status_detects_unqueried_changes_and_new_sources(self):
        self.build()
        self.assertTrue(search.index_status(self.db)["current"])
        (self.notes / "new.md").write_text("different topic")
        result = search.index_status(self.db)
        self.assertFalse(result["current"])
        self.assertEqual(result["new_unindexed_paths"], [str(self.notes / "new.md")])
        self.build(); self.assertTrue(search.index_status(self.db)["current"])

    def test_deliberate_empty_rebuild_clears_removed_memory(self):
        self.build(); self.source.unlink()
        with self.assertRaises(ValueError): self.build()
        self.build(allow_empty=True)
        self.assertEqual(search.query("needle", db_path=self.db), [])
        self.assertTrue(search.index_status(self.db)["current"])

    def test_canary_cannot_pass_against_changed_source(self):
        self.build()
        cases = self.root / "canary.json"; cases.write_text(json.dumps([{"q": "needle", "expect": "MEMORY.md"}]))
        self.source.write_text("unrelated replacement")
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "canary failed"):
            search.canary(cases, strict=True, db_path=self.db)

    def test_unreadable_subtree_preserves_old_index_and_prevents_current_verdict(self):
        restricted = self.notes / "restricted"; restricted.mkdir()
        source = restricted / "kept.md"; source.write_text("# Preserved\nzebra evidence\n")
        self.build(); old_index = self.db.read_bytes(); original = os.scandir
        def deny_subtree(path):
            if Path(path) == restricted:
                raise PermissionError("synthetic unreadable source directory")
            return original(path)
        with patch.object(os, "scandir", deny_subtree):
            with self.assertRaises(PermissionError): self.build()
            status = search.index_status(self.db)
        self.assertEqual(self.db.read_bytes(), old_index)
        self.assertFalse(status["current"])
        self.assertEqual(status["inventory_error"], "PermissionError")
        self.assertIsNone(status["new_unindexed_paths"])
        self.assertEqual(search.query("zebra", db_path=self.db)[0]["path"], str(source))

    def test_future_markdown_destination_is_rejected_before_creating_any_output(self):
        future = self.notes / "not-created" / "index.md"
        original = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "become an indexed"):
            search.build([self.notes], future)
        self.assertFalse(future.parent.exists())
        self.assertFalse(Path(str(future) + ".build-lock.sqlite3").exists())
        self.assertEqual(self.source.read_bytes(), original)
        # A Markdown-looking database outside the selected estate does not become source.
        external = self.root / "outside.md"
        with contextlib.redirect_stdout(io.StringIO()): search.build([self.notes], external)
        self.assertTrue(search.index_status(external)["current"])

    def test_build_lock_cannot_alias_source_or_destination(self):
        lock = Path(str(self.db) + ".build-lock.sqlite3")
        lock.hardlink_to(self.source); original = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.build()
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(lock.read_bytes(), original)
        self.assertFalse(self.db.exists())
        lock.unlink(); self.build(); old_index = self.db.read_bytes()
        lock.unlink(); lock.hardlink_to(self.db)
        with self.assertRaisesRegex(ValueError, "different files"):
            self.build()
        self.assertEqual(self.db.read_bytes(), old_index)

    def test_current_only_fills_k_after_skipping_a_higher_ranked_stale_hit(self):
        alternative = self.notes / "other.md"; alternative.write_text("# Source\nneedle alpha\n")
        self.build()
        self.assertEqual(search.query("needle", k=1, db_path=self.db)[0]["path"], str(self.source))
        self.source.write_text("replacement without the searched fact")
        self.assertEqual(search.query("needle", k=1, db_path=self.db)[0]["source_status"], "changed_since_index")
        current = search.query("needle", k=1, db_path=self.db, current_only=True)
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["path"], str(alternative))
        self.assertEqual(current[0]["source_status"], "matches_index")

    def test_query_sees_old_complete_index_until_atomic_replacement(self):
        self.build(); self.source.write_text("# Source\nneedle beta\n")
        original = search.chunk_file; observations = []
        def query_during_build(path, data=None):
            hit = search.query("needle", db_path=self.db)[0]
            observations.append((hit["text"], hit["source_status"]))
            yield from original(path, data)
        with patch.object(search, "chunk_file", query_during_build): self.build()
        self.assertEqual(len(observations), 1)
        self.assertIn("alpha", observations[0][0])
        self.assertEqual(observations[0][1], "changed_since_index")
        final = search.query("needle", db_path=self.db, current_only=True)[0]
        self.assertIn("beta", final["text"])

    def test_legacy_schema_remains_queryable_without_claiming_current_source(self):
        with sqlite3.connect(self.db) as db:
            db.execute("CREATE TABLE chunks(path TEXT,heading TEXT,line INTEGER,text TEXT)")
            db.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(path,heading,text,content='chunks',content_rowid='rowid')")
            values = (str(self.source), "Legacy", "legacy needle")
            db.execute("INSERT INTO chunks VALUES(?,?,1,?)", values)
            db.execute("INSERT INTO chunks_fts(rowid,path,heading,text) VALUES(1,?,?,?)", values)
        hit = search.query("needle", db_path=self.db)[0]
        self.assertEqual(hit["source_status"], "legacy_index_unverified")
        self.assertEqual(search.query("needle", db_path=self.db, current_only=True), [])
        self.assertEqual(search.index_status(self.db)["status"], "legacy_index_unverified")


if __name__ == "__main__": unittest.main()
