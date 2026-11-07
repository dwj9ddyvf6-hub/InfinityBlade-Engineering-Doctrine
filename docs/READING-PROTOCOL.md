# Read the whole doctrine. Make the depth usable.

**Do not skim your way into claiming this discipline. Read every part, understand what it changes, and prove that you can use it.** The primer gives you the reason. The core gives you the loop. The references, research, specialist methods, implementations and failure tests show where the loop succeeds, where it can be misapplied, and how to make it hold under pressure.

The target is complete engagement with one exact repository revision. A context window is a batch size, not a reason to discard the rest. Finish the read across bounded sessions, preserve what you learned, and resume the exact unfinished point. Use the [ascent path](ASCENT-PATH.md) to convert coverage into applied judgment.

## Start here and keep going

1. Read [PRIMER.md](../PRIMER.md), then [the core](../skills/infinityblade/SKILL.md).
2. Read [the operating paths](OPERATING-PATHS.md), [the examples](../skills/infinityblade/references/examples.md) and [review mode](../skills/infinityblade/references/review-mode.md). Write one outcome contract and one discriminating check for a fresh task.
3. Read the field manual, playbooks and all incident patterns. For each family, identify the first failed boundary and the mechanism that cures it.
4. Read all eighteen enhancement disciplines, the registers and their historical corrections. Follow every implemented surface through its module, template and tests. Preserve the distinction between an adopted requirement, a shipped mechanism and a demonstrated host effect.
5. Read every specialist skill and its complete resources. Even outside its domain, extract the transferable method: identity before action, geometry before narration, independent cross-checking, consumer census, or temporal provenance.
6. Read the research, source ledgers, evaluation machinery, installation tooling, metadata, CI and changelog. Ask what each check actually rejects and which claim remains outside its reach.
7. Complete every remaining tracked path in the reading ledger. Finish the ascent exercises, then carry the resulting methods into authorized work.

This sequence prioritizes meaning; the tool below inventories everything. Neither a router suggestion nor an index page removes an obligation from that inventory.

## Use a pinned, resumable ledger

The automated reader requires a Git checkout and reads its pinned objects. Run from the repository root. Keep the SQLite ledger **outside the repository**: notes may contain task-specific or private context and do not belong in a public source bundle.

For a Gitless source bundle, first verify `BUNDLE-MANIFEST.json`, then use its complete file/hash inventory with the host's bounded reader. Record the same source identity, path, byte range, reading note and unresolved parts in an external ledger. Read every manifest member; absence of the Git-backed CLI does not reduce the reading obligation.

```bash
python3 tools/read_repository.py --repo . --ledger /tmp/doctrine-reading.sqlite init --ref HEAD --chunk-bytes 16000
python3 tools/read_repository.py --repo . --ledger /tmp/doctrine-reading.sqlite next --path PRIMER.md
```

Read the complete returned chunk. Then acknowledge its actual receipt ID with a substantive note:

```bash
python3 tools/read_repository.py --repo . --ledger /tmp/doctrine-reading.sqlite ack RECEIPT_ID --note 'Method: preserve every acceptance row when one route fails. Application: isolate the failed transport and continue independent rows. Open question: which receiver read resolves an uncertain send?'
python3 tools/read_repository.py --repo . --ledger /tmp/doctrine-reading.sqlite next
python3 tools/read_repository.py --repo . --ledger /tmp/doctrine-reading.sqlite status
python3 tools/read_repository.py --repo . --ledger /tmp/doctrine-reading.sqlite notes
```

Replace `RECEIPT_ID` with the emitted value. `next --path exact/path` lets you follow the curriculum before returning to inventory order. `ack --notes-file PATH` accepts a longer note. Continue until every text chunk is delivered and acknowledged and every non-text obligation is separately resolved. Do not acknowledge unseen, truncated or unread content. If your tool truncates a chunk, retrieve it completely with a smaller reading plan or another bounded reader before recording coverage.

The pinned commit and source objects define the read. If HEAD advances, finish or explicitly supersede the old plan, start a plan for the new revision, and inspect changed material. Old notes remain useful history; they do not silently certify new bytes.

## Read beyond Markdown

Code shows whether the promised mechanism exists. Tests show the cases actually exercised. Templates show which facts survive a handoff. Configuration shows what runs. Fragments contain full domain methods. Registers preserve rejected alternatives and reopening conditions. Historical research explains how a conclusion was formed, including later corrections. **Read all of them.** A Markdown-only pass cannot speak for the repository.

An opaque or unsupported format needs its proper reader. Bind its review to the exact source blob and record a report through:

```bash
python3 tools/read_repository.py --repo . --ledger /tmp/doctrine-reading.sqlite review --path exact/path --report external-review.json
```

The report contract is `{"source_git_blob":"<pinned blob>","reader":"<reader and method>","summary":"<what was inspected>","coverage":"complete","parts_reviewed":["<actual part>"],"unread_parts":[]}`. Retain the reader, method, coverage and source identity in that report. Readable text cannot use this route to bypass chunk reading; `notes --offset N --limit N` pages saved notes when their volume grows. An external review is an attestation with an inspectable source, not a text-chunk acknowledgement. An inaccessible object remains named and unread. Do not relabel an omission as an exemption to earn complete coverage.

## Turn notes into useful understanding

At the end of each reading area, write five things in your private ledger:

| Question | Required substance |
|---|---|
| What failure does this prevent? | A concrete wrong result, not a slogan. |
| What changes the decision? | The observation or boundary that separates the plausible route from the correct one. |
| How does the mechanism work? | Inputs, state transition, output and failure behavior. |
| Where could I misuse it? | A near miss, conflicting scope, stale fact or unsupported generalization. |
| How will I apply it next? | A fresh case, expected artifact and falsifying check. |

Carry unresolved questions forward. A contradiction is a reason to inspect the source and governing scope; resolve it with evidence, not by forgetting one side.

## Coverage and mastery are separate achievements

`status` reports text delivery and noted coverage, external review attestations, unread material and revision drift. It cannot inspect comprehension or prove improved decisions. Earn that second claim through the [ascent exercises](ASCENT-PATH.md) and [behavior evaluation](BEHAVIOR-EVALUATION.md).

A team audit may divide files, provided every file names its reader and the integrator checks the findings and changed artifacts. An individual learner still reads the whole repository; receiving teammates' summaries does not make those source bytes personally read. Report the claim actually earned: individual full reading, attributable team coverage, completed exercise, or tested outcome.

**Finish with a next action, never a ceremonial declaration.** If reading is incomplete, name the revision, unread area and next chunk. If reading is complete, name the fresh task on which you will apply the method and the result that will prove the transfer.
