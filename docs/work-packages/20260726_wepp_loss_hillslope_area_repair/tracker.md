# Tracker - WEPP LOSS Annual Hillslope-Area Repair

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-27 04:19 UTC
**Current phase**: Closed
**Last updated**: 2026-07-27
**Next milestone**: Production deployment, failed-job retry, and observation
**Security impact**: `low`
**Dedicated security review**: `no`

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Confirmed the production row and release identity (2026-07-27 04:19 UTC).
- [x] Scaffolded the package, compatibility plan, and active ExecPlan
  (2026-07-27 04:19 UTC).
- [x] Implemented strict uniform legacy/current layout handling and true-null
  legacy area output (2026-07-27).
- [x] Built and validated the canonical py312 release artifact
  (2026-07-27).
- [x] Audited consumers and passed Rust, native-writer, interchange, reporting,
  export, and dashboard gates (2026-07-27).
- [x] Completed dual review and dispositioned every finding (2026-07-27).
- [x] Pushed WEPPpyo3 commits `fc3e361` and `cee6ff1` to `origin/main`
  (2026-07-27).

## Decisions

- **2026-07-27 04:19 UTC** - Treat `Hillslope Area` as an additive annual
  parquet field because production rows emit it and the average schema already
  establishes its name, unit, and semantic position.
- **2026-07-27 04:19 UTC** - Preserve exact column-count validation; this is a
  schema correction, not a permissive parser fallback.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| Pollutant values shift into the wrong columns | High | Exact value and schema-order assertions | Closed |
| Positional WEPPpy consumer breaks | High | Repository-wide consumer audit and generated-output tests | Closed |
| Release source and binary diverge | High | Build provenance, SHA256, clean-tree verification | Closed |
| Legacy 11-field annual files need compatibility | Medium | Uniform-layout normalization and regressions | Closed |

## Verification Checklist

- [x] `cargo fmt --check` passes.
- [x] `cargo test -p wepp_interchange_rust` passes.
- [x] Rebuilt py312 release imports and converts the incident fixture.
- [x] Relevant WEPPpy consumer tests pass.
- [x] WEPPpy documentation lint passes.
- [x] Code review has no unresolved findings.
- [x] QA review has no unresolved findings.
- [x] WEPPpyo3 commits are pushed to `origin/main`.

## Handoffs

- Production deployment and failed-job retry are not part of this package.
