"""Atomic private files and process-safe locks for cooperating local callers.

The SQLite sidecar coordinates the entire read/modify/write cycle on a
local filesystem. This is not a distributed lock or authorization boundary.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import tempfile


@contextmanager
def locked(path):
    path = Path(path).absolute()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = str(path) + ".lock.sqlite3"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    db = sqlite3.connect(lock_path, timeout=10)
    try:
        db.execute("BEGIN IMMEDIATE")
        yield
    finally:
        db.rollback()
        db.close()


def atomic_text(path, text):
    """Replace a complete UTF-8 file without exposing a partial write."""
    path = Path(path).absolute()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def bounded_blocks(blocks, budget_chars, total=None):
    """Keep complete blocks, count the footer, retain every omission in metadata."""
    if isinstance(budget_chars, bool) or not isinstance(budget_chars, int) or budget_chars < 0:
        raise ValueError("budget_chars must be a nonnegative integer")
    blocks = list(blocks)
    total = len(blocks) if total is None else total
    selected, omitted = [], []
    footer = f"[INJECTION OMISSIONS: see metadata; budget {budget_chars} chars; total {total}]"
    for identifier, block in blocks:
        candidate = "\n".join([text for _, text in selected] + [block])
        if len(candidate) + len(footer) + 1 <= budget_chars:
            selected.append((identifier, block))
        else:
            omitted.append(identifier)
    text = "\n".join([block for _, block in selected] + ([footer] if len(footer) <= budget_chars else []))
    return {"text": text, "included": [identifier for identifier, _ in selected],
            "omitted": omitted, "used_chars": len(text)}
