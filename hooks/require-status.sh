#!/usr/bin/env bash
# Claude Code Stop hook: block finishing until the last reply carries a STATUS line.
input=$(cat)
# Don't loop: if this stop was already triggered by the hook, let it through.
[ "$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("stop_hook_active",False))')" = "True" ] && exit 0
transcript=$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("transcript_path",""))')
[ -f "$transcript" ] || exit 0
last=$(python3 - "$transcript" <<'PY'
import json, sys
text = ""
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    m = e.get("message") or {}
    if e.get("type") == "assistant" and isinstance(m.get("content"), list):
        t = "".join(c.get("text", "") for c in m["content"] if c.get("type") == "text")
        if t.strip():
            text = t
print(text)
PY
)
if printf '%s' "$last" | grep -qE 'STATUS: *(GREEN|PARTIAL|BLOCKED|UNVERIFIED)'; then exit 0; fi
echo '{"decision":"block","reason":"InfinityBlade: end with a STATUS line (GREEN, PARTIAL, BLOCKED or UNVERIFIED) and its proof or what is missing. For a pure conversation reply, write STATUS: GREEN — no change made."}'
