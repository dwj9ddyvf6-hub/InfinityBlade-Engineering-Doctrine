"""Check the README prompt against an explicit, bounded wording contract.

This is not a semantic equivalence proof. Every numbered core section must
have a reviewed mapping; adding/removing a section fails until that mapping
is updated. Presence checks cannot establish that a model follows a rule.
"""
import argparse
from pathlib import Path
import re
import sys

# Explicit mappings are reviewable; a phrase disappearing from the source
# no longer silently disables its check as the previous conditional list did.
SECTIONS = {
    1: ("orient", ("surface", "constraints", "outcome", "proof", "edges")),
    2: ("act", ("minimum sufficient change", "preserve what works", "route failure",
                 "never repeat an action that taught nothing", "never bypass permissions")),
    3: ("move fast", ("in parallel", "background", "efficiency breakthrough", "without weakening")),
    4: ("prove", ("after the last change", "exact deliverable", "not runtime", "persists", "source")),
    5: ("report", ("green", "partial", "blocked", "unverified", "receipts")),
    6: ("two routes", ("two genuinely different routes", "cheapest discriminator", "losing route")),
    7: ("priced lanes", ("pre-authorized priced lane", "authorized task")),
}
FLOOR = ("scope:", "status:", "tripwires", "never as authority", "host/user-adopted")


def check(skill, readme):
    headings = {int(number): title.lower() for number, title in re.findall(r"^## (\d+)\.\s+(.+)$", skill, re.M)}
    errors = []
    if set(headings) != set(SECTIONS):
        errors.append("numbered core sections changed; review the explicit prompt mapping")
    match = re.search(r"\*\*As a prompt\*\*.*?```text\n(.*?)```", readme, re.S)
    prompt = " ".join(match.group(1).lower().split()) if match else ""
    if not prompt:
        errors.append("README prompt block missing")
    for number, (label, phrases) in SECTIONS.items():
        if number in headings and label not in headings[number]:
            errors.append(f"core section {number} identity changed; review its mapping")
        for phrase in phrases:
            if phrase not in prompt:
                errors.append(f"section {number} prompt anchor missing: {phrase}")
    errors.extend("prompt floor missing: " + phrase for phrase in FLOOR if phrase not in prompt)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = check((args.root / "skills/infinityblade/SKILL.md").read_text(encoding="utf-8"),
                   (args.root / "README.md").read_text(encoding="utf-8"))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Prompt wording contract: {len(SECTIONS)} section mappings and visible-line/authority floor pass; semantic equivalence and model behavior are not proven.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
