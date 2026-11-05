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
no new tests solely pinning this literal placement. No generated-index edit or
worker reload is needed for the existing endpoint's template placement.

Independent read-only reviews: `/root/adr_contract_correctness` approved with
no blocking findings; `/root/adr_contract_security` passed with no findings.
Both confirmed exact `usersum.weppcloud.quick_start` anchoring and requested
one-link/sibling-order readback. Both approvals precede implementation edits.
