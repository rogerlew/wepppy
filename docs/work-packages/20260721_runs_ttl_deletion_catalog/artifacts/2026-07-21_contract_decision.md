# Runs TTL Deletion Catalog Contract Decision

**Status**: Proposed for independent ratification review  
**Decision time**: 2026-07-21 22:15 UTC  
**Starting implementation revision**: `a4bd3b63d5be56cfa3a5fe38448c5b972706d89e`  
**Registered owner**: REM-02, borrowing the listed SURF-06 boundary only  
**Operator approval**: The user explicitly authorized full work-package execution,
including the contract, reviews, and implementation, on 2026-07-21.

## Applicable Authority

- `docs/standards/contract-first-change-standard.md`, which requires this
  checkpoint and a standalone accepted ancestor before implementation.
- `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/child_package_register.md`, which registers SURF-06 as the Runs catalog
  owner and permits a concrete bounded remediation only after registration and
  review.
- `wepppy/weppcloud/utils/run_ttl.py` is implementation evidence for the durable
  metadata fields, not normative user-interface authority.

No RQ response/error, CSRF, output-scope, NoDb concurrency, data-schema, or
parameterization contract changes apply. The existing catalog's owner filtering,
authentication, permission rules, and deletion action semantics remain unchanged.

## Normative Delta

For every run that the existing authenticated catalog is already authorized to
return, the lifecycle column has exactly these presentation states:

1. When TTL policy is `rolling_90d` and `expires_at` is a timezone-aware
   ISO-8601 timestamp, render `TTL Deletion: <UTC ISO-8601 time>` followed by a
   template-generated `Learn More` link to `usersum.weppcloud.run_ttl_deletion`.
2. When TTL deletion is disabled, excluded, missing, malformed, has an unknown
   policy, or lacks a usable expiration, render `Last Modified: <time>` and do
   not render a deletion time or the
   policy link.
3. The existing `last_modified` catalog field remains available and unchanged.
   Every catalog row adds `ttl_deletion_at`, which is either `null` or a UTC
   ISO-8601 string ending in `Z`; incomplete/legacy directories use `null`.

The dedicated Usersum document is the user-facing explanation of the active
rolling policy, access refresh, disabled state, and existing role-gated control.
It must not promise retention, restoration, or a deletion schedule beyond what
the persisted TTL metadata says.

## Rationale and Compatibility

Users need to distinguish routine editing history from deletion risk. Reusing a
single column avoids widening an already dense table. Showing last modified for
disabled TTL preserves useful historical context without falsely representing a
disabled run as scheduled for deletion. Existing clients keep working because
the payload only adds fields and retains `last_modified`.

## Security Impact

The remediation is high-risk by registered-owner inheritance. It may expose only
TTL metadata from the same run directory that the catalog has already selected
for an authenticated, authorized caller. No new endpoint, permission, mutation,
TTL touch, path input, queue action, or external link is introduced.

## Proposed Regression Evidence

- Metadata construction reads an active TTL state without mutating its file and
  exposes a normalized active expiry.
- Disabled, excluded, missing, malformed, unknown-policy, invalid-timezone, and
  incomplete TTL states fall back to last modified without raising or changing
  the existing catalog result.
- Template rendering includes the exact labels and template-generated,
  prefix-aware doc-id URL; active rows have `Learn More`, fallback rows do not.
- A sentinel unselected run proves owner/admin catalog filtering completes before
  the TTL reader is invoked; a selected admin-alias run proves the allowed read.
- The Usersum doc-id route renders the dedicated guide and manifest/index lookup
  resolves it.

## Ratification Gate

Two independent read-only reviewers must approve the registration, authority,
compatibility, privacy/authorization scope, and regression plan. The primary
agent must disposition findings and obtain their post-fix confirmations. The
checkpoint, canonical contract, GOV-00A-M1B registration, raw review artifacts,
and review disposition must then be committed as a standalone ancestor before
production code or test files are edited.
