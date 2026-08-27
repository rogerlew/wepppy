# Security Review - WP12C

## Metadata

- **Package**: `docs/work-packages/20260827_project_config_builder_locale_expansion/`
- **Initiative / canonical branch**: `feature/project-owned-config` / `master`
- **Promotion policy**: WP12C pushes the initiative branch and deploys only to
  host `forest`; WP12 owns canonical merge and production
- **Reviewer**: Erdos (`wp12b_security_contract_review`)
- **Date**: 2026-08-27
- **Scope reviewed**: authenticated Builder description, validation, creation,
  persisted capability authority, and provider selection
- **Commit/branch context**: implementation from checkpoint `bb1745fd8` through
  exact candidate `b31eeb625`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: new request IDs select provider-backed persisted run
  authority through authenticated routes.

## Contract Review Findings

The second contract review identified one medium-severity concurrency defect in
the source boundary: `CligenStationsManager` mutates process-global database and
PAR-root state, while threaded requests can construct station metadata
concurrently. That can pair database rows with a different selected database's
PAR root.

The amended contract adds `wepppy/climates/cligen/cligen.py` to the exact source
boundary, requires instance-local database/PAR-root resolution, binds stable
station ID plus exact selector plus resolver adapter revision into provider and
manifest identity, and requires a direct real concurrent Legacy/2015/GHCN test
that proves every `StationMeta.parpath` remains under the selected owned root.
Independent re-review found this contract disposition complete.

## Implementation Review Findings and Disposition

The first implementation review found incomplete v3 climate closure, missing
stable-ID-to-selector binding, live-registry update recomposition, unsafe SQL
registration cleanup, imprecise registry diagnostics, and missing writer-enabled
cross-locale evidence. Remediation `9fd8b556b` closed those findings with exact
immutable graph contracts, typed station selectors, stored-authority update
resolution, compensating deletion tied to an exact registration receipt,
reservation retention after unsafe cleanup, canonical diagnostics, and direct
no-mutation route tests.

Re-review then found that absent/schema-v1 Builder authority could still be
promoted to a live schema-v2 graph. Candidate `b31eeb625` rejects that state
before `load_registry()` and preserves config/manifest bytes. Complete
legacy/no-capabilities and present-axis/no-schema regressions cover the boundary.
The same candidate restores ADR-0047 ownership for ESDAC, ASRIS, and Australian
land cover.

The reviewer confirmed that `capability_authority()` is a pure stored-config
reader/validator with no authentication, writes, enqueue, registry load, or
NoDb mutation. `locales/__init__.py` is import/export wiring only. The
preexisting pure named-preset snapshot helper was not broadened by WP12C.

Validation at the accepted candidate includes 182 focused Python tests,
resolver stubtest, 107 frontend suites / 794 tests, frontend lint, and cumulative
diff checks. The final repository-wide gate passed 7,080 tests with 63 skipped.

## Verdict

- **Contract gate status**: pass
- **Implementation gate status**: pass at exact candidate `b31eeb625`
- **Unresolved contract findings**: High 0; Medium 0; Low 0
- **Unresolved implementation findings**: High 0; Medium 0; Low 0
- **Release recommendation**: Ready for exact-revision, writer-disabled,
  reader-first Forest deployment; creation remains gated on the required
  historical-v2, five-profile-v3, provider, and rollback-floor evidence
