# WP-02 Evidence: Rust HRU + HSG Kernel (`prepare_hrus`)
Status: in_review  
Last Updated: 2026-04-14  
Work-Package: `WP-02`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior package evidence: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-01_wepppyo3_geneva_kernel_scaffold.md`

## 1. Scope Implemented
- Implemented `geneva_prepare_hrus(...)` Rust kernel path in `/workdir/wepppyo3/geneva_core/src/hru.rs`:
  - canonical-grid alignment against `bound.tif` with nearest-neighbor resample path and alignment diagnostics,
  - deterministic HRU key derivation (`landuse`, `hsg`, `burn_severity`, `hydrophobic`) using connected-component HRU assembly,
  - HSG mapping + fallback precedence (`coded_lookup -> default_hsg_code -> unresolved policy`) with provenance counters and warning codes,
  - deterministic minimum-HRU collapse pass using required recipient ordering,
  - water-HRU protection and area-closure enforcement.
- Added typed request/response contracts for `prepare_hrus` with structured diagnostics/warnings in Rust.
- Kept PyO3 adapter thin:
  - `cli_revision/src/geneva/mod.rs` now parses payload, calls kernel, and serializes response only,
  - no algorithm body changes in `cli_revision/src/lib.rs`.

## 2. Code Changes
### Repo: `/workdir/wepppyo3`
- `geneva_core/Cargo.toml`
- `geneva_core/src/error.rs`
- `geneva_core/src/hru.rs`
- `cli_revision/src/geneva/convert.rs`
- `cli_revision/src/geneva/mod.rs`

### Repo: `/workdir/wepppy`
- `wepppy/nodb/mods/geneva/work-packages/wp-02_rust_hru_hsg_kernel_prepare_hrus.md`
- `wepppy/nodb/mods/geneva/implementation-plan.md`

## 3. Tests Added/Extended
Added/extended unit coverage in `geneva_core/src/hru.rs` and `cli_revision/src/geneva/*` for:
- deterministic HRU keying,
- fallback precedence (`coded_lookup`, `default_hsg_code`, `assume_d`, and unresolved-error path),
- deterministic collapse + area conservation,
- water-HRU protection,
- default-collapse sensitivity (`allow_cross_hsg_merge=false`) versus no-collapse references with threshold assertions:
  - runoff depth delta `<= 2%`,
  - runoff volume delta `<= 2%`,
  - peak discharge delta `<= 5%`.

## 4. Required Gates
### 4.1 Kernel repo gates (`/workdir/wepppyo3`)
1. `cd /workdir/wepppyo3 && cargo fmt --check`
   - Result: **pass**
2. `cd /workdir/wepppyo3 && cargo clippy --all-targets -- -D warnings`
   - Result: **pass**
3. `cd /workdir/wepppyo3 && cargo test -p geneva_core`
   - Result: **pass** (`11 passed; 0 failed`)
4. `cd /workdir/wepppyo3 && cargo test -p cli_revision_rust --lib`
   - Result: **pass** (`10 passed; 0 failed`)

### 4.2 Core repo gates (`/workdir/wepppy`)
5. `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`
   - Result: **pass** (`8 files validated, 0 errors, 0 warnings`)
6. `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
   - Result: **fail** (changed-file baseline includes unrelated pre-existing broad-catch deltas in `wepppy/microservices/rq_engine/bootstrap_routes.py`)
   - Note: no WP-02 files are part of that failure set.

## 5. Manual Integration Check
Required fixture:
- `/workdir/wepppy/tests/data/geneva/synthetic_small_watershed_v1`

Commands executed:
- `cd /workdir/wepppyo3 && cargo build -p cli_revision_rust --release --features extension-module`
- Python import via `/workdir/wepppyo3/target/release/libcli_revision_rust.so`
- `geneva_prepare_hrus(...)` called twice with identical payload (bound/landuse/hydgrpdcd/burn fixture paths).

Observed results:
- `hru_row_count = 12`
- deterministic output ordering across repeated runs: `True`
- response contains `hru_rows` and `diagnostics.hsg_provenance_counts`
- warning/reason-code surfaced:
  - `code = collapse_no_compatible_recipient`
  - reason text present and non-empty

## 6. QA Review
Checklist outcomes:
- Pass: algorithm logic resides in `geneva_core/src/hru.rs`; adapter remains boundary-only.
- Pass: deterministic ordering verified by repeated manual integration calls and deterministic-unit tests.
- Pass: collapse selection tie-break order and area conservation tested.

## 7. Security Review
Checklist outcomes:
- Pass: invalid/unknown `hydgrpdcd` values produce explicit diagnostics/warnings and fallback behavior.
- Pass: malformed payloads reject with typed errors (`invalid_json`/`invalid_input`).
- Pass: alignment/dimension mismatches fail fast with typed alignment/contract errors.
- Gate note: broad-exception changed-file enforcement command failed due unrelated dirty baseline outside Geneva scope (see Section 4.2).

## 8. Findings and Disposition
- Finding ID: `WP02-GATE-BROAD-EXCEPTION-BASELINE`
  - Severity: medium
  - Disposition: blocked_external
  - Detail: required changed-file broad-exception gate currently fails due unrelated pre-existing changes in non-Geneva Python files (`rq_engine`), preventing all-gates-pass closure semantics for WP-02 in this workspace state.

## 9. Exit Criteria Check
- [x] Scope completed.
- [x] Required tests added and passing.
- [ ] All required gates passing.
- [x] Manual integration check passing.
- [x] QA checklist pass.
- [x] Security checklist pass (with external changed-file gate blocker documented).
- [x] WP-02 board row updated with final gate states and evidence link.
