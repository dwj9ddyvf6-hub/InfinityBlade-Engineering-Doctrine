#!/usr/bin/env python3
"""Local recall index over an agent's markdown memory estate.

Why this exists (the full evidence is in
../references/research-2026-11-06.md): measured retrieval over an
agent's own notes beats every purpose-built memory database the
field has benchmarked, and the strongest published component result
is lexical: plain BM25 alone hit 96.2% any-hit@5 on LongMemEval-S
in the agentmemory component test, and a files-plus-grep agent
scored 74.0% on LoCoMo in Letta's harness. The recall failure mode
of a file-based agent is almost never the files. It is retrieval
that depends on the agent remembering to search, and search whose
reach stops at whichever file the agent happens to open.

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
            for directory, dirs, files in os.walk(root):
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


def chunk_file(path):
    """Bound heading-scoped chunks and retain the actual 1-based start line."""
    if not stat.S_ISREG(Path(path).stat().st_mode):
        raise ValueError("memory source must be a regular file")
    lines = Path(path).read_text(encoding="utf-8").splitlines()
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


def build(roots=None, db_path=None):
    roots = default_roots() if roots is None else roots
    if not roots:
        raise ValueError("no roots found; set MEMORY_SEARCH_ROOTS")
    destination = Path(database_path(db_path)).absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + destination.name + ".", dir=destination.parent)
    os.close(fd)
    con = None
    try:
        con = sqlite3.connect(temporary)
        con.execute("CREATE TABLE chunks (path TEXT, heading TEXT, line INTEGER, text TEXT)")
        con.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(path, heading, text, content='chunks', content_rowid='rowid')")
        n_chunks = n_files = 0
        for path in iter_files(roots):
            file_chunks = list(chunk_file(path))
            if file_chunks:
                n_files += 1
            for ch in file_chunks:
                cur = con.execute("INSERT INTO chunks (path, heading, line, text) VALUES (?, ?, ?, ?)",
                                  (ch["path"], ch["heading"], ch["line"], ch["text"]))
                con.execute("INSERT INTO chunks_fts (rowid, path, heading, text) VALUES (?, ?, ?, ?)",
                            (cur.lastrowid, ch["path"], ch["heading"], ch["text"]))
                n_chunks += 1
        if not n_files:
            raise ValueError("no nonempty markdown files indexed; previous index preserved")
        con.commit()
        con.close()
        con = None
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


def query(text, k=5, db_path=None):
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
    rows = con.execute(
        "SELECT c.path, c.heading, c.line, c.text, "
        "bm25(chunks_fts, 0.5, 2.0, 1.0) * CASE "
        "WHEN c.path LIKE '%/MEMORY.md' THEN 1.10 "
        "WHEN c.path LIKE '%/USER.md' THEN 1.06 "
        "WHEN c.path LIKE '%/people/%' THEN 1.04 "
        "WHEN c.path LIKE '%/groups/%' THEN 1.04 "
        "ELSE 1.0 END AS rank "
        "FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "
        "WHERE chunks_fts MATCH ? ORDER BY rank, c.path, c.line LIMIT ?",
        (expr, k)).fetchall()
    con.close()
    return [{"path": p, "heading": h, "line": ln, "text": t,
             "score": s} for p, h, ln, t, s in rows]


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
        results = query(case["q"], k=5, db_path=db_path)
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
    sub.add_parser("build")
    cp = sub.add_parser("canary")
    cp.add_argument("--file")
    qp = sub.add_parser("query")
    qp.add_argument("text")
    qp.add_argument("--k", type=int, default=5)
    qp.add_argument("--level", type=int, choices=(1, 2, 3), default=2)
    args = ap.parse_args()
    if args.cmd == "build":
        build()
    elif args.cmd == "canary":
        canary(args.file, strict=True)
    elif args.cmd == "query":
        results = query(args.text, k=args.k)
        if not results:
            print("no matches")
            return
        for i, r in enumerate(results, 1):
            rel = os.path.relpath(r["path"], HOME)
            print(f"{i}. {rel} :: {r['heading']} (line {r['line']})")
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
