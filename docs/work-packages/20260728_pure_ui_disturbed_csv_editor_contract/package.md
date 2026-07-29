# SURF-10 Pure UI Disturbed CSV Editor Contract

**Status**: Closed 2026-07-28 UTC
**Package ID**: SURF-10
**Security impact**: `high`

## Purpose

Verify the shared CSV editor from authorized run-scoped rendering through
session authorization, atomic snapshot load, editable spreadsheet behavior,
optimistic-concurrency save, stale recovery, and explicit runtime dependency
failure.

## Concise Intent Contract

An authorized user receives one run-scoped editor whose config contains the
snapshot, metadata, save, and session-token URLs supplied by its producer. The
client authorizes before loading, constructs the spreadsheet from the atomic
snapshot, submits nonblank rows with the loaded SHA-256 precondition, prevents
duplicate or stale edits, and reloads current data without discarding the
stale lock when recovery fails.

The disturbed producer resolves base or extended lookup identity once and uses
the same variant for render, snapshot, metadata, and mutation. Mutation remains
authorized, locked, preconditioned, validated, atomic, and observable. Missing
spreadsheet runtime dependencies, malformed responses, rejected session
authorization, network errors, and unavailable version fingerprints fail
visibly and leave saving disabled.

## Scope

- `wepppy/weppcloud/templates/controls/edit_csv.htm`;
- disturbed editor, metadata, snapshot, and mutation routes in
  `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`;
- disturbed lookup snapshot/write helpers already exercised by the route;
- the Geneva CN table only as a second producer of the shared editor contract;
- actual rendered-template, executable inline-client, route, and focused NoDb
  lookup evidence.

## Exclusions

DOM-23 retains Disturbed/BAER workflow, build, upload, and RQ ownership. Geneva
domain behavior remains DOM-27/SURF-11. This package does not change lookup
columns, parameter values, formulas, variants, authorization policy, queue
wiring, or add a frontend dependency.

## Acceptance

Actual rendering proves escaped run/config values, producer URLs, CSRF,
accessible status/actions, and runtime assets. Executable client tests prove
authorization-before-load, successful save, blank-row pruning, in-flight and
stale guards, stale polling/recovery, safe errors, and missing-runtime failure.
Route/NoDb tests prove authorization, variant identity, no-store snapshots,
locked optimistic concurrency, validation, atomic persistence, and reload.

Any confirmed mismatch receives the smallest backward-compatible conformance
repair and exact regression coverage. A dedicated security review must pass
with no unresolved high or medium findings.

## Outcome

SURF-10 closed without a production repair. Actual rendering now fixes the
escaped config, run-scoped producer URLs, CSRF, actions, accessibility, and
remote runtime assets. Four executable production-inline tests cover
authorization-before-load, SHA-bound save with blank-row pruning, stale poll
and failed recovery, stale-save conflict, and missing spreadsheet runtime.

Existing route and NoDb evidence proves variant confinement, no-store atomic
snapshots, authorization, locking, validation, stale rejection, atomic
persistence, and reload. The dedicated security review passed with no
unresolved finding. The full Python and frontend suites passed.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; operator directed SURF-10 execution
  and this package preserves existing lookup values and formulas.

## Related Packages

- **Depends on**: `docs/work-packages/20260728_disturbed_baer_ui_contract/`
- **Related**: `docs/work-packages/20260325_disturbed_lookup_hardening/`
- **Related**: `docs/work-packages/20260728_pure_ui_geneva_summary_report_contract/`

## Security Review Gate

The editor mutates run-scoped model input and crosses browser session, CSRF,
filesystem, locking, and concurrency boundaries. A dedicated review is
required at
`artifacts/2026-07-28_security_review.md`.
