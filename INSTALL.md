# Install InfinityBlade

Pick your host. The skill folder is `skills/infinityblade/` (keep `SKILL.md` and `references/` together).

| Host | Install |
|---|---|
| **Claude Code** | Copy the folder to `~/.claude/skills/infinityblade/` (all projects) or `.claude/skills/infinityblade/` (one repo). |
| **Codex** | Copy the folder to `~/.codex/skills/infinityblade/`. Invoke with `Use $infinityblade …` or let it activate. |
| **Other Agent Skills hosts** | Use the host's skills folder or importer. |
| **Cursor** | Paste the prompt from the [README](README.md#use-it-in-30-seconds) into `.cursor/rules/infinityblade.mdc` (set it to always apply). |
| **GitHub Copilot** | Paste the prompt into `.github/copilot-instructions.md`. |
| **Repo instruction files** | Paste the prompt into `AGENTS.md`, `CLAUDE.md` or `GEMINI.md`, or keep this repo's [`AGENTS.md`](AGENTS.md) with the skill folder. |
| **Any chat model / API** | Paste the prompt into the system prompt or custom instructions. |

## Install a library skill

The skills library (index: [`skills/INDEX.md`](skills/INDEX.md)) carries 19 complete skill folders beside the doctrine skill. Installing one means copying its folder into the same skills folder as `skills/infinityblade/`, by the same host rows above: the folder is complete as-is, with its full SKILL.md and every supporting file it needs, except the dependencies the index names in its Dependency column (two folders name theirs plainly). Where a library skill needs a credential, a path, or a document of yours, its SKILL.md names an environment variable or a placeholder; no credential file ships with any skill, and none should be added to one.

## Confirm it works

Do not confirm an install by asking for a recital. A wording check proves the words arrived, not that behavior changed, and this doctrine distrusts wording checks in its own house first.

Run two cases from [eval-cases.md](skills/infinityblade/references/eval-cases.md), one repair case and one absence or verdict case, twice each: once with the skill installed and once without. The install is confirmed only if the with-skill runs score higher on the sheet in that file (scope stated before action, proof taken from the final artifact, verdict exact) and neither without-skill run does. Record the two scores beside the install date. Anything less is UNVERIFIED, and the honest report says so.

## Enforce it

Instructions can be skipped; checks can't. In Claude Code, a Stop hook can refuse to end any turn whose reply lacks a `STATUS:` line. Copy [`hooks/require-status.sh`](hooks/require-status.sh) to `.claude/hooks/`, make it executable, and add to `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command", "command": ".claude/hooks/require-status.sh" }] }]
  }
}
```

The hook reads the session transcript and, if the last assistant message has no `STATUS:` line, asks the agent to add one with its proof. Other hosts: add the same check to your CI or review step (look for `STATUS:` in the agent's final report).

**What the hook actually checks (updated 3.1.0).** The shipped hook pattern-matches the label `STATUS:` and one of the four verdict words, and since 3.1.0 it also refuses a bare label: a STATUS line for work done must carry an evidence pointer (a path, a URL, or a quoted command result) after the verdict, or the hook blocks. It still cannot tell true evidence from a pointer to nothing; no wording-level check can. The paragraph below states the floor honestly. Treat it as a floor: it guarantees the report has a shape, never that the report is true. Any hook or checker implementation claiming this doctrine's enforcement standard must therefore require an evidence pointer after the label (the artifact, file, command output, or read-back the claim rests on) and must refuse a bare label. The same limit applies to any prompt checker: a checker that tests a fixed phrase list checks those phrases only; unless it derives its requirements from SKILL.md at run time, it does not check that a prompt matches the current skill.

**Scope note (2026-11-02).** The hook demands the line on every reply, including casual conversation and pure explanation, which the skill itself skips. That breadth is the enforcement layer's deliberate choice, not the skill's activation scope. The governing statement is in SKILL.md (The non-skippable minimum): a skipped-category reply satisfies the hook with the single line `STATUS: GREEN, no change made`, which is a scope marker, not a completion claim.
