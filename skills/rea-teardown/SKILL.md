---
name: rea-teardown
description: Tear down a trading tool with REA reverse engineering and handle its evidence so large bundles never break the backup or a public save.
version: 1.0.0
---

# REA Teardown

## Identify and capture the target

- Identify the target type first and pick the matching REA route for a JavaScript app, a native binary, a dotnet assembly, an Android package, a website or EVM bytecode.

- Run the doctor check and source the engines environment before a native binary teardown that needs Ghidra.

- Pivot to a browser capture of the live web app when a vendor command has been retired or when a JavaScript analysis returns only a thin framework shell whose logic loads remotely.

- Keep analysis local and read only by default and never execute an untrusted binary outside a bounded capture in a scratch directory.

## Run the trading checks

- Name what the tool actually computes in one sentence from the decompiled or traced signal path and say plainly when that logic cannot be found.

- Check for repaint by looking for reads of the forming bar and quote the code that proves or clears it.

- Check for future leak by looking for future indexing, lookahead requests and recalculated historical values and treat one proven leak as fatal to any backtest claim.

- Audit every vendor claim against an evidence line and mark each one confirmed, refuted or unverifiable.

- Test performance claims against the vendor own exported data when it exists and recompute the arithmetic before repeating any win rate, profit factor or trade count.

- Record outbound network calls and treat credentials or wallet data leaving the box as an instant fail reported to the user at once.

## Handle the evidence bundle

- Save the evidence bundle under the teardown directory with its content hash and keep the hash in the teardown report.

- Measure every evidence file before any backup, commit or GitHub save and never stage a single file over the host limit intact.

- Split any oversized evidence file into parts of 20 MB or smaller for the blob save route and record the original size and sha256 beside the parts.

- Verify each split part by read back hash before deleting any local copy and keep the local copy when read back proof is missing.

- Scan any bundle headed for a public repo for personal identifiers before the save and route the save through the gated writer when one exists.

## Write the verdict and the handoff

- Write the teardown report with the target and its sha256, the one line verdict, the quoted signal logic, the repaint and future leak result, the claim audit, the network result and the named limitations.

- Grade the result green, partial, blocked or unverified and quote the evidence behind any claim that a tool cheats or fabricates its record.

- Extract a clean room specification only when the teardown found a real primitive and state that a clean extraction is not a backtest.

- Write the handoff with the falsifiable claim and its kill criteria so the research protocol, not the teardown, decides whether it earns a sleeve.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- Compare two versions of the same tool when a vendor may have changed the logic between releases.

- Cross check a web screener claim in the live browser when the static bundle and the served app disagree.
