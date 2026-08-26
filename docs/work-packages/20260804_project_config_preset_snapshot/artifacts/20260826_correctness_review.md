# Correctness and User-Experience Review - Project Config Preset Snapshot

## Metadata

- **Package**: `docs/work-packages/20260804_project_config_preset_snapshot/`
- **Reviewer**: Codex, separate static-review pass
- **Date**: 2026-08-26
- **Scope reviewed**: preset resolver/materializer, idempotency service, create route, and Interfaces forms
- **Commit/branch context**: `feature/project-owned-config`, starting at `95a8c4394`
- **Canonical contract(s)**: `docs/schemas/project-owned-config-contract.md` sections 7.1, 7.6, 10, 11, and 14.5
- **Related artifacts**: `artifacts/20260826_preset_snapshot_evidence.md`; `artifacts/20260826_security_review.md`

## User Outcome

- **User goal**: create a named-preset project once and reopen the exact resolved configuration later.
- **Success presented to the user as**: the existing 303 redirect and unchanged preset route token.
- **Failures that may reach the user**: explicit 400 validation, 409 conflict/in-progress, 503 Redis availability, or initialization/materialization errors.
- **Partial-state behavior**: failed post-allocation initialization removes the scoped new run and releases its owned reservation.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Writer flag absent/false | yes | exact legacy creation path | existing route suite |
| No prior idempotency record | yes | reserve and create once | idempotency/route tests |
| Matching completed record | yes | replay original redirect | route replay test |
| Matching active record | yes | 409 plus Retry-After | idempotency state test |
| Existing project artifacts | no for initial writer | refuse overwrite | materializer test |
| Hostile/unknown override | no | 400 before allocation | snapshot hostile-input tests |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Missing/invalid client key | expected | 400 validation | bounded idempotency contract |
| Same key, different fingerprint | expected | canonical 409 conflict | prevents ambiguous duplicate creation |
| Same key still active | expected | canonical 409, retry after 2 seconds | bounded concurrent submission |
| Redis unavailable | exceptional | canonical 503 | cannot safely promise once-only creation |
| Pair/Ron/owner initialization fails | exceptional | explicit failure, cleanup, retry permitted | readiness is published only after initialization |

## Review Checks

- [x] Canonical intent is named and governs implementation.
- [x] Absent, populated, legacy, and hostile states are covered.
- [x] Request combinations and stored/filesystem states were reviewed separately.
- [x] Direct tests exercise real parser, serializer, sanitizer, filesystem, and WP02 reader boundaries.
- [x] Partial success, readiness, retry, and cleanup semantics are explicit.
- [x] Existing workflow remains unchanged while the writer is disabled.
- [x] All-preset claims are limited to 128 shipped non-default preset files and their runtime schema/override policy.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | materialization failure | Materializer and Ron failures initially shared an inaccurate initialization error. | route static review | split the materialization boundary and canonical error | Resolved |
| COR-02 | Medium | capabilities | A single continental-US capability profile would be incorrect for several shipped international presets. | preset corpus and WP03 profile constraint | leave stable capability population/enforcement to WP05; do not infer | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship dormant/default-off WP04; activation remains WP11/WP12 scope
- **Reviewer sign-off**: Codex, 2026-08-26
