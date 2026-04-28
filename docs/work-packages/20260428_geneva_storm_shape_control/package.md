# Geneva Storm Shape Control

**Status**: Complete (2026-04-28)
**Timezone**: UTC

## Overview

This package adds a Geneva user control for storm shape selection and carries that selection through frequency-panel materialization, batch storm construction, Rust hyetograph generation, summary reporting, and documentation. The required choices are `Uniform`, `NEH-4 B`, `Type I`, `Type IA`, `Type II`, and `Type III`.

Current Geneva implementation is internally inconsistent: API/UI payloads name `neh4_type_b` as the only supported distribution, while the Python batch execution path still constructs a uniform cumulative hyetograph. This package must close that gap rather than only adding a dropdown.

## Objectives

- Add a Geneva `Storm Shape` UI control with these canonical values:
  - `uniform` - Uniform
  - `neh4_type_b` - NEH-4 B
  - `type_i` - Type I
  - `type_ia` - Type IA
  - `type_ii` - Type II
  - `type_iii` - Type III
- Define one shared storm-shape contract across WEPPcloud JavaScript, Python NoDb/RQ schemas, query/report payloads, and Rust Geneva kernels.
- Implement Rust hyetograph distribution dispatch for Uniform, NEH-4 B, Type I, Type IA, Type II, and Type III storms.
- Replace the Python batch path's unconditional uniform hyetograph builder with the selected storm-shape kernel output.
- Persist and report the selected storm shape accurately in frequency-panel cells, storm summaries, batch summaries, and Geneva summary reports.
- Update `wepppy/nodb/mods/geneva/specification.md` and `wepppy/nodb/mods/geneva/culvert-cn-comparison.md` to make the new contract and scientific posture authoritative.
- Add regression coverage for the exact current failure mode: selecting a non-uniform shape must change the generated hyetograph and resulting batch assumptions.

## Scope

### Included

- Geneva Pure control UI and controller payload binding in:
  - `wepppy/weppcloud/templates/controls/geneva_pure.htm`
  - `wepppy/weppcloud/controllers_js/geneva.js`
- Python Geneva validation, orchestration, artifact, and report contracts under `wepppy/nodb/mods/geneva/`.
- RQ/route payload propagation for Geneva prepare/panel/run-workflow and run-batch calls where storm-shape data crosses service boundaries.
- Rust Geneva storm-shape implementation in `/workdir/wepppyo3/geneva_core/src/hyetograph.rs` and any dependent Rust frequency-panel/request validation modules.
- Tests for Python schemas/services/routes, JavaScript payload behavior, and Rust hyetograph kernels.
- Documentation updates in:
  - `wepppy/nodb/mods/geneva/specification.md`
  - `wepppy/nodb/mods/geneva/culvert-cn-comparison.md`
  - package tracker and validation artifacts.

### Explicitly Out of Scope

- User-uploaded or arbitrary custom breakpoint distributions.
- Changing CLIGEN or NOAA Atlas 14 source-data derivation beyond preserving selected storm shape in panel/run metadata.
- Non-US Geneva workflow expansion.
- Snowmelt, rain-on-snow, channel routing, reservoir routing, or ARF model expansion.
- Per-event storm-shape mixing within a single Geneva batch. The first implementation should treat `Storm Shape` as a run/panel setting unless a later design explicitly approves per-cell selection.
- Production deployment or run backfill. This package should document stale-artifact behavior, but deployment/backfill remains an operator decision.

## Current Implementation Assessment

Detailed evidence is captured in `artifacts/2026-04-28_current_status_assessment.md`.
Type I/IA/II/III implementation research and the pre-start algorithm specification are captured in `artifacts/2026-04-28_type_i_ia_ii_iii_hyetograph_research.md` and `wepppy/nodb/mods/geneva/specification.md` section 11.6.

Confirmed current state:

- `geneva_pure.htm` exposes only a hyetograph time-step control. It does not expose a storm-shape selector, and its help text references NEH-4 Type B specifically.
- `controllers_js/geneva.js` hard-codes `hyetograph.distribution_type = "neh4_type_b"` in the run payload.
- `schemas/run_batch_schema.py`, `schemas/query_schema.py`, `frequency_panel_service.py`, and the Rust Geneva frequency-panel request validation only accept `neh4_type_b`.
- `batch_run_service.py` ignores `request.hyetograph.distribution_type` during storm construction and calls `_build_uniform_hyetograph(...)` for every selected event.
- Storm summaries and report assumptions currently claim `storm_distribution_assumption = "neh4_type_b"` while also setting `uniform_rainfall_assumed = true`.
- `/workdir/wepppyo3/geneva_core/src/hyetograph.rs` implements an NEH-4 Type B request/response path and rejects every other distribution.
- Geneva docs already identify this as an active gap: the specification says runtime batch behavior is uniform interim, and the culvert comparison says Rust Type B exists but the Python batch path still uses uniform rainfall.
- Staged Wildcat5 macro artifacts currently expose NEH4B and Uniform storm references; Type I/IA/II/III ordinate source selection must be confirmed from an authoritative NRCS/SCS source or another owned validated source before implementation.

## Target Contract

The canonical machine IDs for this package are:

| ID | UI Label | Notes |
| --- | --- | --- |
| `uniform` | Uniform | Linear cumulative rainfall from 0 to depth over storm duration. |
| `neh4_type_b` | NEH-4 B | Existing Geneva Rust kernel behavior, generalized behind shared dispatch. |
| `type_i` | Type I | NRCS/SCS dimensionless storm distribution. |
| `type_ia` | Type IA | NRCS/SCS dimensionless storm distribution. |
| `type_ii` | Type II | NRCS/SCS dimensionless storm distribution. |
| `type_iii` | Type III | NRCS/SCS dimensionless storm distribution. |

Default behavior should remain `neh4_type_b` for new schema-default payloads unless the implementation owner gets explicit product approval to change it. Existing completed artifacts that were generated through the old uniform Python path must not be silently relabeled as scientifically equivalent to newly generated Type B outputs.

## Implementation Milestones

### M1: Source and Contract Confirmation

- Use the pre-start algorithm in `wepppy/nodb/mods/geneva/specification.md` section 11.6.
- Generate the authoritative Type I, Type IA, Type II, and Type III 24-hour ordinate table from NRCS WinTR-20 output before implementation.
- Check in the raw WinTR-20 output, normalized source CSV, and metadata under `/workdir/wepppyo3/geneva_core/resources/`.
- Validate Type II embedded-duration ratios against NEH Chapter 4 Figure 4-31 with absolute fraction tolerance `<= 0.003`; regenerate/export a finer source table before relaxing tolerance.
- Add all-four Type I/IA/II/III anti-compression tests that prove short-duration output uses embedded-window normalization.
- Keep `distribution_type` in frequency-panel materialization for traceability, but treat selected shape as a batch hyetograph/runtime assumption because panel depths and intensities come from source rainfall-frequency data.

### M2: Shared Enum and Schema Surface

- Add a canonical storm-shape enum/list in Python and Rust.
- Update Python request validation to accept all six IDs and reject anything else with explicit messages.
- Update query/report validation constants so persisted cells and storm summaries can contain all supported IDs.
- Preserve backward compatibility for missing `distribution_type` by defaulting to `neh4_type_b`.

### M3: Rust Hyetograph Kernels

- Generalize `Neh4TypeBHyetographRequest`/response naming or add a new dispatch request while preserving compatibility if needed.
- Implement Uniform, NEH-4 B, Type I, Type IA, Type II, and Type III cumulative hyetographs.
- Keep existing safeguards: finite positive depth/duration/time step, max timestep count, monotonic cumulative rainfall, final cumulative closure to depth, and short-duration warnings where applicable.
- Add Rust unit tests for each distribution, interpolation boundaries, closure, monotonicity, invalid distribution rejection, and representative peak timing differences.

### M4: Python Batch Execution Wiring

- Replace `_build_uniform_hyetograph(...)` use in `batch_run_service.py` with the Rust hyetograph dispatcher.
- Persist selected distribution in `storm_inputs.json`, per-storm hyetograph artifacts, storm summaries, and batch summaries.
- Set `uniform_rainfall_assumed` true only for `uniform`.
- Ensure run summary and Geneva summary report assumptions describe the selected shape without contradiction.

### M5: UI and Report Integration

- Add the `Storm Shape` select control beside the existing hyetograph time-step control.
- Update `controllers_js/geneva.js` so prepare/panel/run-workflow/run-batch payloads carry the selected ID consistently.
- Update report/filter payloads and UI labels so users can see which storm shape was used.
- Add JavaScript tests for default selection, non-default selection, and workflow payload propagation.

### M6: Compatibility, Regeneration, and Stale Artifact Policy

- Define how old Geneva outputs should be treated when summaries say `neh4_type_b` but their hyetograph artifact is uniform from the old Python path.
- Add a regeneration or stale-output warning policy if old artifacts are loaded in reports.
- Ensure schema changes are additive and do not break existing runs that omit `distribution_type`.

### M7: Code and QA Review Gates

- Run a code-review sub-agent pass with the `reviewer` role after implementation is complete and before closure.
- Run a QA-review sub-agent pass with the `qa_reviewer` role after targeted tests and documentation updates are in place.
- Record both reviews under package artifacts, including prompt/context, findings, dispositions, and residual risks.
- Close or explicitly accept every Medium/High review finding before package closure. Acceptance of a Medium/High residual requires written rationale in the tracker and package closure notes.

### M8: Validation and Closure

- Run targeted Python, JavaScript, and Rust gates.
- Update work-package tracker with validation outcomes and any deferred follow-ups.
- Close only after docs, contract, and runtime output all agree on the selected storm shape.

## Stakeholders

- **Primary**: Geneva feature maintainers and WEPPcloud operators using Geneva summary/event outputs.
- **Reviewers**: Geneva domain maintainer, WEPPcloud UI maintainer, NoDb/RQ maintainer, `wepppyo3` native-kernel maintainer, required code-review sub-agent (`reviewer`), and required QA-review sub-agent (`qa_reviewer`).
- **Security Reviewer**: Not dedicated unless the implementation expands into custom uploaded distributions, filesystem path inputs, external egress, or broader rq-engine auth changes.
- **Informed**: Users comparing Geneva outputs to Culvert/Wildcat workflows and operators deciding whether existing Geneva runs need regeneration.

## Success Criteria

- [x] Geneva UI exposes `Storm Shape` with Uniform, NEH-4 B, Type I, Type IA, Type II, and Type III choices.
- [x] Payload schemas and RQ/route workflows accept only the six canonical IDs and default missing values to `neh4_type_b`.
- [x] Rust Geneva hyetograph generation supports all six distributions with tests for monotonicity, closure, invalid input, and representative shape differences.
- [x] Raw WinTR-20 output, normalized CSV, and metadata for Type I/IA/II/III are checked in and reproducible.
- [x] Type I/IA/II/III use embedded-window extraction from a WinTR-20-derived 24-hour source curve, not full-curve compression.
- [x] Type I/IA/II/III short-duration anti-compression tests cover every legacy distribution, not only Type II.
- [x] Python batch execution calls the selected hyetograph implementation and no longer uses unconditional uniform rainfall.
- [x] `storm_inputs.json`, per-storm summaries, batch summary, query payload, and report UI agree on selected storm shape.
- [x] `uniform_rainfall_assumed` is true only for Uniform storms.
- [x] Existing runs without `distribution_type` remain readable and use a documented default.
- [x] `specification.md` and `culvert-cn-comparison.md` are updated with the new contract, source/provenance notes, and removed "uniform interim" statements where no longer true.
- [x] Code-review and QA-review sub-agent passes are complete, recorded as artifacts, and all Medium/High findings are closed or explicitly accepted with rationale.
- [x] Targeted Python, JavaScript, and Rust validation gates pass or have documented environment blockers.

## Dependencies

### Prerequisites

- Access to `/workdir/wepppyo3` for Rust Geneva core changes.
- A generated and metadata-documented WinTR-20 raw-output artifact plus normalized source table for Type I, Type IA, Type II, and Type III dimensionless storm ordinates.
- Existing Geneva frequency-panel and summary report contracts from [20260418_geneva_interactive_summary_report](../20260418_geneva_interactive_summary_report/package.md).

### Blocks

- Scientific comparison work that assumes Geneva can vary storm distributions.
- Any user-facing claim that Geneva Type B execution is fully wired through batch runtime.
- Regeneration guidance for existing Geneva reports that were produced by the interim uniform Python path.

## Related Packages

- **Related**: [20260418_geneva_interactive_summary_report](../20260418_geneva_interactive_summary_report/package.md)
- **Related**: [20260428_wepppyo3_repositioning](../20260428_wepppyo3_repositioning/package.md)
- **Follow-up**: Optional operator package for production deployment, run regeneration, and stale-artifact communication.

## Timeline Estimate

- **Expected duration**: 3-5 focused sessions across WEPPpy and `wepppyo3`.
- **Complexity**: High, because the change crosses UI, schemas, RQ payloads, Python orchestration, Rust scientific kernels, generated artifacts, and report semantics.
- **Risk level**: Medium-High. Scientific output changes are expected once the selected hyetograph is actually used.

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: The package adds a closed enum input and changes run-scoped model computation. It does not require new auth, secret handling, arbitrary file paths, external network egress, or user-uploaded executable/content parsing. Keep validation strict; if custom distributions or uploaded ordinate files enter scope, re-triage as high.
- **Security review artifact**: `N/A`

## Validation Plan

Expected gates for implementation closure:

```bash
wctl run-npm test -- geneva
wctl run-npm lint
python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
wctl run-pytest tests/nodb/mods/geneva tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py tests/rq/test_geneva_rq.py tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1
cd /workdir/wepppyo3 && cargo test -p geneva_core
```

If `wctl run-npm lint` continues to fail on known unrelated `landuse_map_inline.test.js` conditional-expect lint, record that blocker separately and keep Geneva-targeted validation green.

Required review gates:

- `reviewer` sub-agent: focus on correctness, schema/API compatibility, stale-artifact handling, cross-repo `wepppyo3` integration, and output contract regressions.
- `qa_reviewer` sub-agent: focus on test adequacy, UX/report clarity, documentation completeness, validation reproducibility, and closure readiness.
- Review artifacts must live under `docs/work-packages/20260428_geneva_storm_shape_control/artifacts/` and include finding disposition status.

## References

- `wepppy/weppcloud/templates/controls/geneva_pure.htm`
- `wepppy/weppcloud/controllers_js/geneva.js`
- `wepppy/nodb/mods/geneva/schemas/run_batch_schema.py`
- `wepppy/nodb/mods/geneva/schemas/query_schema.py`
- `wepppy/nodb/mods/geneva/collaborators/frequency_panel_service.py`
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py`
- `wepppy/nodb/mods/geneva/specification.md`
- `wepppy/nodb/mods/geneva/culvert-cn-comparison.md`
- `/workdir/wepppyo3/geneva_core/src/hyetograph.rs`
- `/workdir/wepppyo3/geneva_core/src/frequency_panel.rs`
- `artifacts/2026-04-28_type_i_ia_ii_iii_hyetograph_research.md`
- `artifacts/2026-04-28_type_hyetograph_spec_qa_validation.md`
- `prompts/active/execute_geneva_storm_shape_control_prompt.md`

## Deliverables

- Implementation PR/commit set spanning WEPPpy and `wepppyo3`.
- Updated Geneva UI storm-shape control and controller payload tests.
- Rust hyetograph distribution kernels and tests.
- Python schema/orchestration/report wiring and tests.
- Updated Geneva specification and culvert comparison docs.
- Active execution prompt for starting the package with a live ExecPlan.
- Code-review and QA-review artifacts with finding dispositions.
- Pre-start QA validation artifact for the Type I/IA/II/III specification.
- Validation summary artifact.

## Follow-up Work

- Decide whether to expose regional/default storm-shape presets after the six explicit shapes are implemented.
- Consider a later custom-distribution package if users need uploaded breakpoint storms; that should receive separate security and provenance review.
- Consider an operator/regeneration package if existing Geneva outputs need to be rebuilt or flagged in production.
