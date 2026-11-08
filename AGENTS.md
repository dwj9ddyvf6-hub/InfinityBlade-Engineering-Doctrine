# Agent instructions

Follow [`skills/infinityblade/SKILL.md`](skills/infinityblade/SKILL.md) for every task in this repository: orient with SCOPE, act with the minimum sufficient change, move fast, prove the result on the final artifact, and report GREEN, PARTIAL, BLOCKED or UNVERIFIED with receipts.

When editing this repository:

- Complete the pinned, resumable [reading protocol](docs/READING-PROTOCOL.md) and the [ascent path](docs/ASCENT-PATH.md). Read all tracked source, tests, templates and historical depth; routes determine order, not omissions.
- `SKILL.md` is the single source of the rules. Keep it short and its operating loop direct: the core stays at or under 220 lines (check: `wc -l skills/infinityblade/SKILL.md`); preserve depth in `references/` behind a "read when" row.
- A new rule enters `SKILL.md` only if it is general to any agent and an eval case shows it changes behavior. Otherwise it belongs in `lessons-from-the-field.md`.
- Keep the README prompt in step with `SKILL.md` (`python3 tools/check_prompt.py` runs in CI), and note every change in `CHANGELOG.md`.
