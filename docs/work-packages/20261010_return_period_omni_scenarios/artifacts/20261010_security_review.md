# Security review: return-period Omni comparisons

Reviewer: `/root/contract_security`, independent read-only security reviewer.
Date: 2026-10-10 UTC. Reviewed working tree atop `946ec76fb`, with initial
contract ancestor `c5358daa7`. Generated docs_index.json excluded.
Related evidence: `20261010_correctness_review.md`, `20261010_validation.md`.

## Triage and decision

High impact under repository classification: URL-selected filesystem reads and
CSV output. Dedicated review completed. Security gate PASS; high/medium/low
findings: 0/0/0. No risk acceptance required. This is implementation review,
not deployment authorization or a substitute for outstanding validation gates.

## Surface checks

Existing authorization/CAP executes before discovery for HTML and CSV. There
is no new endpoint, mutation request, CSRF exception, or permission change.
Discovery anchors paths in the authorized project and validates definition-
generated scenario names. Child NoDb, catalog, completion evidence, and report
Parquets are contained before reads. Unknown/unavailable choices fail explicitly.

The reviewer traced actual readers: NoDb hydration resets persisted `wd` to the
supplied child directory; ReturnPeriodDataset uses fixed event/rank paths under
that directory, so catalog root/fs_path fields cannot redirect report reads.

Direct tests exercise root/intermediate/child/state/output/catalog escapes,
restored valid children, and permitted shared climate/watershed inputs. Optional
absent/empty Omni remains harmless. Jinja escapes names and attributes; accepted
enum-prefixed labels cannot lead with spreadsheet formulas. CSV uses the existing
serializer and preserves numeric values.

Comparison memoization is disabled and staged inputs are checked before report
loads. There is no queue, subprocess, external dependency, archive exclusion,
or new persisted report. Unexpected failures retain the diagnostic boundary.

## Evidence and residual limits

Reviewer inspected direct filesystem/restoration tests, real-dataset CSV tests,
actual-template comparisons, and navigation tests; parent executes validation.
Final counts and browser scope are recorded separately in the validation artifact.

Containment uses resolved paths followed by reads, not atomic file-descriptor
confinement against concurrent filesystem replacement. This assumes established
application ownership of run files; URL input alone cannot replace files.
Comparison cost grows with selected configured children; inputs are deduplicated
and confined to discovered scenarios. Neither is an identified blocking finding.

Post-fix confirmation: reviewer rechecked the final filtered-empty helper,
calendar-date and per-metric interval changes, and malformed-calendar regression.
PASS remains unchanged. Reviewer verified all five source/fixture manifest hashes
match the final files; no new findings.
