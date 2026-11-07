# Memory extraction spec

Use this spec when turning observations into facts for `MemoryStore`.
Extraction is specified, not improvised.

## Entry shape

Each fact is one JSON object matching `templates/memory-fact.json`:

- `id`: stable identifier chosen by the host's deterministic ID rule.
- `text`: self-contained, 15 to 80 words, proper nouns preserved. A reader
  who sees only this fact must understand what it claims.
- `bucket`: one topic bucket (preferences, goals, work, or a host bucket
  added at namespace level).
- `entities`: the named entities the fact is about. Retrieval boosts matched
  entities, capped, and penalises hubs.
- `status`: `current`, `proposed`, or `superseded`.
- `inferred`: true when the fact is derived, not stated. Derived facts also
  carry `review: pending` until a human approves or declines them.
- `valid_from`, `valid_until`, `learned_on`: bi-temporal stamps. When a fact
  stopped being true and when memory learned it are different facts.
- `edge` and `supersedes`: set by `MemoryStore.apply_edge`, never by author
  habit alone.

## Extraction rules

1. Evidence-bound: every fact names its evidence in the host's provenance
   field or source note. An ungrounded addition fails operation grading.
2. Echo-aware: the extractor's own prior output is not new evidence. Copies
   of one statement are one fact, and a feedback loop is junk, not support.
3. Contamination-aware: text quoted from a third party is attributed to that
   party, not adopted as the subject's fact.
4. Transition-preserving: when a fact changes, keep the predecessor and link
   it with an `updates` edge. Do not rewrite history into a single present.
5. Date-grounded: ground relative dates against the observation date, which
   is recorded separately from today.
6. Existing memories are shown to an extractor by temporary integer labels,
   never by real ID, so the extractor cannot forge references.
7. Success is reported only on store confirmation. A failed write is a loud
   failure, distinct from an empty extraction.
8. Future assertions are normalised by `normalize_future_fact`: true-from is
   the date stated; a deadline is never true-until.

## Evaluation

Keep a small fixed probe set per store: knowledge-update, temporal, and
preference questions with known tiers. Run it after any change to extraction
or ranking and record which tier each probe returned. Grade operations
separately with `score_operations`: extraction precision and false-memory
rate for adds, and update correct, hallucination, and omission rates for
updates. End-to-end answer quality alone does not grade this pipeline.
