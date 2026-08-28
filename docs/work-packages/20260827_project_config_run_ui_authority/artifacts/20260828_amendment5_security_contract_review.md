# Amendment 5 Security Contract Review

**Amendment**: `PC-24/WP12D-20260828-5`
**Baseline**: `0ad76c547145bbe323148bac73410ff9cfcd01ef`
**Review mode**: fresh independent read-only review; amendment-3 approval not reused
**Security impact**: high
**Advisory verdict**: READY, 2026-08-28 10:45 UTC
**Binding verdict**: READY, 2026-08-28 16:35 UTC; High 0 / Medium 0 / Low 0
**Implementation verdict**: READY, 2026-08-28 18:16 UTC; High 0 / Medium 0 /
Low 0

## Advisory disposition

The initial review found one Medium self-authentication defect and one Low
preset-policy failure ambiguity. Both are closed:

- eligibility requires current canonical parent SHA-256 values, allowlisted
  override replay, byte-exact canonical rematerialization, and stored/source
  locale congruence;
- self-asserted project hashes and descriptive `source_revision` do not
  authenticate projection;
- fully congruent run-local forgery, parent drift, forged overrides, and locale
  mismatch have explicit negative evidence requirements; and
- unavailable, malformed, or inconsistent preset policy is auth-first
  diagnostic `503 builder_registry_error` with no compatibility fallback or
  file/timestamp/reservation/mutation/enqueue side effect.

The reviewer reported no remaining High, Medium, or Low findings. Upload
authority, stored schema-v2/v3 isolation, finite source scope, reader-first
rollback, and the WP12 production reservation were also sound.

## Binding disposition

After exact operator ratification, a fresh binding security pass re-read the
ratified canonical diff against baseline
`0ad76c547145bbe323148bac73410ff9cfcd01ef` and reported BINDING READY with no
High, Medium, or Low findings. The rematerialization proof, auth-first policy
503, upload no-side-effect boundary, stored-graph isolation, finite scope,
reader-first sequence, dirty exclusions, and production hold remain intact.
Forest writer exposure and production remain unauthorized.

## Implementation disposition

The independent high-impact security review examined the implemented stored-
graph projection, hostile preset eligibility matrix, graph-authoritative
upload gate, consumer propagation, and no-side-effect rejection boundaries.
It reported READY with no High, Medium, or Low findings. The final tree binds
manifest and config validation to the exact loaded byte observations, requires
strict typed manifest policy fields, retains raw schema-v1 soil/model
authority, and projects only climate/landuse into current authority. Stored
schema-v2/v3 graphs and all previously accepted identities remain unchanged.

Exact-host `forest` writer/reopen/rollback acceptance remains required before
WP12D acceptance. Merge and production remain reserved to parent WP12.
