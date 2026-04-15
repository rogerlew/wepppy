# WP-04 Evidence: Frequency Panel + NEH4 Type B Kernel
Status: done  
Last Updated: 2026-04-15  
Work-Package: `WP-04`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-03_rust_cn_rainfall_excess_kernel.md`

## 1. Scope Implemented
Implemented the WP-04 kernel and adapter scope in `/workdir/wepppyo3`:
- Replaced frequency-panel stub with typed request/response contracts in `geneva_core/src/frequency_panel.rs`:
  - requested-vs-available matrix materialization for `cligen_freq` (required) and `noaa14_pds` (optional),
  - canonical unavailable reason codes (`duration_unavailable`, `ari_unavailable`, `source_missing`),
  - no synthetic duration interpolation (`allow_duration_interpolation=true` is rejected),
  - deterministic ordering (`datasource_id`, `duration_minutes`, `ari_years`, `storm_id`),
  - explicit path validation for source references (reject parent-dir traversal / malformed mappings).
- Replaced NEH4 Type B hyetograph stub with full kernel in `geneva_core/src/hyetograph.rs`:
  - pinned Type B ordinates and duplicate-`t*=0`-safe interpolation,
  - timestep arrays (`cumulative_rainfall_mm`, `incremental_rainfall_mm`, `intensity_mm_per_hr`),
  - monotonic cumulative enforcement and closure guarantees,
  - required short-duration warning (`type_b_short_duration_extrapolation` for `<30 min`),
  - typed validation for invalid duration/depth/timestep and malformed ordinate CSV input/path.
- Kept adapter thin:
  - `cli_revision/src/geneva/mod.rs` now parses payload, invokes kernel, serializes response for `geneva_build_frequency_panel(...)`.
  - no algorithm body added to `cli_revision/src/lib.rs`.

## 2. Code Changes
### Repo: `/workdir/wepppyo3`
- `geneva_core/src/frequency_panel.rs`
- `geneva_core/src/hyetograph.rs`
- `cli_revision/src/geneva/convert.rs`
- `cli_revision/src/geneva/mod.rs`

### Repo: `/workdir/wepppy`
- `wepppy/nodb/mods/geneva/work-packages/wp-04_frequency_panel_neh4_type_b_kernel.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

## 3. Tests Added/Extended
Added and/or extended coverage for WP-04 acceptance behavior:
- Frequency panel matrix tests:
  - CLIGEN-only path marks NOAA cells as `source_missing` when NOAA artifact is absent,
  - dual-source path materializes each datasource independently,
  - no synthetic fill for missing requested durations,
  - schema invariants (`available -> reason_code=null`, unavailable reason-code enum constraint),
  - deterministic ordering and repeated-run byte-stable payload equivalence.
- NEH4 Type B hyetograph tests:
  - breakpoint parity against pinned Type B ordinates (0.1% relative tolerance),
  - duplicate-`t*=0` interpolation behavior,
  - monotonicity and closure checks,
  - short-duration warning behavior,
  - invalid input handling for non-positive values and malformed/missing ordinate CSV path.
- Adapter boundary tests:
  - `geneva_build_frequency_panel(...)` returns typed `ok` payload with canonical IDs,
  - malformed source mapping and invalid payload paths return typed input/json errors.

## 4. Required Gates
### 4.1 Kernel repo gates (`/workdir/wepppyo3`)
1. `cd /workdir/wepppyo3 && cargo fmt --check`
   - Result: **pass**
2. `cd /workdir/wepppyo3 && cargo clippy --all-targets -- -D warnings`
   - Result: **pass**
3. `cd /workdir/wepppyo3 && cargo test -p geneva_core`
   - Result: **pass** (`43 passed; 0 failed`)
4. `cd /workdir/wepppyo3 && cargo test -p cli_revision_rust --lib`
   - Result: **pass** (`18 passed; 0 failed`)

### 4.2 Core repo gates (`/workdir/wepppy`)
5. `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`
   - Result: **pass** (`10 files validated, 0 errors, 0 warnings`)
6. `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
   - Result: **pass** (`Result: PASS`)

## 5. Manual Integration Protocol Evidence
Adapter-path panel scenarios and kernel-harness hyetograph checks executed.

### 5.1 Adapter path: CLIGEN-only + NOAA-missing scenario
- Built release extension:
  - `cd /workdir/wepppyo3 && cargo build -p cli_revision_rust --release --features extension-module`
- Called `geneva_build_frequency_panel(...)` with CLIGEN source present and NOAA path absent.
- Observed:
  - `status = ok`
  - `cligen_available = 3`
  - `noaa_source_missing = 9`
  - `datasource_ids = ["cligen_freq", "noaa14_pds"]`

### 5.2 Adapter path: dual-source scenario
- Called `geneva_build_frequency_panel(...)` with both CLIGEN and NOAA artifacts present.
- Observed:
  - `status = ok`
  - `cligen_available = 3`
  - `noaa_available = 6`
  - `noaa_duration_unavailable = 3`
  - unavailable `reason_code` set constrained to canonical enum (`duration_unavailable` in this scenario)
  - deterministic repeated-run equivalence: `True`

### 5.3 Kernel harness: NEH4 Type B checks
Executed targeted kernel tests as manual harness checks:
- `cd /workdir/wepppyo3 && cargo test -p geneva_core hyetograph::tests::generated_hyetograph_is_monotonic_and_closes -- --exact`
  - Result: **pass** (cumulative monotonicity, incremental non-negativity, endpoint/closure assertions)
- `cd /workdir/wepppyo3 && cargo test -p geneva_core hyetograph::tests::short_duration_emits_required_warning -- --exact`
  - Result: **pass** (`type_b_short_duration_extrapolation` asserted)

## 6. Review Workflow
### 6.1 Code Review (`reviewer` pass, manual)
Checklist outcomes:
- Pass: frequency-panel and Type B algorithm bodies reside in `geneva_core`.
- Pass: adapter remains boundary-only parse/execute/serialize path.
- Pass: deterministic ordering and reason-code invariants verified in tests.

### 6.2 QA Review (`qa_reviewer` pass, manual)
Checklist outcomes:
- Pass: no synthetic duration interpolation in matrix materialization.
- Pass: parity/closure tolerances anchored to spec thresholds.
- Pass: repeated-run determinism validated at adapter-path level.

### 6.3 Security Review (`security_reviewer` pass, manual)
Checklist outcomes:
- Pass: malformed source mapping and malformed/missing ordinate CSV path return typed errors.
- Pass: source/ordinate path traversal segments (`..`) are rejected.
- Pass: input dimension guards (`matrix size`, `timestep count`) prevent unbounded workload.
- Pass: no panic-based control flow introduced in user-input paths.

Open findings:
- None.

## 7. Findings and Disposition
- Finding ID: `WP04-CODE-CLIPPY-MANUAL-CONTAINS`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: replaced `iter().any(|x| x == 0)` with `contains(&0)` to satisfy `-D warnings` clippy gate.
- Finding ID: `WP04-SEC-SOURCE-PATH-TRAVERSAL`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: added explicit source and ordinate path validation rejecting parent-directory traversal and malformed path inputs.
- Finding ID: `WP04-QA-DETERMINISM-EVIDENCE`
  - Severity: low
  - Disposition: resolved_fix_now
  - Action/Notes: added deterministic repeated-run adapter integration assertion and kernel ordering tests.
- Finding ID: `WP04-GATE-BROAD-EXCEPTION-BASELINE`
  - Severity: medium
  - Disposition: resolved_fix_now
  - Action/Notes: after follow-up cleanup of the unrelated changed-file baseline, `check_broad_exceptions --enforce-changed` now passes for the WP-04 validation window.

## 8. Exit-Criteria Check
- [x] Frequency panel matrix implementation complete for CLIGEN required + NOAA optional behavior.
- [x] NEH4 Type B scaling/interpolation complete with closure and monotonic guarantees.
- [x] Required tests added/updated and passing with tolerance evidence.
- [x] Required gates all passing.
- [x] Manual integration evidence captured.
- [x] Code/QA/security reviews completed and findings dispositioned.
- [x] Board row updated to `done` with evidence link.
