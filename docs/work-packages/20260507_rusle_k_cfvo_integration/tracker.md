# Tracker - RUSLE K CFVO Profile-Fragment Adjustment Integration

## Quick Status

**Timezone**: UTC
**Started**: 2026-05-07
**Current phase**: Closed
**Last updated**: 2026-05-07
**Security impact**: `none`
**Dedicated security review**: `no`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Done
- [x] Package scaffold + active ExecPlan created.
- [x] Implemented `cfvo` runtime path and manifest contract.
- [x] Added/adjusted regression tests.
- [x] Updated RUSLE specification + README.
- [x] Ran validation gates (`targeted` and `broad`).
- [x] Dispatched code/QA review and dispositioned all high/medium findings.
- [x] Closed package docs and archived ExecPlan.

## Validation Log

- `wctl run-pytest tests/nodb/mods/test_rusle_k_integration.py --maxfail=1`:
  `10 passed`.
- `wctl run-pytest tests/nodb/mods/test_rusle_k_nomograph.py tests/nodb/mods/test_rusle_k_epic.py tests/nodb/mods/test_rusle_k_compare.py tests/nodb/mods/test_rusle_k_reference_harness.py tests/nodb/mods/test_rusle_k_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`:
  `31 passed`.
- `wctl run-pytest tests --maxfail=1`: stopped on unrelated baseline failure in
  `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_mtime_advance_on_unchanged_signature_then_rejects_stale_writer`.
- `wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md --path wepppy/nodb/mods/rusle/README.md --path docs/work-packages/20260507_rusle_k_cfvo_integration`:
  `5 files validated, 0 errors, 0 warnings`.

## Decisions Log

### 2026-05-07: Keep `cfvo` optional at runtime, explicit in metadata
**Decision**: Ship `cfvo` as an optional ancillary adjustment path that applies only when required layers are present.

**Rationale**: Preserves deterministic no-`cfvo` behavior while closing the deferred implementation gap with explicit auditable contracts.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Misinterpreting SoilGrids `cfvo` units | High | Apply documented conversion policy and record normalization metadata | Mitigated |
| Over-adjustment of `K` in rocky domains | Medium | Use conservative class-step policy and clamp bounds | Mitigated |
| Behavior drift for runs without `cfvo` | Medium | Keep no-`cfvo` path unchanged and add regression assertions | Mitigated |
