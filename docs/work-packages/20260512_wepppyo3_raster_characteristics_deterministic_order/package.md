# Deterministic Return Ordering for wepppyo3 Raster Characteristics APIs

**Status**: Completed (2026-05-13)
**Timezone**: UTC

## Overview
`wepppyo3.raster_characteristics` currently returns Python mappings from Rust `HashMap`-backed outputs in multiple public APIs. This can produce run-to-run key order differences even when values are identical, which creates nondeterministic behavior in downstream iteration, noisy diagnostics, and unstable regression artifacts. This package standardizes deterministic ordering for all public `raster_characteristics` return maps while preserving existing value semantics and failure contracts.

## Objectives
- Make all public `wepppyo3.raster_characteristics` map-returning functions produce deterministic key order.
- Preserve existing computational semantics (mode/median/count values) and existing error contracts.
- Add regression tests in `wepppyo3` that prove deterministic ordering and value parity.
- Add/adjust WEPPpy-side targeted tests where ordering assumptions are consumed or validated.
- Refresh and validate canonical release exports used by WEPPpy runtime paths.
- Complete mandatory independent code review with findings disposition and no unresolved high/medium findings.
- Update `wepppyo3` docs to capture the deterministic-order contract and release-refresh evidence.

## Scope
This package is limited to deterministic return ordering in the `wepppyo3.raster_characteristics` API surface and related regression coverage.

### Included
- Audit of all public functions exported by `wepppyo3.raster_characteristics` for ordering behavior.
- Rust/PyO3 return-type and container updates required for deterministic ordering.
- Targeted tests in `wepppyo3/tests/raster_characteristics` for deterministic order and semantic parity.
- Targeted WEPPpy regression checks for call sites that iterate these mappings.
- Targeted release refresh for `release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so` plus runtime import verification from the release tree.
- Required independent code review and findings disposition artifact.
- `wepppyo3` documentation updates (`README.md`, `docs/module-registry.md`, `docs/release-provenance.md`) describing deterministic ordering guarantees and release-refresh evidence.
- Package lifecycle updates (`tracker.md`, active/completed prompt lifecycle, `PROJECT_TRACKER.md`).

### Explicitly Out of Scope
- New raster-statistics features or API additions beyond deterministic ordering.
- Algorithmic performance redesign unrelated to ordering determinism.
- Broad refactors in WEPPpy call sites beyond what is necessary for deterministic-order compatibility and tests.
- Non-`raster_characteristics` modules in `wepppyo3`.

## Implementation Fidelity and Evidence (Required for modernization/migrations)
- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**: `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs`, `/home/workdir/wepppyo3/release/linux/py312/wepppyo3/raster_characteristics/__init__.py`
- **Cutover proof required**: deterministic return order verified at the shipped Python API boundary on repeated calls over fixed fixtures.
- **Acceptance evidence type**: `both`

## Stakeholders
- **Primary**: WEPPpy/WEPPcloud maintainers operating disturbed, soils, RAP, and Omni flows.
- **Reviewers**: wepppyo3 maintainers; WEPPpy NoDb maintainers for impacted call sites.
- **Security Reviewer**: not required for planned scope.
- **Informed**: runtime triage contributors investigating nondeterministic behavior.

## Success Criteria
- [x] Every public map-returning function in `wepppyo3.raster_characteristics` returns deterministic key order.
- [x] Determinism is validated by repeated-call tests against fixed fixtures.
- [x] Value outputs (mode/median/count) match pre-change semantics on fixture/parity checks.
- [x] Targeted wepppyo3 and WEPPpy tests pass.
- [x] Release `raster_characteristics_rust.so` is rebuilt/copied into `release/linux/py312` and verified via Python import from release tree.
- [x] `wepppyo3` docs are updated to reflect deterministic-order contract and release refresh provenance.
- [x] Mandatory code review/disposition is complete with no unresolved high/medium findings.
- [x] Package docs and tracker lifecycle are updated and complete.

## Required Validation and Closure Gates

### Phase 1: Determinism and Parity Test Execution (Required)
Run and capture outcomes for:
- `cd /home/workdir/wepppyo3 && pytest tests/raster_characteristics -q`
- `cd /home/workdir/wepppyo3 && cargo test -p raster_characteristics_rust`
- `cd /workdir/wepppy && wctl run-pytest tests/nodb/test_landuse_coverage_area_source.py tests/soils/test_wepppyo3_nodata_guard.py --maxfail=1`

### Phase 2: Release Build and Runtime Verification (Required)
Run and capture outcomes for:
- `cd /home/workdir/wepppyo3 && export PYO3_PYTHON=/usr/bin/python3.12 && export PYTHON_SYS_EXECUTABLE=$PYO3_PYTHON && cargo build -p raster_characteristics_rust --release`
- `cd /home/workdir/wepppyo3 && cp target/release/libraster_characteristics_rust.so release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so`
- `cd /home/workdir/wepppyo3 && PYTHONPATH=/home/workdir/wepppyo3/release/linux/py312 python3.12 -c "from wepppyo3.raster_characteristics import raster_characteristics_rust as rc; print(rc.__file__)"`
- `cd /home/workdir/wepppyo3 && sha256sum release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so`

### Phase 3: Code Review and Disposition (Required)
- Perform independent correctness-focused code review of implementation, tests, and docs.
- Disposition findings by severity (`fixed`, `accepted-risk`, `deferred` with rationale).
- Closure gate: no unresolved high/medium findings.
- Record review artifact under package `artifacts/`.

### Phase 4: wepppyo3 Documentation Update (Required)
- Update `/home/workdir/wepppyo3/README.md` for deterministic-order behavior in `raster_characteristics`.
- Update `/home/workdir/wepppyo3/docs/module-registry.md` evidence notes for deterministic-order contract hardening.
- Update `/home/workdir/wepppyo3/docs/release-provenance.md` with this package's release refresh command/evidence.
- Validate doc edits with `git diff --check` and relative-link checks in `wepppyo3`.

## Dependencies

### Prerequisites
- Access to `/home/workdir/wepppyo3` and `/workdir/wepppy` workspaces.
- Existing raster fixture coverage in `wepppyo3/tests/raster_characteristics`.

### Blocks
- Follow-on hardening packages that depend on stable deterministic traversal/report artifacts from raster characteristics results.

## Related Packages
- **Depends on**: none.
- **Related**:
  - [20260423_mofe_landuse_pair_counts_wepppyo3](../20260423_mofe_landuse_pair_counts_wepppyo3/package.md)
  - [20260428_wepppyo3_repositioning](../20260428_wepppyo3_repositioning/package.md)
- **Follow-up**: optional broader benchmark matrix for deterministic-order overhead characterization.

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium (cross-repo behavior contract sensitivity).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: deterministic ordering hardening only; no auth/session/secrets/public route attack-surface change.
- **Security review artifact**: `N/A`

## References
- `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs` - Rust/PyO3 implementation of raster-characteristics APIs.
- `/home/workdir/wepppyo3/release/linux/py312/wepppyo3/raster_characteristics/__init__.py` - shipped Python wrappers.
- `/home/workdir/wepppyo3/README.md` - canonical build/release/import workflow for py312 package tree.
- `/home/workdir/wepppyo3/docs/module-registry.md` - module evidence and maturity registry.
- `/home/workdir/wepppyo3/docs/release-provenance.md` - release refresh and provenance contract.
- `wepppy/nodb/core/landuse.py` - high-impact consumer (`identify_mode_*`, `count_intersecting_raster_key_pairs`).
- `wepppy/nodb/core/soils.py` - consumer (`identify_mode_*`).
- `wepppy/nodb/mods/rap/rap.py` and `wepppy/nodb/mods/rap/rap_ts.py` - consumer (`identify_median_*`).

## Deliverables
- Updated `wepppyo3.raster_characteristics` implementation and exports with deterministic ordering guarantees.
- Added/updated tests proving deterministic ordering and semantic parity.
- Refreshed `release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so` with import and hash evidence captured in artifacts.
- `wepppyo3` docs updates (`README.md`, `docs/module-registry.md`, `docs/release-provenance.md`) for deterministic-order contract + provenance notes.
- Independent code review artifact with findings disposition and closure state.
- Validation notes and command transcripts in package artifacts.
- Updated package lifecycle documents and tracker entries.

## Follow-up Work
- Optional: broaden deterministic-order contract tests to additional downstream workflows if needed.
