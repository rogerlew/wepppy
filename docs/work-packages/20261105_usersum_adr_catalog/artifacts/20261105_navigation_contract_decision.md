# ADR sidebar placement amendment

Date: 2026-11-05 UTC. Base: `0b804f1ff`; feature implementation remains in the
working tree from the reviewed, forest-verified change.

The operator explicitly requests ADRs after Quick Start and before Feature
Maturity and Release Governance in the navigation panel. This supersedes the
original outside-curated-sections placement and authorizes Start Here inclusion.
The active package already has checkpoint commit authority.

Canonical amendment: Usersum specification **Automatic ADR catalog**. Preserve
shared navigation styling, existing index link, public access, automatic file
discovery, route registration and manifest/search behavior. This is an intended
presentation change only; there is no filesystem, persistence or safety boundary
change. Place one dynamic navigation leaf immediately after the existing Quick
Start leaf. Existing role views retain this public link.

Validate the actual live sidebar HTML for unique ADR link and exact sibling
order on the Help index and ADR catalog. Use existing scoped route/shell tests;
no new tests solely pinning this literal placement. No generated-index edit or new route registration is needed. Reload web workers
if their template caches retain the old placement.

Independent read-only reviews: `/root/adr_contract_correctness` approved with
no blocking findings; `/root/adr_contract_security` passed with no findings.
Both confirmed exact `usersum.weppcloud.quick_start` anchoring and requested
one-link/sibling-order readback. Both approvals precede implementation edits.

## Implementation evidence

Checkpoint ancestor: `6bedea271`. Moved the existing sidebar link into the
standard navigation list after `usersum.weppcloud.quick_start`. Forest template
caches retained the earlier placement; gracefully reloaded the verified
Gunicorn master. External Help index and ADR catalog both return HTTP 200 with
exactly one sidebar ADR link between Quick Start and Feature Maturity and Release
Governance. Existing focused route/shell suite: 100 passed.

The operator also reported apparently missing records. Direct source/list
comparison confirms all 138 are present; 47 lack explicit Date metadata and sort
last. ADR-0131 through ADR-0135 are among these. Asked the operator to choose
verified Date normalization or numeric ordering; neither change is applied yet.
