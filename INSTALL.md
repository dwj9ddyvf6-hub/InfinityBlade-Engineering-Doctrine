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

## Confirm it works

Ask:

```text
Using InfinityBlade, state the SCOPE for this task before changing anything.
```

You should see Surface, Constraints, Outcome, Proof and Edges, and the final report should end with GREEN, PARTIAL, BLOCKED or UNVERIFIED plus receipts.

For a real behavior check, run a few cases from [eval-cases.md](skills/infinityblade/references/eval-cases.md) with and without the skill and compare.

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
