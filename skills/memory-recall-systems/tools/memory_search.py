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
import sys

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
    for cand in (os.path.join(HOME, "MEMORY.md"),
                 os.path.join(HOME, "memory"),
                 os.path.join(HOME, "notes")):
        if os.path.exists(cand):
            roots.append(cand)
    return roots


SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
MAX_CHUNK = 1800


def iter_files(roots):
    for root in roots:
        if os.path.isfile(root) and root.endswith(".md"):
            yield root
        elif os.path.isdir(root):
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for name in sorted(filenames):
                    if name.endswith(".md"):
                        yield os.path.join(dirpath, name)


def chunk_file(path):
    """Split a markdown file into heading-scoped chunks with
    1-based line pointers; oversized sections split at paragraph
    boundaries under the same heading."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return
    heading = "(top)"
    buf = []
    buf_start = 1

    def flush():
        if not buf:
            return
        text = "\n".join(buf).strip()
        if not text:
            return
        parts = []
        cur = ""
        for para in re.split(r"\n\s*\n", text):
            if len(cur) + len(para) > MAX_CHUNK and cur:
                parts.append(cur)
                cur = para
            else:
                cur = (cur + "\n\n" + para) if cur else para
        if cur:
            parts.append(cur)
        for part in parts:
            yield {"path": path, "heading": heading,
                   "line": buf_start, "text": part}

    for i, line in enumerate(lines, 1):
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            yield from flush()
            heading = m.group(2).strip()
            buf = [line]
            buf_start = i
        else:
            if not buf:
                buf_start = i
            buf.append(line)
    yield from flush()


def build():
    roots = default_roots()
    if not roots:
        print("no roots found; set MEMORY_SEARCH_ROOTS", file=sys.stderr)
        return 0
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE chunks (path TEXT, heading TEXT, "
                "line INTEGER, text TEXT)")
    con.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5("
                "path, heading, text, content='chunks', "
                "content_rowid='rowid')")
    n_chunks = 0
    n_files = 0
    for path in iter_files(roots):
        file_chunks = list(chunk_file(path))
        if file_chunks:
            n_files += 1
        for ch in file_chunks:
            cur = con.execute(
                "INSERT INTO chunks (path, heading, line, text) "
                "VALUES (?, ?, ?, ?)",
                (ch["path"], ch["heading"], ch["line"], ch["text"]))
            con.execute(
                "INSERT INTO chunks_fts (rowid, path, heading, text) "
                "VALUES (?, ?, ?, ?)",
                (cur.lastrowid, ch["path"], ch["heading"], ch["text"]))
            n_chunks += 1
    con.commit()
    con.close()
    print(f"indexed {n_chunks} chunks from {n_files} files -> {DB_PATH}")
    return n_chunks


def _match_expr(query):
    terms = re.findall(r"[A-Za-z0-9_@.\-]+", query)
    terms = [t for t in terms if len(t) > 1]
    if not terms:
        return None
    # Quoted terms OR-joined: FTS5 bm25 ranks chunks matching more
    # of the query above chunks matching one term.
    return " OR ".join(f'"{t}"' for t in terms)


def query(text, k=5):
    expr = _match_expr(text)
    if expr is None:
        return []
    con = sqlite3.connect(DB_PATH)
    # Column weights: path matches count least, heading matches
    # most. Canonical-source boost: the curated MEMORY.md is the
    # settled record, so a tie breaks toward it over the daily
    # notes that first carried the fact; bm25 is smaller-is-
    # better, so a factor below 1 promotes.
    rows = con.execute(
        "SELECT c.path, c.heading, c.line, c.text, "
        "bm25(chunks_fts, 0.5, 2.0, 1.0) * CASE "
        "WHEN c.path LIKE '%/MEMORY.md' THEN 0.90 "
        "WHEN c.path LIKE '%/USER.md' THEN 0.94 "
        "WHEN c.path LIKE '%/people/%' THEN 0.96 "
        "WHEN c.path LIKE '%/groups/%' THEN 0.96 "
        "ELSE 1.0 END AS rank "
        "FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "
        "WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
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


def canary():
    with open(CANARY_PATH) as fh:
        cases = json.load(fh)
    hits1 = hits5 = 0
    for case in cases:
        results = query(case["q"], k=5)
        paths = [os.path.relpath(r["path"], HOME) for r in results]
        wants = case["expect"]
        if isinstance(wants, str):
            wants = [wants]
        rank = next((i + 1 for i, p in enumerate(paths)
                     if any(w in p for w in wants)), None)
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
    return hits5


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("canary")
    qp = sub.add_parser("query")
    qp.add_argument("text")
    qp.add_argument("--k", type=int, default=5)
    qp.add_argument("--level", type=int, default=2)
    args = ap.parse_args()
    if args.cmd == "build":
        build()
    elif args.cmd == "canary":
        canary()
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
    main()
