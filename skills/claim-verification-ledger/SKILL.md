---
name: claim-verification-ledger
description: Use whenever a not found, closed, or cannot be done verdict is about to be reported, whenever a save, backup, push, export, or deletion is about to be reported done, and whenever a delegated or background result is about to be repeated as fact.
version: 1.0.0
---

# Claim Verification and Coverage Ledger

## Frame the claim before checking it

- Write down the exact claim you might have to make, such as this file does not exist, this post was never published, this source is closed, this save is complete or this delegated result is true.

- List every identifier the target could hide under before you search, covering exact names, shortened names, author names, handles, alternate spellings, file paths, branch names and referenced dates or commits.

- Name the places the target could plausibly live, covering the named source, its archives, mirrors, local copies on this machine, linked threads or replies and any index or manifest that points at it.

- Treat any claim assembled from memory, from a pusher report or from the files already in flight as unverified until it matches a fresh check of the source or the destination.

## Enumerate the set before saving

- Write the save set down as an explicit enumeration from the source directory, index or manifest before moving, pushing or deleting anything.

- Count the enumeration and record its total size and its largest file so an oversized item is routed before it can fail a commit.

- Ask what sibling sets the same ruling covers whenever a save is defined by a category rather than a path and add any sibling set the answer names to the enumeration.

## Work independent routes and read back

- Try at least two routes that fail for different reasons, such as a direct link or direct read, a search inside the source itself, an index or API lookup, and a local filesystem or repository search.

- Check the exact revision, date, branch or thread the user or the record pointed at, not only the current head, the newest page or the first screen of results.

- Follow pagination, reply threads and older timeline windows to their end before treating a shallow window as the whole corpus.

- When a route returns private, walled or invite only, test whether the underlying content is still readable through a direct link, an embedded copy, a mirror or an archived copy before calling it closed.

- Treat a tool error, an empty result page and a failed lookup as facts about that one route, and record the exact error or empty result beside the route that produced it.

- Save each enumerated item and then read it back from the destination and compare its hash or byte count against the source record.

- Report save progress as the verified count over the enumerated total, counted at the destination, never as the count a pusher claims to have sent.

- Keep the local copy until its read back proof exists and delete local bulk only after that proof, leaving a short note that names the destination repo, branch, path and commit.

- Retry a failed save by re-reading the destination state first so two writers racing the same repo rebase on the landed state instead of bouncing each other.

- Restart a killed save from its verified count and its enumeration rather than from the start and say which items remain unverified.

## Verify a delegated or reported claim

- Treat every delegated handback, background report and summary number as a claim until it is checked against the files, tree or system of record it names.

- Re-read the primary record behind any garbled, surprising or load bearing number and report the re-read value with its source instead of the reported one.

- Check a claimed commit by confirming the commit exists and the final tree matches it before repeating any landing, cure or completion claim.

- Name any claim that cannot be verified as unverified in the report rather than passing it on as a result.

## Prove absence separately

- Keep a coverage ledger while you hunt with four parts, covering routes searched, routes excluded with the reason, routes unavailable with the error seen, and how far pagination or timeline depth actually reached.

- Require the ledger to show that every plausible home from the framing step was either searched or named as unavailable before any absence claim is allowed.

- Ask what would prove the opposite, then run that one check, such as opening a link the user supplied, asking a peer source that found it before, or searching under the author name alone.

- Stop and revise the claim the moment any route contradicts it, and report the contradiction instead of defending the earlier negative.

## Watch for false completion signals

- Treat a pusher success report as a claim, because progress counts only at the destination after read back and comparison.

- Treat a save set built from files already in flight as incomplete, because whole sibling categories were once missed exactly that way.

- Treat a detailed background report as a claim, because a fabricated completion report already reached the user once and every handback gets checked against the record before it is repeated.

- Treat a mostly verified save as partial, and report the verified count over the enumerated total with the remainder named instead of calling it done.

## Report the outcome

- Report a found item with the route that found it and the exact location, so the user can reach it without redoing the hunt.

- Report a not found result only with its coverage ledger attached, and phrase it as not found in the places searched rather than as proof that it does not exist.

- Report a blocked route as blocked, naming the exact route that remains untried and what would open it, instead of upgrading the block into an impossibility verdict.

- Name any earlier negative claim of yours that the hunt reversed, in one plain sentence, before giving the corrected result.

- Report saved only for items with read back proof and list the unverified remainder by name and count, with the enumeration total beside the verified total in every progress and completion report.

- Carry an incomplete save forward as an open item on the next relevant report until its verified count reaches its enumerated total.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Websites

- [GitHub](https://github.com/) for repository search at a named commit or branch when a connector search only covers the current head. Carry the exact repo, path and referenced commit into `browser.browse` and verify the file at that revision there.

## Alternatives for better results

- Start from a link, screenshot or name the user supplied and work outward from that anchor, because user supplied anchors repeatedly pointed at the real location after broad searches missed it.

- Search the local machine and its archives in parallel with the web route when the target is a document, post or package this desk may already hold.

- Prefer a manifest or scoreboard generated from the destination over one maintained by hand, and push a corrected manifest when the destination count exposes it as stale.

- Split a save that keeps dying on restarts into verified batches that each land and prove themselves before the next batch starts.
