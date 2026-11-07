"""Atomic private files and process-safe locks for cooperating local callers.

The SQLite sidecar coordinates the entire read/modify/write cycle on a
local filesystem. This is not a distributed lock or authorization boundary.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import threading

_LOCKS = threading.local()


@contextmanager
def locked(path):
    path = Path(path).resolve()
    held = getattr(_LOCKS, "held", None)
    # A forked child inherits Python thread-local values, but it does not own
    # its parent's transaction. Never treat the inherited set as reentrancy.
    if held is None or getattr(_LOCKS, "pid", None) != os.getpid():
        for inherited in getattr(_LOCKS, "connections", ()):
            inherited.close()
        _LOCKS.pid = os.getpid()
        held = _LOCKS.held = set()
        _LOCKS.connections = set()
    if str(path) in held:
        # Nested calls in one operation share its transaction lock. Other
        # threads/processes still acquire their own SQLite connection.
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = str(path) + ".lock.sqlite3"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    db = sqlite3.connect(lock_path, timeout=10)
    owner_pid = os.getpid()
    _LOCKS.connections.add(db)
    try:
        db.execute("BEGIN IMMEDIATE")
        held.add(str(path))
        try:
            yield
        finally:
            if os.getpid() == owner_pid:
                held.remove(str(path))
    finally:
        if os.getpid() == owner_pid:
            _LOCKS.connections.discard(db)
            db.rollback()
            db.close()


def sync_directory(path):
    """Persist directory entries on POSIX; other hosts retain atomic replace."""
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def read_bytes(path):
    """Read a regular state file without following its final symlink."""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("state must be a regular file")
        return handle.read()


def read_text(path):
    return read_bytes(path).decode("utf-8")


def atomic_bytes(path, data):
    """Replace complete private bytes and persist the directory entry."""
    path = Path(path).absolute()
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("state destination must be a regular file")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_text(path, text):
    """Replace a complete UTF-8 file without exposing a partial write."""
    atomic_bytes(path, text.encode("utf-8"))


def append_text(path, text):
    """Durable append for cooperating callers; hold locked(path) around RMW."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags, 0o600), "wb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("append destination must be a regular file")
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    sync_directory(path.parent)


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
