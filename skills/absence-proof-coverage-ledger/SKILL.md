---
name: absence-proof-coverage-ledger
description: Use whenever a not found, does not exist, never published, closed, or cannot be done verdict is about to be reported, even when one search already came back empty; skip for ordinary lookups where the item is expected to be found.
version: 1.0.0
---

# Absence Proof and Coverage Ledger

## Why this skill exists

The default: Reporting not found after one search in one place.
The cost: A sworn absence that was wrong: the thing existed, in the place, at the revision, nobody checked. The reader acted on the absence and paid for it.
The replacement: Prove absence separately, with a coverage ledger naming searched, excluded, and unavailable, or report only not found in the places searched.

## Frame the hunt before searching

- Write down the exact claim you might have to make, such as this file does not exist, this post was never published, this source is closed or this feature is unavailable.

- List every identifier the target could hide under before you search, covering exact names, shortened names, author names, handles, alternate spellings, file paths, branch names and referenced dates or commits.

- Name the places the target could plausibly live, covering the named source, its archives, mirrors, local copies on this machine, linked threads or replies and any index or manifest that points at it.

## Work independent routes

- Try at least two routes that fail for different reasons, such as a direct link or direct read, a search inside the source itself, an index or API lookup, and a local filesystem or repository search.

- Check the exact revision, date, branch or thread the user or the record pointed at, not only the current head, the newest page or the first screen of results.

- Follow pagination, reply threads and older timeline windows to their end before treating a shallow window as the whole corpus.

- When a route returns private, walled or invite only, test whether the underlying content is still readable through a direct link, an embedded copy, a mirror or an archived copy before calling it closed.

- Treat a tool error, an empty result page and a failed lookup as facts about that one route, and record the exact error or empty result beside the route that produced it.

## Prove absence separately

- Keep a coverage ledger while you hunt with four parts, covering routes searched, routes excluded with the reason, routes unavailable with the error seen, and how far pagination or timeline depth actually reached.

- Require the ledger to show that every plausible home from the framing step was either searched or named as unavailable before any absence claim is allowed.

- Ask what would prove the opposite, then run that one check, such as opening a link the user supplied, asking a peer source that found it before, or searching under the author name alone.

- Stop and revise the claim the moment any route contradicts it, and report the contradiction instead of defending the earlier negative.

## Report the hunt

- Report a found item with the route that found it and the exact location, so the user can reach it without redoing the hunt.

- Report a not found result only with its coverage ledger attached, and phrase it as not found in the places searched rather than as proof that it does not exist.

- Report a blocked route as blocked, naming the exact route that remains untried and what would open it, instead of upgrading the block into an impossibility verdict.

- Name any earlier negative claim of yours that the hunt reversed, in one plain sentence, before giving the corrected result.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Websites

- [GitHub](https://github.com/) for repository search at a named commit or branch when a connector search only covers the current head. Carry the exact repo, path and referenced commit into `browser.browse` and verify the file at that revision there.

## Alternatives for better results

- Start from a link, screenshot or name the user supplied and work outward from that anchor, because user supplied anchors repeatedly pointed at the real location after broad searches missed it.

- Search the local machine and its archives in parallel with the web route when the target is a document, post or package this desk may already hold.

## Relations

This skill is the canonical home of absence proof. claim-verification-ledger routes absence claims here and governs the wider set (saves, delegated results, closure claims); where the two overlap on an absence claim, this file governs.
