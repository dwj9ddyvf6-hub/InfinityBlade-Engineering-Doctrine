---
name: save-readback-verification
description: Use whenever a save, backup, push, export, or deletion is about to be reported done, and whenever a delegated, background, or subagent result is about to be repeated as fact, even when the save looks small; skip for live execution proof or absence proof.
version: 1.0.0
---

# Verified Saves and Claim Checks

## Enumerate the set before saving

- Write the save set down as an explicit enumeration from the source directory, index or manifest before moving, pushing or deleting anything.

- Count the enumeration and record its total size and its largest file so an oversized item is routed before it can fail a commit.

- Ask what sibling sets the same ruling covers whenever a save is defined by a category rather than a path and add any sibling set the answer names to the enumeration.

- Treat a set assembled from memory or from the files already in flight as incomplete until it matches a fresh enumeration of the source.

## Save with read back proof

- Save each enumerated item and then read it back from the destination and compare its hash or byte count against the source record.

- Report progress as the verified count over the enumerated total, counted at the destination, never as the count a pusher claims to have sent.

- Keep the local copy until its read back proof exists and delete local bulk only after that proof, leaving a short note that names the destination repo, branch, path and commit.

- Retry a failed save by re-reading the destination state first so two writers racing the same repo rebase on the landed state instead of bouncing each other.

- Restart a killed save from its verified count and its enumeration rather than from the start and say which items remain unverified.

## Verify a delegated or reported claim

- Treat every delegated handback, background report and summary number as a claim until it is checked against the files, tree or system of record it names.

- Re-read the primary record behind any garbled, surprising or load bearing number and report the re-read value with its source instead of the reported one.

- Check a claimed commit by confirming the commit exists and the final tree matches it before repeating any landing, cure or completion claim.

- Name any claim that cannot be verified as unverified in the report rather than passing it on as a result.

## Report the outcome

- Report saved only for items with read back proof and list the unverified remainder by name and count.

- State the enumeration total beside the verified total in every progress and completion report so a partial save can never read as a complete one.

- Carry an incomplete save forward as an open item on the next relevant report until its verified count reaches its enumerated total.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Prefer a manifest or scoreboard generated from the destination over one maintained by hand, and push a corrected manifest when the destination count exposes it as stale.

- Split a save that keeps dying on restarts into verified batches that each land and prove themselves before the next batch starts.
