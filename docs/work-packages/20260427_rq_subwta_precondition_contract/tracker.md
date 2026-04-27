# Tracker - RQ WEPP Subwta Precondition Contract Enforcement

> Living document tracking progress, decisions, risks, and validation for strict watershed abstraction-state enforcement on WEPP run endpoints.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-27 20:20 UTC
**Current phase**: Discovery
**Last updated**: 2026-04-27 20:20 UTC
**Next milestone**: Implement strict pre-enqueue `subwta` enforcement and update contract docs/tests
**Security impact**: `low`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Add strict abstraction-state gate for `run-wepp` and `run-wepp-watershed` before batch/base short-circuit logic.
- [ ] Define/lock `checkbox_wepp_watershed` behavior so it cannot bypass strict `subwta` requirement.
- [ ] Update canonical contract docs and schema-defaults metadata for strict enforcement language.
- [ ] Extend route + schema-default regression tests for strict precondition cases.

### In Progress
- [ ] Package scaffold and initial decision capture.

### Blocked
- None.

### Done
- [x] Package scaffold created (`package.md`, `tracker.md`, active ExecPlan path) (2026-04-27 20:20 UTC).
- [x] User decision recorded: `watershed.subwta` is always required because removed `subwta.tif` invalidates hillslope/watershed integrity (2026-04-27 20:20 UTC).

## Timeline

- **2026-04-27 20:20 UTC** - Package created from deferred review findings.
- **2026-04-27 20:20 UTC** - Strict contract decision captured from user directive.

## Decisions Log

### 2026-04-27 20:20 UTC: `watershed.subwta` is always required on WEPP run endpoints
**Context**: Deferred review findings identified ambiguity around batch/base exceptions and `checkbox_wepp_watershed=false` behavior.

**Options considered**:
1. Require `subwta` only when watershed routine is enabled.
2. Require `subwta` for all `run-wepp` and `run-wepp-watershed` requests.

**Decision**: Option 2.

**Impact**: Endpoint contract is strict; no batch/base or checkbox path can bypass `subwta` precondition.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Strict precondition causes behavior change for existing batch/base workflows | Medium | Medium | Add focused regression tests and explicit contract docs to prevent silent drift | Open |
| Contract/docs mismatch reappears between runtime and schema defaults | Medium | Medium | Update `rq-response-contract.md` and schema-default tests in same change | Open |

## Verification Checklist

### Code Quality
- [ ] `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- [ ] `git diff --check`

### Documentation
- [ ] `wctl doc-lint --path docs/schemas/rq-response-contract.md --path docs/work-packages/20260427_rq_subwta_precondition_contract --path PROJECT_TRACKER.md`

### Testing
- [ ] Route tests cover strict enforcement in batch/base and checkbox-toggled payload cases.
- [ ] Schema-default tests assert strict error metadata/recovery for both run endpoints.

## Progress Notes

### 2026-04-27 20:20 UTC: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Created package and tracker scaffolding.
- Recorded strict contract decision from user directive.

**Next steps**:
1. Implement strict gate ordering in `wepp_routes.py`.
2. Update contract docs and schema-default metadata.
3. Add/adjust targeted route/schema tests and run required gates.
