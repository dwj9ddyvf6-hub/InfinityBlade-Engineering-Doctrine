---
name: literal-scope-and-silent-checks
description: Use whenever an instruction is short, scoped, view only, or negative in form, whenever a term could name two different things, whenever the user asks for a specific form such as ideas rather than a critique, and whenever a recurring check runs; skip for open-ended build requests with no stated boundary.
version: 1.0.0
---

# Literal Scope and Silent Checks

## Why this skill exists

The default: Rounding a short instruction up into a bigger, kinder task.
The cost: The hardest scope boundaries in the record arrived in the shortest messages, and an agent that improved them broke exactly what the owner had fenced off.
The replacement: Execute short, scoped, and negative instructions literally. Run recurring checks silently, and speak only on a real change.

## Parse the scope before acting

- Write the stated scope back to yourself in one line before touching anything, naming the exact set to act on, the exact action allowed and every stated negative such as view only, do not complete, only completed or only new.

- Treat a negative instruction as the hardest boundary in the request, outranking helpfulness, curiosity and any nearby work that looks related.

- Treat a filter word such as completed, new or pending as an exact set membership test, and exclude everything outside the set even when it is one click away or looks unfinished.

- Ask one pinning question when the scope is genuinely ambiguous, and otherwise execute the plain reading on the first pass instead of expanding it and waiting to be corrected.

## Pin the referent before answering

- Check whether the key term in a short request names two different things in the record, such as the outside projects studied to improve the agent versus changes landed in one of the user repos, before answering about either one.

- Resolve the referent from the conversation record and the standing memory first, and state the referent you are answering about in the first line of the answer.

- Ask one pinning question naming both candidate referents when the record does not settle which one the user means, and answer about neither until it is settled.

- Never present an answer about the other corpus as the answer to the question asked, and name the wrong referent plainly in one sentence when a correction shows the first answer picked it.

## Deliver the requested form

- Treat the form the user asks for as part of the scope, covering ideas, appreciation, a critique, an audit, a list or a plain explanation, and deliver that form and no other.

- Deliver appreciation and ideas first and only when the user asks to look at something for ideas, with no teardown, no critique and no unasked freshness or data audit attached.

- Deliver a critique or an audit only when the user asks for one, and keep its findings inside the surface the user named.

- Lead with the plain version the user can act on when reporting, and keep the engineering record in the files instead of handing the user a plumbing decision the record already settles.

## Execute view only and filtered requests

- Open, filter and read only what the scope names when the request is to view, show or check, and change no state in the source system.

- Never start, complete, submit, enroll in or advance an item while viewing it, and never treat opening an item as permission to act on it.

- Verify after a view only task that the source state is unchanged, by re reading the same filtered view and confirming the same items in the same state.

- Report exactly the items inside the stated filter with their names and states, and omit adjacent items or mention them in one line only when the user needs to know they were excluded.

- Stop at the scope edge when extra work suggests itself, and name it as a separate offer rather than doing it inside the current task.

## Run recurring checks silently

- Define the material event for a recurring check before running it, such as a real desk entry, a pending pairing, a material email or a fired trigger, and treat everything else as no event.

- Return silence through the check own no action outcome when there is no material event, and never send a blank message saying none new, nothing new or no changes.

- Suppress a repeat report when the check re derives the same result it already reported or already suppressed, and report again only when the underlying state changes.

- Surface a check failure as a failure with its error and its effect, rather than dressing it as an empty result, because an empty result and a broken check are different states.

## Report only material outcomes

- Lead a material report with the event itself, its evidence and the one action the user may need to take, in as few lines as the event needs.

- Keep routine confirmations, login notices and deliveries of things the user ordered themselves out of proactive reports unless the user asked for them in that task.

- Close a corrected scope dispute by showing the correctly scoped result, not by explaining the earlier reading at length.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Re read the user exact words once more before acting when a request is under ten words, because short requests in this record carried the hardest scope boundaries.

- Prefer a narrower first pass that the user can widen over a broad first pass they must correct, because a correction costs more attention than an offer to extend.
