# Current Status Assessment - Geneva Storm Shape Control

**Date**: 2026-04-28 20:52 UTC
**Scope**: Geneva storm-shape UI, Python NoDb/RQ contracts, Rust Geneva hyetograph kernels, and current documentation.

## Summary

Geneva currently has partial storm-distribution scaffolding, not complete storm-shape support. `neh4_type_b` is the only accepted distribution ID in UI payloads, Python validators, query/report validators, and Rust request validators. Despite that, Python batch execution still constructs a uniform cumulative rainfall series for every selected storm cell.

The requested feature is therefore a contract repair and model execution change, not just a new UI select.

## Confirmed Current State

### UI and JavaScript

- `wepppy/weppcloud/templates/controls/geneva_pure.htm` exposes `Hyetograph time step` but no storm-shape selector.
- The time-step help text still says the value is used when expanding the NEH-4 Type B hyetograph.
- `wepppy/weppcloud/controllers_js/geneva.js` hard-codes:

```javascript
hyetograph: {
    distribution_type: "neh4_type_b",
    time_step_minutes: parseFloat(raw.geneva_run_time_step_minutes || "1.0")
}
```

### Python Schema and Services

- `wepppy/nodb/mods/geneva/schemas/run_batch_schema.py` defines `_ALLOWED_DISTRIBUTION_TYPES = {"neh4_type_b"}` and rejects every other ID.
- `wepppy/nodb/mods/geneva/schemas/query_schema.py` defines `GENEVA_DISTRIBUTION_IDS = ("neh4_type_b",)` and validates panel/report cells against that list.
- `wepppy/nodb/mods/geneva/collaborators/frequency_panel_service.py` rejects non-Type-B values and reports `uniform` and `custom_breakpoint` only as reserved IDs.
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py` reads `request.hyetograph.distribution_type`, but storm construction ignores it and calls `_build_uniform_hyetograph(...)`.
- `batch_run_service.py` writes per-storm assumptions with both `storm_distribution_assumption = "neh4_type_b"` and `uniform_rainfall_assumed = True`.
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py` also returns report assumptions with `storm_distribution_assumption = "neh4_type_b"` and `uniform_rainfall_assumed = True`.

### Rust Geneva Core

- `/workdir/wepppyo3/geneva_core/src/hyetograph.rs` contains NEH-4 Type B constants and a `Neh4TypeBHyetographRequest`.
- The Rust request validator rejects every distribution except `neh4_type_b`.
- `/workdir/wepppyo3/geneva_core/src/frequency_panel.rs` also rejects every distribution except `neh4_type_b`.
- There are no Rust Geneva implementations for `uniform`, `type_i`, `type_ia`, `type_ii`, or `type_iii`.

### Documentation

- `wepppy/nodb/mods/geneva/specification.md` already documents the gap:
  - runtime batch hyetograph distribution is **Uniform (interim)**,
  - the NEH4 Type B kernel exists in Rust,
  - the Type B kernel is not wired into Python `run_batch`,
  - `hyetograph.distribution_type` currently must be `neh4_type_b`,
  - current runtime behavior uses uniform cumulative rainfall.
- `wepppy/nodb/mods/geneva/culvert-cn-comparison.md` also documents that Geneva's Rust Type B exists while Python batch execution currently uses uniform rainfall.
- Existing Wildcat5 macro artifacts under `wepppy/nodb/mods/geneva/resources/Wildcat5/` visibly reference NEH4B and Uniform storm paths. They did not surface Type I/IA/II/III ordinate definitions in the initial search.

## What Must Be Implemented

### Contract Surface

- Add canonical IDs:
  - `uniform`
  - `neh4_type_b`
  - `type_i`
  - `type_ia`
  - `type_ii`
  - `type_iii`
- Keep validation closed and explicit across UI, Python, query/report payloads, and Rust.
- Preserve missing-value compatibility by defaulting to `neh4_type_b`, unless a product decision changes the default.

### Rust Hyetograph Generation

- Generalize the current Type-B-specific request/response path or add a new dispatch request.
- Implement cumulative hyetograph generation for all six shapes.
- Confirm source/provenance for Type I, Type IA, Type II, and Type III ordinates before coding.
- Test monotonicity, closure to total depth, invalid inputs, and distinct shape behavior.

### Python Runtime Wiring

- Replace `_build_uniform_hyetograph(...)` in batch execution with the selected Rust hyetograph dispatcher.
- Persist selected `distribution_type` in `storm_inputs.json`, per-storm summaries, batch summaries, and generated hyetograph artifacts.
- Set `uniform_rainfall_assumed` only when `distribution_type == "uniform"`.
- Update warning/error behavior for any hyetograph kernel rejection.

### UI and Reporting

- Add a Geneva `Storm Shape` select control with labels exactly matching the package contract.
- Bind the selected value into run-batch and run-workflow payloads.
- Show selected storm shape in summary/report payloads without contradiction.
- Add tests for default and non-default UI payload propagation.

### Documentation

- Update `specification.md` to replace "uniform interim" language after implementation and record the exact storm-shape contract.
- Update `culvert-cn-comparison.md` to reflect that Geneva can execute selected distributions after the implementation lands.
- Document old artifact behavior because existing summaries may claim Type B while their hyetograph was generated uniformly.

## Open Questions

- What is the authoritative ordinate source for Type I, Type IA, Type II, and Type III in this codebase?
- Should `distribution_type` be persisted on frequency-panel cells even if panel depth/intensity values are source-data properties and not distribution-derived?
- Should old completed runs receive a report warning, a stale artifact marker, or no special handling?
- Should the initial UI default remain NEH-4 B to match existing payload defaults, or should product explicitly switch the visible default to Uniform to match historical runtime behavior?

## Validation Needs

- Rust: `cd /workdir/wepppyo3 && cargo test -p geneva_core`
- JavaScript: `wctl run-npm test -- geneva`
- JavaScript lint and bundle rebuild:

```bash
wctl run-npm lint
python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
```

- Python targeted tests:

```bash
wctl run-pytest tests/nodb/mods/geneva tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py tests/rq/test_geneva_rq.py tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1
```
