#!/usr/bin/env bash
# Claude Code Stop hook. Keep this file in the repository/bundle, or set
# INFINITYBLADE_ROOT to that root when installing a copy of the hook.
set -eu
hook_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export INFINITYBLADE_ROOT="${INFINITYBLADE_ROOT:-$hook_root}"
exec python3 -c '
import importlib.util, json, os, pathlib, sys
def block(reason):
    print(json.dumps({"decision": "block", "reason": "InfinityBlade: " + reason}))
try:
    event = json.load(sys.stdin)
    if event.get("stop_hook_active") is True:
        raise SystemExit(0)
    path = pathlib.Path(event.get("transcript_path", ""))
    if not path.is_file():
        block("transcript unavailable; cannot verify the final reply")
        raise SystemExit(0)
    checker = pathlib.Path(os.environ["INFINITYBLADE_ROOT"]) / "tools/status_evidence_check.py"
    spec = importlib.util.spec_from_file_location("status_evidence_check", checker)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    last = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        message = row.get("message") or {}
        content = message.get("content")
        if row.get("type") == "assistant" and isinstance(content, list):
            text = "".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
            if text.strip():
                last = text
    ok, reason = module.check(last)
    if not ok:
        block(reason)
except (OSError, ValueError, TypeError, AttributeError) as exc:
    block("hook input or checker unavailable: " + type(exc).__name__)
'
