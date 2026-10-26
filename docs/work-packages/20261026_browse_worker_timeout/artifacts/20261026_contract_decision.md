# Browse transparency contract decision

Date: 2026-10-26 UTC. Starting implementation: dcfb634210a1ce0be8dd21dc12b005e887d8f052.

Roger explicitly directed reverting the filesystem path-resolution/lifecycle
mechanism, requiring browse/download to reflect actual directories and allowing
only security and PII guards. This authorizes exposing existing stale, partial,
legacy and unreceipted files; it does not authorize changing producer/report
eligibility or security boundaries. No further approval is required.

Applicable contracts: browse-filesystem-contract.md (new canonical rule),
weppcloud-browse-auth-contract.md, roads-preparation-lifecycle-contract.md,
file-dependency-freshness-contract.md and Roads specification. Amendments are
pending implementation. Closed prior packages are historical and unchanged.

Classification: intentional operator-approved semantic reversal with performance
benefit. Remove Roads guards from browse listing/manifest/download/schema/files
and direct D-Tale file viewers, retaining existing authorization, PII controls,
containment and byte-consistency checks. Remove legacy raw-archive exclusions
if they hide physically present files solely due to retired format status.
Do not revive virtual archive browsing. Compatibility: direct files become
available regardless of Roads publication; reports retain eligibility. No new
schema, producer, permission or deployment changes. Security impact: low when
existing auth/path/PII boundaries are preserved and tested.

Regression: real on-disk missing/empty/populated/legacy/stale/locked states,
permitted alias and raw retired archive; exact manifest path and byte readback;
negative auth/containment/PII tests; large project collector timing. D-Tale
lazy source changes still fail changed_source; eager snapshots stay usable.
Two independent read-only contract reviews precede implementation checkpoint.
