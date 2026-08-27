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
- **Commit/branch context**: contract checkpoint pending

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

## Verdict

- **Contract gate status**: pass
- **Implementation gate status**: pending implementation re-review
- **Unresolved contract findings**: High 0; Medium 0; Low 0
- **Release recommendation**: hold until implementation review and acceptance
