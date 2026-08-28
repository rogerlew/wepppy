# WP12D Amendment 3 Advisory Correctness Review

**Amendment**: `PC-24/WP12D-20260827-3`
**Review status**: READY
**Review type**: advisory, pre-ratification

Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate

## Scope

Review the complete amendment-2 locale/config model plus the amendment-3
capability-refresh delta: one locale-to-graph hotpath, frozen-by-default stored
authority, complete refresh preview, exact acknowledgment, atomic graph
replacement, reversible manifest provenance, exact-current behavior, and
direct/browser parity.

## Verdict

READY for exact operator ratification. No unresolved High or Medium findings.

The review required and verified these corrections:

- refresh rebases the current envelope around unchanged project selections and
  refuses removed/incompatible selections;
- schema-v2 and preset-source refresh remain unavailable, while eligible
  schema-v3 Builder manifests require exact locale/profile/selection
  congruence;
- commit-point recovery, queue history, historical amendment inference, and
  latest-preview idempotent HTTP/RQ reconciliation match the existing
  transaction;
- historical provenance is limited to stored provider/binary and selected-
  chain identities, with exact JSON, sorting, null, and hashing contracts; and
- append-only structure validation uses current production identities plus a
  genuine test-only evolution pair. No production structural map transition is
  claimed until a separately ratified reader-first change supplies one.

No tests were run for this documentation-only advisory review. This advisory
does not satisfy the later binding reviews of the ratified canonical
checkpoint.
