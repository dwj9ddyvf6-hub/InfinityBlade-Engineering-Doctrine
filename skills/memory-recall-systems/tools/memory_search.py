#!/usr/bin/env python3
"""Local recall index over an agent's markdown memory estate.

Why this exists (the full evidence is in
../references/research-2026-11-06.md): the cited agentmemory component
test reports 96.2% any-hit@5 for BM25 on LongMemEval-S, and Letta's
files-plus-grep agent reports 74.0% on LoCoMo in its own harness.
These different measurements motivate testing simple, inspectable
retrieval; they are not a shared ranking or a result for this tool.
This implementation addresses two concrete recall failures: failing
to search retained knowledge and searching only the first open file.

This tool indexes the whole estate into one SQLite FTS5 index
(Python standard library only, no models to download): heading-
scoped chunks with line pointers, BM25 ranking with column weights
and a canonical-source boost, and progressive disclosure (index
line, then snippet, then full chunk). A canary mode grades recall
against questions drawn from the adopter's own history, so a
recall regression is a measured defect, not a vibe.

Configuration (environment):
  MEMORY_SEARCH_ROOTS  os.pathsep-separated files or directories
                       of markdown to index. Default: ~/MEMORY.md,
                       ~/memory, ~/notes, whichever exist.
  MEMORY_SEARCH_DB     index location.
                       Default: ~/.agent-memory-index.db

Usage:
  python3 memory_search.py build
  python3 memory_search.py query "terms" [--k 5] [--level 1|2|3]
  python3 memory_search.py canary   # reads memory_canaries.json
                                    # beside this script; see
                                    # memory_canaries.example.json
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path

HOME = os.path.expanduser("~")
DB_PATH = os.environ.get(
    "MEMORY_SEARCH_DB", os.path.join(HOME, ".agent-memory-index.db"))
CANARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "memory_canaries.json")


def default_roots():
    roots = []
    env = os.environ.get("MEMORY_SEARCH_ROOTS")
    if env:
        return [p for p in env.split(os.pathsep) if p]
    home = os.path.expanduser("~")
    for cand in (os.path.join(home, "MEMORY.md"),
                 os.path.join(home, "memory"),
                 os.path.join(home, "notes")):
        if os.path.exists(cand):
            roots.append(cand)
    return roots


SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
MAX_CHUNK = 1800


def iter_files(roots):
    def traversal_error(error):
        raise error  # An unreadable subtree is missing evidence, not an empty estate.

    seen = set()
    for root in roots:
        root = Path(root).absolute()
        if root.is_symlink():
            raise ValueError("memory roots must not be symlinks")
        if not root.exists():
            raise FileNotFoundError(root)
        if root.is_file():
            candidates = [root] if root.suffix == ".md" else []
        else:
            candidates = []
            for directory, dirs, files in os.walk(root, onerror=traversal_error):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
                if any((Path(directory) / d).is_symlink() for d in dirs):
                    raise ValueError("memory directory contains a symlink; select explicit roots")
                candidates.extend(Path(directory) / name for name in sorted(files) if name.endswith(".md"))
        for path in candidates:
            if path.is_symlink():
                raise ValueError("memory file is a symlink; select its intended source explicitly")
            if not stat.S_ISREG(path.stat().st_mode):
                raise ValueError("memory source must be a regular file")
            canonical = str(path.resolve())
            if canonical not in seen:
                seen.add(canonical)
                yield canonical


def read_source(path):
    """Read one stable regular source; a late FIFO/symlink swap cannot hang."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError("memory source must not be a symlink")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("memory source must be a regular file")
        data = handle.read()
        after = os.fstat(handle.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("memory source changed during its read")
    return data


def chunk_file(path, data=None):
    """Bound heading-scoped chunks and retain the actual 1-based start line."""
    data = read_source(path) if data is None else data
    lines = data.decode("utf-8").splitlines()
    heading, buffer, start = "(top)", "", 1
    for number, line in enumerate(lines, 1):
        match = re.match(r"^(#{1,6})\s+(.*)", line)
        if match:
            if buffer.strip():
                yield {"path": str(path), "heading": heading, "line": start, "text": buffer}
            buffer, heading = "", match.group(2).strip()
        parts = [line[i:i + MAX_CHUNK] for i in range(0, len(line), MAX_CHUNK)] or [""]
        for part in parts:
            candidate = buffer + ("\n" if buffer else "") + part
            if buffer and len(candidate) > MAX_CHUNK:
                if buffer.strip():
                    yield {"path": str(path), "heading": heading, "line": start, "text": buffer}
                buffer = ""
            if not buffer:
                start = number
                buffer = part
            else:
                buffer += "\n" + part
    if buffer.strip():
        yield {"path": str(path), "heading": heading, "line": start, "text": buffer}


def database_path(path=None):
    return str(path or os.environ.get("MEMORY_SEARCH_DB") or DB_PATH)


def validate_destination(roots, destination, paths):
    """Reject source aliases and prospective indexed outputs before any write."""
    lock_path = Path(str(destination) + ".build-lock.sqlite3")
    for output in (destination, lock_path):
        if output.is_symlink():
            raise ValueError("index destination and build lock must not be symlinks")
        if output.exists() and not output.is_file():
            raise ValueError("index destination and build lock must be regular files")
        for source in paths:
            if (Path(source).resolve() == output.resolve()
                    or output.exists() and os.path.samefile(source, output)):
                raise ValueError("index destination or build lock would overwrite an indexed source")
    if destination.exists() and lock_path.exists() and os.path.samefile(destination, lock_path):
        raise ValueError("index destination and build lock must be different files")
    if destination.suffix == ".md":
        for root in roots:
            root = Path(root).resolve()
            if root.is_dir() and destination.resolve().is_relative_to(root):
                relative = destination.resolve().relative_to(root)
                if not any(part in SKIP_DIRS for part in relative.parts[:-1]):
                    raise ValueError("index destination would become an indexed markdown source; choose a path outside that estate")


@contextmanager
def build_lock(destination):
    lock_path = str(destination) + ".build-lock.sqlite3"
    if Path(lock_path).is_symlink():
        raise ValueError("index build lock must not be a symlink")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.close(fd)
    lock = sqlite3.connect(lock_path, timeout=15)
    try:
        lock.execute("BEGIN IMMEDIATE")
        yield
    finally:
        lock.rollback()
        lock.close()


def build(roots=None, db_path=None, allow_empty=False):
    roots = default_roots() if roots is None else roots
    roots = list(roots)
    if not roots:
        raise ValueError("no roots found; set MEMORY_SEARCH_ROOTS")
    destination = Path(database_path(db_path)).absolute()
    validate_destination(roots, destination, list(iter_files(roots)))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with build_lock(destination):
        return _build(roots, destination, allow_empty)


def _build(roots, destination, allow_empty=False):
    paths = list(iter_files(roots))
    validate_destination(roots, destination, paths)
    fd, temporary = tempfile.mkstemp(prefix="." + destination.name + ".", dir=destination.parent)
    os.close(fd)
    con = None
    try:
        con = sqlite3.connect(temporary)
        con.execute("CREATE TABLE chunks (path TEXT, heading TEXT, line INTEGER, text TEXT)")
        con.execute("CREATE TABLE sources (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL)")
        con.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.executemany("INSERT INTO metadata VALUES (?,?)", [("schema_version", "2"), ("built_at", datetime.now(timezone.utc).isoformat()), ("roots", json.dumps([str(Path(p).absolute()) for p in roots]))])
        con.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(path, heading, text, content='chunks', content_rowid='rowid')")
        n_chunks = n_files = 0
        for path in paths:
            data = read_source(path)
            con.execute("INSERT INTO sources VALUES (?,?,?)", (path, hashlib.sha256(data).hexdigest(), len(data)))
            file_chunks = list(chunk_file(path, data))
            if file_chunks:
                n_files += 1
            for ch in file_chunks:
                cur = con.execute("INSERT INTO chunks (path, heading, line, text) VALUES (?, ?, ?, ?)",
                                  (ch["path"], ch["heading"], ch["line"], ch["text"]))
                con.execute("INSERT INTO chunks_fts (rowid, path, heading, text) VALUES (?, ?, ?, ?)",
                            (cur.lastrowid, ch["path"], ch["heading"], ch["text"]))
                n_chunks += 1
        if not n_files and not allow_empty:
            raise ValueError("no nonempty markdown files indexed; previous index preserved")
        if list(iter_files(roots)) != paths:
            raise ValueError("source inventory changed during indexing; previous index preserved")
        for path, expected in con.execute("SELECT path,sha256 FROM sources"):
            if hashlib.sha256(read_source(path)).hexdigest() != expected:
                raise ValueError("source bytes changed during indexing; previous index preserved")
        con.commit()
        con.close()
        con = None
        with open(temporary, "rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if con is not None:
            con.close()
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"indexed {n_chunks} chunks from {n_files} files -> {destination}")
    return n_chunks


def _match_expr(query):
    terms = re.findall(r"[A-Za-z0-9_@.\-]+", query)
    terms = [t for t in terms if len(t) > 1]
    if not terms:
        return None
    # Quoted terms OR-joined: FTS5 bm25 ranks chunks matching more
    # of the query above chunks matching one term.
    return " OR ".join(f'"{t}"' for t in terms)


def source_state(path, expected=None, indexed_bytes=None):
    result = {"indexed_sha256": expected, "indexed_bytes": indexed_bytes}
    if expected is None:
        return {**result, "source_status": "legacy_index_unverified", "current_sha256": None}
    try:
        raw = read_source(path)
        current = hashlib.sha256(raw).hexdigest()
        return {**result, "source_status": "matches_index" if current == expected else "changed_since_index",
                "current_sha256": current}
    except FileNotFoundError:
        return {**result, "source_status": "source_missing", "current_sha256": None}
    except (OSError, ValueError):
        return {**result, "source_status": "source_unreadable", "current_sha256": None}


def query(text, k=5, db_path=None, current_only=False):
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 1000:
        raise ValueError("k must be an integer from 1 to 1000")
    expr = _match_expr(text)
    if expr is None:
        return []
    con = sqlite3.connect(Path(database_path(db_path)).absolute().as_uri() + "?mode=ro", uri=True)
    # Column weights: path matches count least, heading matches
    # most. Canonical-source boost: the curated MEMORY.md is the
    # settled record, so a tie breaks toward it over the daily
    # notes that first carried the fact; bm25 is smaller-is-
    # better and negative, so a factor above 1 promotes.
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        identities = dict((path, (sha, size)) for path, sha, size in con.execute("SELECT path,sha256,bytes FROM sources")) if "sources" in tables else {}
        rows = con.execute(
        "SELECT c.path, c.heading, c.line, c.text, "
        "bm25(chunks_fts, 0.5, 2.0, 1.0) * CASE "
        "WHEN c.path LIKE '%/MEMORY.md' THEN 1.10 "
        "WHEN c.path LIKE '%/USER.md' THEN 1.06 "
        "WHEN c.path LIKE '%/people/%' THEN 1.04 "
        "WHEN c.path LIKE '%/groups/%' THEN 1.04 "
        "ELSE 1.0 END AS rank "
        "FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "
        "WHERE chunks_fts MATCH ? ORDER BY rank, c.path, c.line",
        (expr,))
        result, states = [], {}
        for p, h, ln, t, s in rows:
            if p not in states:
                states[p] = source_state(p, *identities.get(p, (None, None)))
            if current_only and states[p]["source_status"] != "matches_index":
                continue
            result.append({"path": p, "heading": h, "line": ln, "text": t,
                           "score": s, **states[p], "indexed_snapshot": True})
            if len(result) == k:
                break
        return result
    finally:
        con.close()


def index_status(db_path=None):
    """Inspect every indexed source, including sources with no current query hit."""
    con = sqlite3.connect(Path(database_path(db_path)).absolute().as_uri() + "?mode=ro", uri=True)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "sources" not in tables:
            return {"status": "legacy_index_unverified", "next_action": "Rebuild from explicit roots to add source identity."}
        rows = [{"path": p, **source_state(p, sha, size)} for p, sha, size in con.execute("SELECT path,sha256,bytes FROM sources ORDER BY path")]
        roots = json.loads(con.execute("SELECT value FROM metadata WHERE key='roots'").fetchone()[0])
        try:
            current_paths = set(iter_files(roots))
            inventory_error = None
        except (OSError, ValueError) as error:
            current_paths, inventory_error = set(), type(error).__name__
        indexed = {r["path"] for r in rows}
        added = sorted(current_paths - indexed) if inventory_error is None else None
        return {"sources": rows, "new_unindexed_paths": added, "inventory_error": inventory_error,
                "current": not inventory_error and not added and all(r["source_status"] == "matches_index" for r in rows),
                "next_action": "Rebuild from the same explicit roots when source bytes or membership change."}
    finally:
        con.close()


def snippet(chunk_text, query_text, width=320):
    terms = [t.lower() for t in
             re.findall(r"[A-Za-z0-9_@.\-]+", query_text) if len(t) > 1]
    low = chunk_text.lower()
    pos = min((low.find(t) for t in terms if low.find(t) >= 0),
              default=0)
    start = max(0, pos - 80)
    return chunk_text[start:start + width].replace("\n", " ").strip()


def canary(path=None, strict=False, db_path=None):
    with open(path or CANARY_PATH, encoding="utf-8") as fh:
        cases = json.load(fh)
    if not isinstance(cases, list) or not cases:
        raise ValueError("canary file must contain a nonempty case list")
    hits1 = hits5 = 0
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("q"), str) or not case["q"].strip():
            raise ValueError("every canary needs a nonempty query")
        results = query(case["q"], k=5, db_path=db_path, current_only=True)
        paths = [os.path.relpath(r["path"], HOME) for r in results]
        wants = case["expect"]
        if isinstance(wants, str):
            wants = [wants]
        if not isinstance(wants, list) or not wants or any(not isinstance(w, str) or not w for w in wants):
            raise ValueError("every canary needs nonempty expected path suffixes")
        rank = next((i + 1 for i, p in enumerate(paths)
                     if any(Path(p).parts[-len(Path(w).parts):] == Path(w).parts for w in wants)), None)
        if rank == 1:
            hits1 += 1
        if rank is not None:
            hits5 += 1
        print(f"[{'hit@' + str(rank) if rank else 'MISS'}] "
              f"{case['q']} -> want {'|'.join(wants)}"
              + (f", got {paths[0] if paths else 'nothing'}"
                 if not rank else ""))
    n = len(cases)
    print(f"canary: hit@1 {hits1}/{n}, hit@5 {hits5}/{n}")
    if strict and hits5 != n:
        raise ValueError(f"recall canary failed: {n - hits5}/{n} misses")
    return hits5


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    bp = sub.add_parser("build")
    bp.add_argument("--roots", nargs="+", help="Explicit markdown files/directories; overrides default roots")
    bp.add_argument("--allow-empty", action="store_true", help="Deliberately replace the index after a valid source estate becomes empty")
    sub.add_parser("status")
    cp = sub.add_parser("canary")
    cp.add_argument("--file")
    qp = sub.add_parser("query")
    qp.add_argument("text")
    qp.add_argument("--k", type=int, default=5)
    qp.add_argument("--level", type=int, choices=(1, 2, 3), default=2)
    qp.add_argument("--json", action="store_true")
    qp.add_argument("--current-only", action="store_true", help="Return only sources whose current bytes still match the index")
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.roots, allow_empty=args.allow_empty)
    elif args.cmd == "status":
        print(json.dumps(index_status(), indent=2))
    elif args.cmd == "canary":
        canary(args.file, strict=True)
    elif args.cmd == "query":
        results = query(args.text, k=args.k, current_only=args.current_only)
        if args.json:
            print(json.dumps(results, indent=2))
            return
        if not results:
            print("no matches")
            return
        for i, r in enumerate(results, 1):
            rel = os.path.relpath(r["path"], HOME)
            print(f"{i}. {rel} :: {r['heading']} (line {r['line']}; {r['source_status']}; indexed sha256={r['indexed_sha256']})")
            if args.level >= 2:
                print(f"   {snippet(r['text'], args.text)}")
            if args.level >= 3:
                print(f"---\n{r['text']}\n---")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"memory search failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
