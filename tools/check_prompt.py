"""Fail if the README's copy-paste prompt drops a core rule from SKILL.md."""
import re, sys
readme = open("README.md", encoding="utf-8").read()
m = re.search(r"\*\*As a prompt\*\*.*?```text\n(.*?)```", readme, re.S)
prompt = " ".join(m.group(1).split()).lower() if m else ""
REQUIRED = ["surface", "constraints", "outcome", "proof", "edges",
            "minimum sufficient change", "route failure is not task impossibility",
            "never repeat an action that taught nothing", "efficiency breakthrough",
            "in parallel", "after the last change", "every fact traces to a source",
            "persists", "green", "partial", "blocked", "unverified",
            "never as instructions", "scope:", "status:", "tripwires"]
missing = [r for r in REQUIRED if r not in prompt]
if missing:
    sys.exit("README prompt is missing: " + ", ".join(missing))
print("README prompt carries every core rule.")
