# Project Config Preset Snapshot (WP04)

**Status**: Complete (2026-08-26)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate

## Overview

WP04 adds the first default-off project-owned configuration writer to the
existing synchronous Interfaces creation boundary. When explicitly enabled,
named-preset creation resolves shared defaults plus the requested preset,
normalizes only declared query overrides, writes canonical `<preset>.cfg` and
`config-manifest.json` before Ron initialization, and protects submission with
a 24-hour Redis idempotency reservation. With the flag disabled, legacy
creation behavior remains byte-for-byte and route-token compatible.

## Objectives

- Snapshot every supported shared preset under its original basename/token.
- Generate manifest schema v1 with immutable defaults/preset provenance.
- Materialize only explicit, typed, per-preset allowlisted query overrides.
- Atomically persist both files and clean incomplete initialization safely.
- Add scoped 24-hour create/replay/conflict/in-progress idempotency.
- Keep the writer default-off and preserve all current Interfaces links.

## Scope

### Included

- A preset-policy registry, typed snapshot resolver, manifest builder, and
  atomic initial materializer.
- Default-off integration with rq-engine `/create/` and `/api/create/`.
- Existing creation authorization/CAPTCHA/ownership and synchronous redirect
  semantics.
- Generated project-pair, hostile input, all-preset, replay, conflict,
  concurrency, failure, cleanup, and security evidence.

### Explicitly Out of Scope

- Builder creation and privileged cell-size authorization (WP06).
- Runtime capability enforcement (WP05).
- Additive amendment/update transactions (WP08).
- Fork/archive/restore consistency (WP10).
- Forest activation and writer enablement (WP11/WP12).

## Owned Requirements

- PC-09: N-023 through N-027; R-011 through R-014; R-031; R-035.
- PC-10: N-055 through N-057; N-081 through N-083; R-046; R-052.
- Contributions: PC-01 real preset creation, PC-04 sanitizer invocation,
  PC-05 canonical bytes, PC-06 provenance, and PC-08 manifest writing.

## Compatibility and Regression Plan

This package creates new run-scoped files but does not rename/remove existing
keys, presets, route tokens, payload aliases, or NoDb schemas. The writer flag
is absent/false by default; that path continues passing `<preset>.cfg?<legacy
overrides>` directly to Ron. The enabled path uses the same preset basename,
normalizes only its declared durable query keys, creates a complete typed map
from canonical defaults and preset sources, and initializes Ron with the stable
basename after the project-local pair is durable.

Generated-output validation will inspect a temporary run directory before and
after creation, parse the actual `.cfg` through the WP02 reader, verify the
manifest digest/chain/overrides, prove the shared source can change or vanish
without changing the snapshot, and scan both artifacts through WP00A. Failure
fixtures cover each pre-write/write/Ron/ownership boundary and assert no ready
project or unexpected survivor. Existing Interfaces rendering and unflagged
rq-engine tests remain mandatory regression gates.

## Success Criteria

- [x] Every shipped named preset has an explicit policy and resolves canonically.
- [x] Enabled creation writes the complete safe pair before Ron begins.
- [x] Replays return the original redirect; conflicts/in-progress return 409.
- [x] Failed initialization releases reservation and cleans the new directory.
- [x] Disabled creation and Interfaces links/tokens remain unchanged.
- [x] Focused, microservice, NoDb, full-suite, stub, docs, correctness, and security gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes
- **Rationale**: WP04 snapshots existing canonical effective values and
  ratified creation overrides; it changes no default, formula, threshold,
  conversion, or fallback heuristic.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Primary assets**: run ownership/readiness, credentials, preset paths,
  idempotency records, canonical config and manifest integrity.

## Dependencies and Handoff

- **Depends on**: WP00R, WP00A, WP00B, WP02, and WP03; all closed on this branch.
- **Blocks**: WP05, WP06, WP08, WP10, and WP11.
- **Rollback**: leave the writer flag disabled or revert the dormant writer;
  no legacy project migration/backfill is introduced.

## References

- `docs/schemas/project-owned-config-contract.md` sections 5, 7.1, 7.6, 10,
  11, and 14.5.
- `docs/schemas/project-owned-config-implementation-roadmap.md` WP04.
- `docs/work-packages/20260804_project_config_contract_ratification/artifacts/normative_requirement_checklist.md`.
