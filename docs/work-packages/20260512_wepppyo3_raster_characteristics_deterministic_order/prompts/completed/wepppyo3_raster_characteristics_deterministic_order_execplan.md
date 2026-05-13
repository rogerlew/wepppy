# Deterministic Return Ordering for wepppyo3 Raster Characteristics APIs

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, every public map-returning function in `wepppyo3.raster_characteristics` produces deterministic key order for identical inputs, across repeated calls and process invocations. Users can verify this by running repeated-call tests that assert stable ordered key sequences while preserving the same numerical outputs (mode/median/count values) as before.

## Progress

- [x] (2026-05-13 03:18 UTC) Created work package scaffold and active ExecPlan.
- [x] (2026-05-13 03:31 UTC) Baseline current ordering behavior for each public API function.
- [x] (2026-05-13 03:32 UTC) Implement deterministic ordering changes in Rust/PyO3 return paths.
- [x] (2026-05-13 03:34 UTC) Add wepppyo3 deterministic-order + semantic-parity regression tests.
- [x] (2026-05-13 03:37 UTC) Add/adjust WEPPpy targeted tests for ordering-sensitive consumers (targeted consumer suites validated; no WEPPpy test edits required).
- [x] (2026-05-13 03:32 UTC) Refresh `release/linux/py312` raster-characteristics shared object and verify import/runtime behavior from release tree.
- [x] (2026-05-13 03:39 UTC) Update `wepppyo3` docs (`README.md`, `docs/module-registry.md`, `docs/release-provenance.md`) for deterministic-order + release-refresh evidence.
- [x] (2026-05-13 04:13 UTC) Complete mandatory independent code review and findings disposition with no unresolved high/medium findings.
- [x] (2026-05-13 03:42 UTC) Run targeted validation in both repos and capture evidence.
- [x] (2026-05-13 04:16 UTC) Update package closure docs and archive prompt.

## Surprises & Discoveries

- Observation: Prior to hardening, four of five public map-returning APIs exhibited nondeterministic key order across repeated calls because `HashMap`/`HashSet` traversal order fed Python dict insertion.
  Evidence: repeated-call probe (40 runs per API) observed `outer_order_variants=6` for `identify_*` APIs and inner-order variants for nested maps.
- Observation: The local Python import path resolves to the canonical release tree (`release/linux/py312`), so release artifact refresh is required before pytest can validate Rust implementation changes.
  Evidence: `python3.12 -c "import wepppyo3.raster_characteristics.raster_characteristics_rust as rc; print(rc.__file__)"` resolved to release-tree `.so`.

## Decision Log

- Decision: enforce deterministic ordering at the source API boundary (`wepppyo3`) instead of caller-side ad hoc sorting.
  Rationale: one consistent contract for all consumers; lower downstream drift risk.
  Date/Author: 2026-05-13 / Codex.
- Decision: treat release refresh, upstream docs update, and independent code review as mandatory closure gates.
  Rationale: deterministic behavior must be verifiable at the deployed artifact boundary and explicitly recorded in source-of-truth docs.
  Date/Author: 2026-05-13 / Codex.
- Decision: enforce deterministic ordering in Rust return containers (`BTreeMap`) rather than post-processing in Python wrappers.
  Rationale: keeps the determinism contract at the module boundary used by all callers and avoids wrapper-only divergence risk.
  Date/Author: 2026-05-13 / Codex.

## Outcomes & Retrospective

Package completed successfully with deterministic ordering guaranteed for all public map-returning `raster_characteristics` APIs, preserved value/error semantics, green targeted validations in both repositories, refreshed release artifact provenance, and independent review closure with no unresolved high/medium findings. Follow-up work is optional benchmark characterization only; no functional closure gaps remain for this scope.

## Context and Orientation

Target module:
- `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs`

Current exported Python wrapper:
- `/home/workdir/wepppyo3/release/linux/py312/wepppyo3/raster_characteristics/__init__.py`

Primary public functions to audit and harden:
- `identify_mode_single_raster_key`
- `identify_mode_intersecting_raster_keys`
- `identify_median_single_raster_key`
- `identify_median_intersecting_raster_keys`
- `count_intersecting_raster_key_pairs`

Known consumer touch points in WEPPpy:
- `wepppy/nodb/core/landuse.py`
- `wepppy/nodb/core/soils.py`
- `wepppy/nodb/mods/rap/rap.py`
- `wepppy/nodb/mods/rap/rap_ts.py`
- `wepppy/nodb/mods/ash_transport/ash.py`
- `wepppy/nodb/mods/omni/omni_contrast_build_service.py`

The current nondeterminism risk is concentrated where Rust functions return `HashMap`-backed structures to Python. Python dict preserves insertion order, so nondeterministic insertion from `HashMap` yields nondeterministic iteration in Python.

## Plan of Work

Milestone 1: Baseline behavior and contract definition.

Audit each public function for return container type and nested ordering behavior. Record deterministic-order contract as lexical numeric-string ordering for outer and nested keys unless an existing documented contract requires otherwise.

Milestone 2: Implementation in wepppyo3.

Replace nondeterministic return-container paths with deterministic containers (for example `BTreeMap`) at the Python boundary. Keep computational logic and failure semantics unchanged; only ordering behavior should change.

Milestone 3: Regression tests in wepppyo3.

Add tests that call each public function repeatedly on fixed fixtures and assert stable ordered key lists across runs. Add value-parity assertions against expected fixture outputs to prove semantic stability.

Milestone 4: Targeted WEPPpy compatibility checks.

Run targeted WEPPpy tests covering major consumers to confirm no functional regressions and no hidden ordering assumptions break runtime behavior.

Milestone 5: Release build refresh and runtime verification.

Rebuild `raster_characteristics_rust`, copy the resulting `.so` into `release/linux/py312/wepppyo3/raster_characteristics/`, and validate import/runtime behavior from that release tree.

Milestone 6: wepppyo3 docs update.

Update `/home/workdir/wepppyo3/README.md`, `/home/workdir/wepppyo3/docs/module-registry.md`, and `/home/workdir/wepppyo3/docs/release-provenance.md` so deterministic-order behavior and release-refresh evidence are documented at the source.

Milestone 7: Independent code review and findings disposition.

Run an independent correctness-focused review over implementation, tests, and docs; disposition all findings and close with no unresolved high/medium findings.

Milestone 8: Validation evidence and closeout.

Capture commands/results in package artifacts, update tracker and package docs, and move this plan to `prompts/completed` with an outcome note when complete.

## Concrete Steps

Working directories:
- WEPPpy: `/workdir/wepppy`
- wepppyo3: `/home/workdir/wepppyo3`

1. Inventory current function signatures and return containers.

    cd /home/workdir/wepppyo3
    rg -n "fn identify_|fn count_intersecting|PyResult<" raster_characteristics/src/lib.rs

2. Implement deterministic return ordering in Rust/PyO3 paths.

    cd /home/workdir/wepppyo3
    edit raster_characteristics/src/lib.rs

3. Add/extend wepppyo3 tests.

    cd /home/workdir/wepppyo3
    pytest tests/raster_characteristics -q
    cargo test -p raster_characteristics_rust

4. Run targeted WEPPpy tests for key consumers.

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/test_landuse_coverage_area_source.py tests/soils/test_wepppyo3_nodata_guard.py --maxfail=1

    Optional expanded run if touch points broaden:

    wctl run-pytest tests/nodb/mods/test_omni_contrast_build_service.py tests/nodb/mods/test_omni.py --maxfail=1

5. Refresh release artifact for `raster_characteristics`.

    cd /home/workdir/wepppyo3
    export PYO3_PYTHON=/usr/bin/python3.12
    export PYTHON_SYS_EXECUTABLE=$PYO3_PYTHON
    cargo build -p raster_characteristics_rust --release
    cp target/release/libraster_characteristics_rust.so release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so
    PYTHONPATH=/home/workdir/wepppyo3/release/linux/py312 python3.12 -c "from wepppyo3.raster_characteristics import raster_characteristics_rust as rc; print(rc.__file__)"
    sha256sum release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so

6. Update `wepppyo3` docs.

    cd /home/workdir/wepppyo3
    edit README.md docs/module-registry.md docs/release-provenance.md
    git diff --check

7. Run mandatory independent code review/disposition and store artifact.

    cd /workdir/wepppy
    edit docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/artifacts/20260513_code_review.md

8. Update work-package docs and lifecycle status.

    cd /workdir/wepppy
    edit docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/{package.md,tracker.md}
    move this ExecPlan to prompts/completed when done

## Validation and Acceptance

Acceptance criteria:
- Repeated-call tests prove deterministic key ordering for every public map-returning function in `wepppyo3.raster_characteristics`.
- Existing value semantics (mode/median/count outputs) remain unchanged for fixed fixtures.
- Targeted WEPPpy consumer tests pass.
- Release `raster_characteristics` shared object in `release/linux/py312` is rebuilt/copied and import-verified from the release tree.
- `wepppyo3` docs (`README.md`, `docs/module-registry.md`, `docs/release-provenance.md`) are updated for deterministic-order and release-refresh evidence.
- Independent code review/disposition artifact exists with no unresolved high/medium findings.
- No new broad exception handling is introduced.

Validation commands must include exact outputs (`passed` counts) in tracker progress notes.

## Idempotence and Recovery

- This work is safe to rerun because it is contract hardening and tests are repeatable on fixed fixtures.
- If parity tests fail, revert container changes for the failing function and isolate mismatch with fixture-specific asserts before proceeding.
- Keep changes additive and scoped; avoid unrelated refactors during this package.

## Artifacts and Notes

Store command transcripts and concise validation summaries under:
- `docs/work-packages/20260512_wepppyo3_raster_characteristics_deterministic_order/artifacts/`

Suggested files:
- `validation_summary.md`
- `ordering_contract_matrix.md`
- `20260513_code_review.md`
- `20260513_release_refresh.md`

## Interfaces and Dependencies

Required end-state interfaces:
- Public Python APIs in `wepppyo3.raster_characteristics` maintain existing names and arguments.
- Return values remain Python dictionaries/maps but with deterministic iteration order.
- Existing error classes/messages for read/shape/argument failures remain contract-compatible unless explicitly documented in tracker decisions.

Dependencies:
- wepppyo3 Rust crate `raster_characteristics`
- wepppyo3 release export path used by WEPPpy
- targeted WEPPpy consumers listed above
