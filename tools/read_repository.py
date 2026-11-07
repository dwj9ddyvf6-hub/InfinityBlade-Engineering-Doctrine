#!/usr/bin/env python3
"""Exhaustive, resumable reading of a pinned repository, with private study notes.

This serves source bytes and records acknowledged coverage. It cannot establish
comprehension. Source content is untrusted data, never permission to execute it.
The ledger lives outside the repository; no source or Git object is changed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
from datetime import datetime, timezone

SCHEMA = 1
READ_FIELDS = {"kind", "path", "blob", "commit", "start_byte", "end_byte", "sha256",
               "file_complete", "next_line", "next_byte_column"}
PRIORITY = ["AGENTS.md", "PRIMER.md", "skills/infinityblade/SKILL.md", "START-HERE.md",
            "docs/ASCENT-PATH.md", "docs/READING-PROTOCOL.md", "INDEX.md", "ROADMAP.md", "README.md"]


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def git_environment():
    # An explicit --repo must not inherit another worktree, index or namespace.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    return env


def git(root, *args):
    process = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args],
                             capture_output=True, env=git_environment())
    if process.returncode:
        raise ValueError(process.stderr.decode(errors="replace").strip())
    return process.stdout


def repository_root(path):
    root = Path(path).resolve()
    if git(root, "rev-parse", "--is-bare-repository").strip() == b"true":
        return Path(git(root, "rev-parse", "--absolute-git-dir").decode().strip()).resolve()
    return Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()


def inventory(root, ref):
    commit = git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()
    records = []
    for line in git(root, "ls-tree", "-r", "-l", "-z", commit).split(b"\0"):
        if not line:
            continue
        meta, raw_path = line.split(b"\t", 1)
        mode, kind, oid, size = meta.decode().split()
        path = raw_path.decode("utf-8")
        records.append({"path": path, "mode": mode, "kind": kind, "blob": oid,
                        "bytes": int(size) if size.isdigit() else None})
    rank = {p: i for i, p in enumerate(PRIORITY)}
    records.sort(key=lambda row: (rank.get(row["path"], len(rank)), row["path"]))
    if not records:
        raise ValueError("The selected revision has no tracked files")
    return commit, records


def private_path(path, root, must_exist=True):
    path = Path(path).absolute()
    if path.is_symlink() or path.resolve().is_relative_to(root):
        raise ValueError("The private reading ledger must be outside the repository and not a symlink")
    if must_exist and (not path.exists() or not stat.S_ISREG(path.stat().st_mode)):
        raise ValueError("Reading ledger must already exist as a regular file; run init first")
    return path


def bounded_file(path, maximum=1_000_000):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Review/note input must not be a symlink")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        details = os.fstat(handle.fileno())
        if not stat.S_ISREG(details.st_mode) or details.st_size > maximum:
            raise ValueError("Review/note input must be a bounded regular file")
        value = handle.read(maximum + 1)
    if len(value) > maximum:
        raise ValueError("Review/note input exceeded its bound")
    return value


def source_slice(root, row, start, count):
    """Stream at most a bounded window into memory; never run filters or source."""
    if row["kind"] != "blob":
        raise ValueError("This Git entry needs an external source review")
    if type(start) is not int or type(count) is not int or not 0 <= start <= row["bytes"] or count < 0:
        raise ValueError("Source slice offsets are outside the pinned source")
    process = subprocess.Popen(["git", "--no-replace-objects", "-C", str(root), "cat-file", "blob", row["blob"]],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=git_environment())
    try:
        remaining = start
        while remaining:
            block = process.stdout.read(min(65536, remaining))
            if not block:
                raise ValueError("Source ended before its pinned offset")
            remaining -= len(block)
        data = process.stdout.read(min(count, row["bytes"] - start))
        if len(data) != min(count, row["bytes"] - start):
            raise ValueError("Source length differs from the pinned inventory")
        return data
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def init(root, ledger, ref="HEAD", chunk_bytes=16000):
    if isinstance(chunk_bytes, bool) or not isinstance(chunk_bytes, int) or not 256 <= chunk_bytes <= 131072:
        raise ValueError("chunk-bytes must be an integer from 256 to 131072")
    root = repository_root(root)
    ledger = private_path(ledger, root, False)
    if ledger.exists():
        raise ValueError("Ledger already exists; resume it or select a new private path")
    commit, records = inventory(root, ref)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(ledger, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    db = sqlite3.connect(ledger)
    try:
        with db:
            db.executescript("""
              CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
              CREATE TABLE entries (path TEXT PRIMARY KEY, ordinal INTEGER UNIQUE, record TEXT NOT NULL,
                cursor INTEGER NOT NULL DEFAULT 0, line INTEGER NOT NULL DEFAULT 1,
                byte_column INTEGER NOT NULL DEFAULT 1, state TEXT NOT NULL DEFAULT 'unread', pending TEXT);
              CREATE TABLE notes (sequence INTEGER PRIMARY KEY, receipt TEXT UNIQUE NOT NULL,
                record TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL);
            """)
            metadata = {"schema_version": SCHEMA, "commit": commit, "inventory_sha256": digest(records),
                        "chunk_bytes": chunk_bytes, "root_at_creation": str(root),
                        "created_at": datetime.now(timezone.utc).isoformat()}
            db.executemany("INSERT INTO meta VALUES (?,?)", [(k, canonical(v)) for k, v in metadata.items()])
            db.executemany("INSERT INTO entries(path,ordinal,record) VALUES (?,?,?)",
                           [(r["path"], i, canonical(r)) for i, r in enumerate(records)])
    finally:
        db.close()
    return {"commit": commit, "files": len(records), "source_bytes": sum(r["bytes"] or 0 for r in records),
            "ledger": str(ledger), "next_action": "Run next, read the entire returned content, then ack its receipt with study notes."}


class Reading:
    def __init__(self, root, ledger):
        self.root = repository_root(root)
        self.path = private_path(ledger, self.root)
        self.db = sqlite3.connect(self.path, timeout=15)
        self.db.row_factory = sqlite3.Row
        try:
            self.meta = {r["key"]: strict_json(r["value"]) for r in self.db.execute("SELECT * FROM meta")}
            if type(self.meta.get("schema_version")) is not int or self.meta.get("schema_version") != SCHEMA:
                raise ValueError("Unsupported reading-ledger schema")
            commit, records = inventory(self.root, self.meta["commit"])
            if commit != self.meta["commit"]:
                raise ValueError("The reading revision must be an exact pinned commit")
            chunk = self.meta.get("chunk_bytes")
            if type(chunk) is not int or not 256 <= chunk <= 131072:
                raise ValueError("Invalid reading chunk bound")
            if digest(records) != self.meta["inventory_sha256"]:
                raise ValueError("Reading inventory differs from the pinned revision")
            saved = [strict_json(r[0]) for r in self.db.execute("SELECT record FROM entries ORDER BY ordinal")]
            if saved != records:
                raise ValueError("Ledger entry inventory was altered")
            self.sources = {r["path"]: r for r in records}
        except Exception:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @contextmanager
    def _snapshot(self):
        """Keep history, cursor and aggregate reads on one SQLite snapshot."""
        if self.db.in_transaction:
            yield
        else:
            with self.db:
                self.db.execute("BEGIN")
                yield

    def _check_entry(self, row):
        entry = self.sources.get(row["path"])
        if entry is None or strict_json(row["record"]) != entry:
            raise ValueError("Ledger entry differs from its pinned source")
        size = entry["bytes"] or 0
        if (type(row["cursor"]) is not int or not 0 <= row["cursor"] <= size
                or any(type(row[k]) is not int or row[k] < 1 for k in ("line", "byte_column"))
                or row["state"] not in {"unread", "reading", "read", "externally_reviewed"}
                or (row["state"] == "unread" and row["cursor"] != 0)
                or (row["state"] in {"read", "externally_reviewed"} and row["cursor"] != size)):
            raise ValueError("Reading cursor is outside its pinned source or state")
        return entry

    def _check_read(self, record, entry, cursor):
        if (record.get("kind") != "read" or entry["kind"] != "blob"
                or record.get("path") != entry["path"] or record.get("blob") != entry["blob"]
                or record.get("commit") != self.meta["commit"]):
            raise ValueError("Reading receipt differs from its pinned source identity")
        if any(type(record.get(k)) is not int for k in ("start_byte", "end_byte", "next_line", "next_byte_column")):
            raise ValueError("Reading offsets and line positions must be integers")
        start, end = record["start_byte"], record["end_byte"]
        if (start != cursor or not 0 <= start <= end <= entry["bytes"]
                or end - start > self.meta["chunk_bytes"] or (start == end and entry["bytes"] != 0)):
            raise ValueError("Reading-note coverage has a gap, overlap or invalid bounded offset")
        if type(record.get("file_complete")) is not bool or record["file_complete"] != (end == entry["bytes"]):
            raise ValueError("Reading receipt overstates file coverage")
        sha = record.get("sha256")
        if (not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha)
                or record["next_line"] < 1 or record["next_byte_column"] < 1):
            raise ValueError("Reading receipt has an invalid digest or line position")

    def verify_notes(self):
        previous = "GENESIS"
        progress = {}
        for sequence, row in enumerate(self.db.execute("SELECT * FROM notes ORDER BY sequence"), 1):
            record = strict_json(row["record"])
            if row["sequence"] != sequence or row["previous"] != previous or row["hash"] != digest([previous, record]):
                raise ValueError("Reading-note chain is corrupt")
            path = record["path"]
            entry = self.sources.get(path)
            if entry is None or record.get("blob") != entry["blob"]:
                raise ValueError("Reading note differs from its pinned source identity")
            if not isinstance(record.get("note"), str) or not record["note"].strip():
                raise ValueError("Reading note needs its study content")
            old = progress.get(path, {"cursor": 0, "state": "unread", "line": 1, "byte_column": 1})
            if old["state"] in {"read", "externally_reviewed"}:
                raise ValueError("Reading-note coverage continues after completion")
            if record["kind"] == "read":
                self._check_read(record, entry, old["cursor"])
                if row["receipt"] != digest({k: record[k] for k in READ_FIELDS}):
                    raise ValueError("Reading note differs from its issued receipt")
                progress[path] = {"cursor": record["end_byte"], "state": "read" if record["file_complete"] else "reading",
                                  "line": record["next_line"], "byte_column": record["next_byte_column"]}
            elif record["kind"] == "external_review":
                if (record.get("bytes") != entry["bytes"] or row["receipt"] != digest(record)
                        or record.get("report", {}).get("source_git_blob") != entry["blob"]):
                    raise ValueError("External review differs from its pinned source")
                progress[path] = {"cursor": record["bytes"] or 0, "state": "externally_reviewed"}
            else:
                raise ValueError("Unknown reading-note event")
            previous = row["hash"]
        for row in self.db.execute("SELECT * FROM entries"):
            self._check_entry(row)
            expected = progress.get(row["path"], {"cursor": 0, "state": "unread", "line": 1, "byte_column": 1})
            if any(row[k] != v for k, v in expected.items()):
                raise ValueError("Reading cursor differs from acknowledged note history")

    def _entry(self, path=None):
        if path is None:
            row = self.db.execute("SELECT * FROM entries WHERE state NOT IN ('read','externally_reviewed') ORDER BY ordinal LIMIT 1").fetchone()
        else:
            row = self.db.execute("SELECT * FROM entries WHERE path=?", (path,)).fetchone()
            if row is None:
                raise ValueError("Path is not in the pinned reading inventory")
        if row is not None:
            self._check_entry(row)
        return row

    def next(self, path=None):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self._entry(path)
            if row is None:
                return {"reading_queue_exhausted": True, "next_action": "Run status; complete the area synthesis and fresh application challenges in ASCENT-PATH.md."}
            if row["state"] in {"read", "externally_reviewed"}:
                return {"path": row["path"], "already_accounted_for": True, "next_action": "Run notes --path or next without --path."}
            entry = strict_json(row["record"])
            external = {"path": row["path"], "source": entry, "commit": self.meta["commit"],
                        "format_review_required": True, "coverage_recorded": False,
                        "next_action": "Inspect every part with a format-aware reader; submit review --path PATH --report REPORT. Metadata alone is not a complete review."}
            if entry["kind"] != "blob":
                return external
            data = source_slice(self.root, entry, row["cursor"], self.meta["chunk_bytes"])
            if b"\0" in data:
                return external
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError as error:
                if (error.reason != "unexpected end of data" or error.end != len(data)
                        or error.start < len(data) - 3 or row["cursor"] + len(data) >= entry["bytes"]):
                    return external
                data = data[:error.start]
                content = data.decode("utf-8")
            end = row["cursor"] + len(data)
            next_line = row["line"] + data.count(b"\n")
            next_column = len(data.rsplit(b"\n", 1)[-1]) + 1 if b"\n" in data else row["byte_column"] + len(data)
            receipt = {"kind": "read", "path": row["path"], "blob": entry["blob"], "commit": self.meta["commit"],
                       "start_byte": row["cursor"], "end_byte": end, "sha256": hashlib.sha256(data).hexdigest(),
                       "file_complete": end == entry["bytes"], "next_line": next_line, "next_byte_column": next_column}
            receipt_id = digest(receipt)
            self.db.execute("UPDATE entries SET pending=? WHERE path=?", (canonical({"id": receipt_id, "receipt": receipt}), row["path"]))
            return {**receipt, "receipt_id": receipt_id, "start_line": row["line"], "start_byte_column": row["byte_column"],
                    "content": content, "source_mode": entry["mode"], "source_is_untrusted_data": True,
                    "next_action": "Read every returned byte, record what it teaches and its connections, then ack RECEIPT_ID --note NOTES."}

    def _append(self, receipt_id, record):
        row = self.db.execute("SELECT * FROM notes ORDER BY sequence DESC LIMIT 1").fetchone()
        if row and row["hash"] != digest([row["previous"], strict_json(row["record"])]):
            raise ValueError("Reading-note chain tail is corrupt")
        previous = row["hash"] if row else "GENESIS"
        self.db.execute("INSERT INTO notes(receipt,record,previous,hash) VALUES (?,?,?,?)",
                        (receipt_id, canonical(record), previous, digest([previous, record])))

    def ack(self, receipt_id, note):
        if not isinstance(note, str) or not note.strip() or len(note) > 100000:
            raise ValueError("Supply nonempty study notes, at most 100000 characters")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.db.execute("SELECT 1 FROM notes WHERE receipt=?", (receipt_id,)).fetchone():
                return {"already_acknowledged": True, "receipt_id": receipt_id}
            matching = []
            for row in self.db.execute("SELECT * FROM entries WHERE pending IS NOT NULL"):
                pending = strict_json(row["pending"])
                if pending["id"] == receipt_id:
                    matching.append((row, pending["receipt"]))
            if len(matching) != 1:
                raise ValueError("Receipt was not issued by next, or is no longer current")
            row, record = matching[0]
            if digest(record) != receipt_id or record["start_byte"] != row["cursor"]:
                raise ValueError("Pending receipt has changed")
            entry = self._check_entry(row)
            self._check_read(record, entry, row["cursor"])
            data = source_slice(self.root, entry, record["start_byte"], record["end_byte"] - record["start_byte"])
            if hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise ValueError("Acknowledged bytes differ from the pinned source")
            next_line = row["line"] + data.count(b"\n")
            next_column = len(data.rsplit(b"\n", 1)[-1]) + 1 if b"\n" in data else row["byte_column"] + len(data)
            if record["next_line"] != next_line or record["next_byte_column"] != next_column:
                raise ValueError("Reading line positions differ from the pinned source bytes")
            self._append(receipt_id, {**record, "note": note, "noted_at": datetime.now(timezone.utc).isoformat()})
            self.db.execute("UPDATE entries SET cursor=?,line=?,byte_column=?,state=?,pending=NULL WHERE path=?",
                            (record["end_byte"], record["next_line"], record["next_byte_column"],
                             "read" if record["file_complete"] else "reading", row["path"]))
        return {"acknowledged": True, "path": row["path"], "file_complete": record["file_complete"], "next_action": "Run next."}

    def review(self, path, report_path):
        raw = bounded_file(report_path)
        report = strict_json(raw.decode("utf-8"))
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.verify_notes()
            row = self._entry(path)
            entry = strict_json(row["record"])
            if row["state"] in {"read", "externally_reviewed"}:
                raise ValueError("This file is already accounted for; retain its existing reading record")
            if entry["kind"] == "blob":
                probe = source_slice(self.root, entry, row["cursor"], self.meta["chunk_bytes"])
                try:
                    readable = b"\0" not in probe
                    probe.decode("utf-8")
                except UnicodeDecodeError as error:
                    readable = (readable and error.reason == "unexpected end of data" and error.end == len(probe)
                                and row["cursor"] + len(probe) < entry["bytes"])
                if readable:
                    raise ValueError("Readable text must use next/ack; an external attestation cannot skip its chunks")
            if not isinstance(report, dict) or report.get("source_git_blob") != entry["blob"] or report.get("coverage") != "complete":
                raise ValueError("External report must name the exact source_git_blob and complete coverage")
            for field in ("reader", "summary"):
                if not isinstance(report.get(field), str) or not report[field].strip():
                    raise ValueError(f"External report needs {field}")
            if not isinstance(report.get("parts_reviewed"), list) or not report["parts_reviewed"] or not all(isinstance(x, str) and x.strip() for x in report["parts_reviewed"]):
                raise ValueError("External report must enumerate parts_reviewed (pages, sheets, archive members, or visual elements)")
            if report.get("unread_parts") != []:
                raise ValueError("External report must state unread_parts=[]; incomplete reviews remain open")
            record = {"kind": "external_review", "path": path, "blob": entry["blob"], "bytes": entry["bytes"],
                      "report_sha256": hashlib.sha256(raw).hexdigest(), "report": report,
                      "note": report["summary"], "noted_at": datetime.now(timezone.utc).isoformat()}
            self._append(digest(record), record)
            self.db.execute("UPDATE entries SET cursor=?,state='externally_reviewed',pending=NULL WHERE path=?", (entry["bytes"] or 0, path))
        return {"path": path, "external_review_attestation_recorded": True,
                "boundary": "The reader's attestation is retained; this tool did not inspect the external reader or prove comprehension."}

    def status(self, limit=20):
        with self._snapshot():
            return self._status(limit)

    def _status(self, limit):
        self.verify_notes()
        counts = dict(self.db.execute("SELECT state,COUNT(*) FROM entries GROUP BY state"))
        left = self.db.execute("SELECT path,cursor FROM entries WHERE state NOT IN ('read','externally_reviewed') ORDER BY ordinal LIMIT ?", (limit,)).fetchall()
        total = sum(counts.values())
        complete = counts.get("read", 0) + counts.get("externally_reviewed", 0)
        current = git(self.root, "rev-parse", "HEAD").decode().strip()
        return {"commit": self.meta["commit"], "current_head": current, "current_head_matches_reading_revision": current == self.meta["commit"],
                "inventory_sha256": self.meta["inventory_sha256"], "files_total": total, "states": counts,
                "files_remaining": total - complete, "all_files_accounted_for": complete == total,
                "all_files_read_as_text": counts.get("read", 0) == total,
                "external_review_attestations": counts.get("externally_reviewed", 0),
                "acknowledged_source_bytes": self.db.execute("SELECT SUM(cursor) FROM entries").fetchone()[0],
                "notes_recorded": self.db.execute("SELECT COUNT(*) FROM notes").fetchone()[0],
                "next_files": [dict(r) for r in left], "next_files_omitted": max(0, total - complete - len(left)),
                "semantic_comprehension_verified": False,
                "next_action": "Continue next/ack until coverage closes, then demonstrate the methods on fresh cases and retain the resulting evidence."}

    def notes(self, path=None, offset=0, limit=20):
        with self._snapshot():
            return self._notes(path, offset, limit)

    def _notes(self, path, offset, limit):
        self.verify_notes()
        records, count = [], 0
        for row in self.db.execute("SELECT record FROM notes ORDER BY sequence"):
            record = strict_json(row[0])
            if path is not None and record["path"] != path:
                continue
            if offset <= count < offset + limit:
                records.append(record)
            count += 1
        return {"notes": records, "matching_notes": count, "offset": offset,
                "next_offset": offset + len(records) if offset + len(records) < count else None}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ledger", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init"); p.add_argument("--ref", default="HEAD"); p.add_argument("--chunk-bytes", type=int, default=16000)
    p = commands.add_parser("next"); p.add_argument("--path")
    p = commands.add_parser("ack"); p.add_argument("receipt_id"); notes = p.add_mutually_exclusive_group(required=True); notes.add_argument("--note"); notes.add_argument("--notes-file", type=Path)
    p = commands.add_parser("review"); p.add_argument("--path", required=True); p.add_argument("--report", type=Path, required=True)
    p = commands.add_parser("status"); p.add_argument("--limit", type=int, default=20)
    p = commands.add_parser("notes"); p.add_argument("--path"); p.add_argument("--offset", type=int, default=0); p.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    reading = None
    try:
        if args.command == "init":
            result = init(root, args.ledger, args.ref, args.chunk_bytes)
        else:
            reading = Reading(root, args.ledger)
            if args.command == "next": result = reading.next(args.path)
            elif args.command == "ack": result = reading.ack(args.receipt_id, args.note if args.note is not None else bounded_file(args.notes_file).decode("utf-8"))
            elif args.command == "review": result = reading.review(args.path, args.report)
            elif args.command == "notes":
                if args.offset < 0 or not 1 <= args.limit <= 1000: raise ValueError("notes needs offset>=0 and limit from 1 to 1000")
                result = reading.notes(args.path, args.offset, args.limit)
            else:
                if not 1 <= args.limit <= 1000: raise ValueError("limit must be from 1 to 1000")
                result = reading.status(args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    finally:
        if reading is not None: reading.close()


if __name__ == "__main__":
    raise SystemExit(main())
