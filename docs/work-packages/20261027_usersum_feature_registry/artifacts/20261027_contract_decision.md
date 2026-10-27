# Public registry contract decision

Date: 2026-10-27 17:05 UTC
Starting revision: `0da9c9071069c37fdcf3df5a74b28d161b1af458`
Amendment: USERSUM-CATALOG-01

## Authority and Approval

Operator request: "scaffold and implement work-package to implement a feature
registry view as part of usersum. it should be public facing. the source is
open-source. there is no reason to secure the feature registry information."
This explicitly authorizes public registry metadata and implementation scope.
Follow-up operator instruction: "yes. commit and continue implementation"
authorizes the standalone contract commit and continued implementation. No
implementation edits may precede that ancestor.

## Contracts and Exact Delta

Amend `wepppy/weppcloud/routes/usersum/specification.md`, Public Feature Catalog,
and `wepppy/weppcloud/feature_registry/specification.md`, Public Metadata Catalog.
Add anonymous `/usersum/features/` with every validated feature/config entry,
including Internal/embargo, in source order. Display maturity, id, label,
backend, role/group policy, optional internal reason/date, feature prerequisites,
and config replacements. Runtime config overrides apply. Link the index outside
curated sections and reuse Jinja shell. No row visibility filtering or new
account lookup. Existing feature access governance, document visibility,
resource access, controller presentation, and CSRF contracts are unchanged;
this GET introduces no action or mutation. This is an additive enhancement,
not a conformance repair or a change to those owners' execution policies.

## Rationale, Compatibility, and Security

Open-source metadata need not be secured. A live Jinja view avoids stale copied
Markdown and already has index/search precedent. Separate config rows clarify
scope. No YAML value, role entitlement, run artifact, schema, or API is removed
or changed. Low security impact: fixed validated sources and escaped text only.
Do not turn metadata fields into arbitrary file reads or privileged actions.

## State and Request Matrix

Anonymous/authenticated requests, with and without role query filters, must
show identical rows. Missing optional fields render neutral values. Empty
validated collections show an explicit empty state. Populated collections show
all entries. Supported legacy optional metadata retains loader behavior.
Malformed registry data is exceptional and fails explicitly under the registry
failure contract. Hostile text is escaped; query strings cannot select files or
grant access. Absent run/account state is normal and is not consulted.

## Regression and Acceptance Evidence

Use existing usersum route/shell fixtures, plus real unmocked registry loaders
and real Jinja rendering. Compare complete ids and maturity values with loaded
registries, include Roads, internal entries and group-only policies, check
config overrides and URL prefixes, and confirm no login redirect. Exercise
empty and hostile metadata separately. Run focused usersum/registry tests,
frontend gates, broad pytest, and docs lint. Retain rendered HTML readback.

## Review Disposition

Two independent read-only reviews approved; see [review disposition](20261027_contract_reviews.md). One low formatting finding was corrected. Commit authority granted by the operator.
Implementation conformance pending; no production or deployment claim.
