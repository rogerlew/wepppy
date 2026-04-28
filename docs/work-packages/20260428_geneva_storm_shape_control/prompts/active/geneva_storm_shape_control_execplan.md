# Geneva Storm Shape Control End-to-End Implementation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`. It is self-contained so a new contributor can continue from this file plus the current working tree.

## Purpose / Big Picture

Geneva users need to choose the rainfall storm shape used to turn a selected rainfall depth and duration into timestep rainfall for runoff and peak-flow calculations. Today the public Geneva contract says `neh4_type_b`, but the Python batch path still builds a uniform storm, so reports can describe Type B while runtime artifacts are uniform. After this work, users can select `Uniform`, `NEH-4 B`, `Type I`, `Type IA`, `Type II`, or `Type III`, and the same selected closed enum is validated, executed, persisted, and reported across WEPPcloud, Python Geneva services, and the Rust `geneva_core` kernel.

The observable result is that a Geneva run-batch request with a non-uniform `distribution_type` produces a non-uniform hyetograph artifact and summary/report assumptions that name the selected storm shape without contradiction. Existing payloads that omit `distribution_type` continue to default to `neh4_type_b`.

## Progress

- [x] (2026-04-28 21:35 UTC) Read the package, tracker, active execution prompt, current-status artifact, Type I/IA/II/III research artifact, pre-start QA artifact, and `wepppy/nodb/mods/geneva/specification.md` section 11.6 before coding.
- [x] (2026-04-28 21:35 UTC) Created this active ExecPlan before implementation edits.
- [x] (2026-04-28 21:35 UTC) Recorded implementation start in `docs/work-packages/20260428_geneva_storm_shape_control/tracker.md` and `PROJECT_TRACKER.md`.
- [x] (2026-04-28 21:46 UTC) Inspected both worktrees with `git status --short` and confirmed only this package's docs/resources were dirty.
- [x] (2026-04-28 21:46 UTC) Generated WinTR-20-derived raw table payload, normalized CSV, and metadata under `/workdir/wepppyo3/geneva_core/resources/`.
- [x] (2026-04-28 21:46 UTC) Validated Type II embedded-duration ratios against NEH Chapter 4 Figure 4-31 with maximum absolute difference `0.00050333`, within the required `<= 0.003` tolerance.
- [x] (2026-04-28 22:02 UTC) Implemented the closed storm-shape enum and Rust hyetograph dispatch after source-artifact and Type II ratio gate clearance.
- [x] (2026-04-28 22:12 UTC) Wired storm shape through Python schemas, batch execution, persisted artifacts, query/report payloads, and stale-artifact handling.
- [x] (2026-04-28 22:16 UTC) Added Geneva UI `Storm Shape` control and JavaScript payload tests.
- [x] (2026-04-28 22:20 UTC) Updated Geneva specification and culvert comparison documentation.
- [x] (2026-04-28 22:34 UTC) Ran targeted validation commands and recorded results in `artifacts/2026-04-28_validation_summary.md`.
- [x] (2026-04-28 22:35 UTC) Ran required `reviewer` and `qa_reviewer` gates and dispositioned all Medium/High findings in package artifacts.
- [x] (2026-04-28 22:38 UTC) Updated tracker, package artifacts, and project tracker closure notes.
- [x] (2026-04-28 22:42 UTC) Re-ran the full required validation command set after reconnect and refreshed validation artifact output.

## Surprises & Discoveries

- Observation: The work package blocks Type I/IA/II/III runtime implementation until three source artifacts exist in `/workdir/wepppyo3/geneva_core/resources/` and Type II embedded-duration ratios validate at `<= 0.003` absolute tolerance.
  Evidence: `package.md`, the active execution prompt, and specification section 11.6 all repeat this prerequisite.

- Observation: The NRCS WinTR-20 installer is an InstallShield package containing an MSI and `Data1.cab`; the authoritative Type I/IA/II/III curves were present as built-in WinTR-20 `.tbl` payloads rather than emitted by a model run.
  Evidence: `type_i.tbl`, `type_ia.tbl`, `type_ii.tbl`, and `type_iii.tbl` were extracted from `WinTR-20_Setup_Version3.30.1_7Sept2022.exe`; their hashes and the installer hash are recorded in `geneva_core/resources/nrcs_legacy_24h_distributions.metadata.json`.

- Observation: The extracted source tables use 0.1-hour increments, include 241 cumulative ordinates per distribution from 0.0 to 24.0 hours, and pass monotonic endpoint checks.
  Evidence: The normalized CSV has 241 rows and the metadata records `monotonic_endpoint_checks` as passing for all four legacy distributions.

- Observation: The WEPPpy runtime import surfaces did not initially expose `geneva_build_hyetograph` even after Python/Rust code integration.
  Evidence: Reviewer gate flagged missing callable; rebuild + sync of `cli_revision_rust` shared objects restored callable availability in both `wepppyo3.climate.cli_revision_rust` and `cli_revision_rust`.

- Observation: Runtime can enter inconsistent state if panel distribution and batch hyetograph distribution drift.
  Evidence: QA gate found panel/run-batch mismatch failure mode; explicit run-batch distribution consistency validation and cache-shape-aware panel rebuild logic were required to close it safely.

## Decision Log

- Decision: Preserve `neh4_type_b` as the default for missing or blank `distribution_type`.
  Rationale: Existing API/UI contracts already use `neh4_type_b`; switching the default to `uniform` would be a product-visible behavior change not approved by the package.
  Date/Author: 2026-04-28 / Codex

- Decision: Treat `Storm Shape` as a closed enum and keep custom uploaded distributions out of scope.
  Rationale: The package explicitly names six supported IDs and assigns low security impact based on closed-enum validation. Arbitrary uploaded curves would require a separate security and provenance review.
  Date/Author: 2026-04-28 / Codex

- Decision: Do not silently relabel existing Geneva outputs that claim Type B but were generated by the old Python uniform path.
  Rationale: Old artifacts are scientifically stale relative to the new runtime behavior. Reports and docs need a compatibility policy rather than pretending old output is equivalent to newly generated Type B output.
  Date/Author: 2026-04-28 / Codex

- Decision: Use the official NRCS WinTR-20 3.30.1 installer's built-in Type I/IA/II/III rainfall distribution `.tbl` files as the checked-in raw source artifact.
  Rationale: The package required raw WinTR-20-derived source data before runtime implementation. The installer is the official NRCS-distributed WinTR-20 package and contains the normalized storm distribution tables consumed by WinTR-20. No secondary web tables or hand-entered ordinates are used. The artifact is recorded as raw WinTR-20 table payload rather than a hydrologic run output so reviewers can evaluate the provenance precisely.
  Date/Author: 2026-04-28 / Codex

- Decision: Evolve Geneva run artifacts additively.
  Rationale: `storm_inputs.json`, per-storm `summary.json`, and `hyetograph.parquet` need selected storm-shape and extraction metadata. Existing keys remain readable; new fields are additive (`distribution_type`, `uniform_rainfall_assumed`, and optional extraction/source metadata), and old summaries missing these fields are interpreted through the documented stale-artifact policy rather than relabeled as newly generated Type B.
  Compatibility and regression plan: Preserve missing-value default `neh4_type_b`; keep old summary/event-table reads working when `distribution_type` or extraction metadata is absent; add regression tests for missing `distribution_type`, selected non-uniform execution, and report assumptions.
  Date/Author: 2026-04-28 / Codex

- Decision: Reject non-divisible `duration_minutes / time_step_minutes` combinations before invoking the CN kernel.
  Rationale: Reviewer findings showed non-uniform time vectors can violate CN kernel timestep assumptions. Early explicit validation prevents downstream kernel/runtime failures with clear user-facing errors.
  Date/Author: 2026-04-28 / Codex

- Decision: Require run-batch hyetograph distribution to match persisted panel distribution.
  Rationale: QA findings showed that allowing independent values can produce stale or suppressed results and distribution ambiguity in report payloads. Hard validation preserves one unambiguous run contract.
  Date/Author: 2026-04-28 / Codex

- Decision: Surface legacy-uniform artifact state as an explicit warning instead of relabeling old summaries.
  Rationale: The package requirement forbids silently relabeling interim uniform artifacts as new Type B output. Warning visibility in existing summary warning surfaces provides compatibility without scientific mislabeling.
  Date/Author: 2026-04-28 / Codex

## Outcomes & Retrospective

Implemented and validated end to end across UI, Python, and Rust. The selected storm shape is now a closed six-value enum propagated through prepare/panel/run payloads, run-batch schemas, kernel dispatch, persisted artifacts, and summary/report payloads with default `neh4_type_b` preserved for missing values.

Required source-artifact gating was satisfied before Type I/IA/II/III runtime behavior: raw WinTR-20 table payload, normalized CSV, and metadata were added under `/workdir/wepppyo3/geneva_core/resources/`, and Type II embedded-duration ratio validation passed inside the required `<= 0.003` tolerance.

Reviewer and QA gates both returned findings that were dispositioned in-code and in tests. High-risk closures included kernel callable availability (`geneva_build_hyetograph`), non-divisible timestep validation, panel/run-batch distribution consistency checks, stale-summary suppression on distribution drift, and explicit legacy-uniform warning surfacing.

Validation command set from the active execution prompt was re-run after reconnect and still passes except one known unrelated `wctl run-npm lint` failure in `controllers_js/__tests__/landuse_map_inline.test.js` (`jest/no-conditional-expect`) that predates this package and was not modified here.

## Context and Orientation

There are two repositories involved. `/workdir/wepppy` contains the WEPPcloud application, Python Geneva NoDb services, package documentation, tests, and JavaScript controllers. `/workdir/wepppyo3` contains Rust native kernels; this package changes `geneva_core`.

The key term `hyetograph` means the cumulative rainfall time series for a storm. Geneva frequency-panel cells provide a rainfall depth for a selected duration, such as 60 minutes. A storm shape describes how that duration depth accumulates through time. `Uniform` is linear accumulation. `NEH-4 B` is Geneva's existing Type B curve in Rust. `Type I`, `Type IA`, `Type II`, and `Type III` are NRCS legacy 24-hour cumulative mass curves exported from WinTR-20 and then window-extracted for shorter durations.

The canonical machine IDs are `uniform`, `neh4_type_b`, `type_i`, `type_ia`, `type_ii`, and `type_iii`. The UI labels are `Uniform`, `NEH-4 B`, `Type I`, `Type IA`, `Type II`, and `Type III`.

Current confirmed behavior before this package:

- `wepppy/weppcloud/templates/controls/geneva_pure.htm` exposes a hyetograph time-step control but no storm-shape selector.
- `wepppy/weppcloud/controllers_js/geneva.js` hard-codes `hyetograph.distribution_type = "neh4_type_b"`.
- `wepppy/nodb/mods/geneva/schemas/run_batch_schema.py`, `schemas/query_schema.py`, and `collaborators/frequency_panel_service.py` accept only `neh4_type_b`.
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py` reads the request distribution but always calls `_build_uniform_hyetograph(...)`.
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py` reports assumptions that can combine `storm_distribution_assumption = "neh4_type_b"` with `uniform_rainfall_assumed = true`.
- `/workdir/wepppyo3/geneva_core/src/hyetograph.rs` has an NEH-4 Type B path and rejects other distribution IDs.
- `/workdir/wepppyo3/geneva_core/src/frequency_panel.rs` rejects non-Type-B distributions.

The Type I/IA/II/III algorithm is an embedded-window extraction, not full-curve compression. For an event duration `d` less than 24 hours, the kernel must find the window `[a, a + d]` on the 24-hour cumulative mass curve with maximum rainfall fraction, normalize that window to 0..1, then multiply by the Geneva frequency-panel depth for that same duration. For a 24-hour event, the full source curve is used.

## Plan of Work

First, update package lifecycle docs to show this execution has started. Inspect both worktrees and nested instructions before touching implementation files. Because generated run artifact schemas are changing, keep the schema evolution additive and document compatibility behavior for old artifacts.

Second, satisfy the source-artifact gate in `/workdir/wepppyo3/geneva_core/resources/`. The required files are `nrcs_legacy_24h_distributions.wintr20_raw.txt`, `nrcs_legacy_24h_distributions.csv`, and `nrcs_legacy_24h_distributions.metadata.json`. The metadata must name the WinTR-20 version, generation date, raw file SHA-256, CSV SHA-256, export mode, source time increment, precision, rounding policy, post-processing steps, row count, and monotonic endpoint checks. Type II embedded ratios for 5, 10, 15, 30, 60, 120, 180, 360, 720, and 1440 minutes must match NEH Chapter 4 Figure 4-31 within `<= 0.003` absolute fraction tolerance before Type I/IA/II/III runtime code is implemented.

Third, implement Rust storm-shape dispatch in `/workdir/wepppyo3/geneva_core/src/hyetograph.rs` and any request validation in `/workdir/wepppyo3/geneva_core/src/frequency_panel.rs`. Preserve finite-positive validation, monotonic cumulative output, final closure to total depth, endpoint time-vector behavior, and max timestep caps. Uniform should produce a linear cumulative curve. NEH-4 B should preserve existing behavior behind the shared dispatch. Type I/IA/II/III should load the checked-in source table and return extraction metadata including `source_distribution_type`, `source_curve_duration_hours`, `extraction_start_hours`, `extraction_end_hours`, `extraction_ratio_to_24h`, `event_depth_is_duration_depth`, and `source_table_sha256`.

Fourth, update Python Geneva contracts. `wepppy/nodb/mods/geneva/schemas/run_batch_schema.py` and `schemas/query_schema.py` should accept only the six IDs and default missing values to `neh4_type_b`. `collaborators/frequency_panel_service.py` should preserve `distribution_type` for traceability while avoiding claims that frequency-panel source depths are storm-shape-specific. `collaborators/batch_run_service.py` should replace unconditional `_build_uniform_hyetograph(...)` with the Rust dispatcher and persist selected distribution and extraction metadata in storm inputs, per-storm hyetograph artifacts, storm summaries, and batch summaries. `collaborators/report_payload_service.py` should make report assumptions match generated artifacts and set `uniform_rainfall_assumed` true only for `uniform`.

Fifth, update WEPPcloud UI and JavaScript. Add a `Storm Shape` select in `wepppy/weppcloud/templates/controls/geneva_pure.htm` beside the hyetograph time-step control. Update `wepppy/weppcloud/controllers_js/geneva.js` so prepare, panel, run-workflow, and run-batch payloads carry the selected ID consistently and default to `neh4_type_b` if the control is absent.

Sixth, update tests and documentation. Add Rust tests for every distribution, invalid IDs, time-vector endpoints, Type II Figure 4-31 ratios, and anti-compression behavior for Type I/IA/II/III. Add Python tests for schema validation, missing-value compatibility, selected hyetograph execution, persisted metadata, report assumptions, and stale old-artifact behavior. Add JavaScript tests for default and non-default payload propagation. Update `wepppy/nodb/mods/geneva/specification.md`, `wepppy/nodb/mods/geneva/culvert-cn-comparison.md`, the package tracker, and validation/review artifacts.

Seventh, run the required review gates. After implementation and targeted validations are in place, dispatch a `reviewer` sub-agent for correctness and compatibility, then a `qa_reviewer` sub-agent for test adequacy and closure readiness. Record prompts, findings, dispositions, and residual risks under `docs/work-packages/20260428_geneva_storm_shape_control/artifacts/`. Close or explicitly accept every Medium/High finding with written rationale.

## Concrete Steps

Run these from `/workdir/wepppy` unless another working directory is shown:

    git status --short --untracked-files=all
    cd /workdir/wepppyo3 && git status --short --untracked-files=all

Inspect local instructions before editing files:

    find wepppy/nodb/mods/geneva -name AGENTS.md -print
    find wepppy/weppcloud -name AGENTS.md -print
    cd /workdir/wepppyo3 && find . -name AGENTS.md -print

After source resources exist, validate the Type II embedded ratios with Rust tests before adding or relying on Type I/IA/II/III runtime dispatch. If the ratio test fails above `0.003`, stop runtime implementation and regenerate or improve the source export.

Implementation edits should be made with `apply_patch` for manual code/document changes. Formatting tools or project build generators may rewrite generated files when that is the project's established workflow.

## Validation and Acceptance

Run the package-specified validation commands.

From `/workdir/wepppy`:

    wctl run-npm test -- geneva
    wctl run-npm lint
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-pytest tests/nodb/mods/geneva tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py tests/rq/test_geneva_rq.py tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1
    wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260428_geneva_storm_shape_control --path wepppy/nodb/mods/geneva/specification.md --path wepppy/nodb/mods/geneva/culvert-cn-comparison.md
    git diff --check

From `/workdir/wepppyo3`:

    cargo test -p geneva_core
    git diff --check

Acceptance requires these observable behaviors:

- The Geneva UI contains a `Storm Shape` selector with exactly the six labels and defaults to `NEH-4 B`.
- JavaScript payloads include the selected storm-shape ID for Geneva prepare/panel/run-workflow/run-batch flows and preserve `neh4_type_b` as the fallback.
- Python run-batch schemas accept the six IDs, reject unsupported IDs, and default missing values to `neh4_type_b`.
- Rust hyetograph output for every distribution starts at zero, is monotonic, and ends at the requested depth at the exact requested duration.
- Type I/IA/II/III short-duration events record embedded-window metadata and do not use full-curve compression.
- Selecting `uniform` sets `uniform_rainfall_assumed = true`; selecting any other shape sets it false.
- Existing artifacts missing `distribution_type` remain readable and are treated according to a documented stale-artifact compatibility policy.
- Reports and batch summaries identify the selected storm shape consistently.

## Idempotence and Recovery

Resource generation is safe to repeat only when the raw WinTR-20 output and metadata are regenerated together and hashes are updated consistently. If metadata and CSV hashes diverge, treat the resources as invalid and fix them before continuing runtime implementation.

Schema changes should be additive. Do not rename or remove existing user-visible keys without explicit operator approval. If a test fixture lacks `distribution_type`, keep the fixture readable and prove the default path.

Manual edits must not revert unrelated user changes in either worktree. If unexpected dirty files are present, leave them untouched unless they are directly required for this package.

## Artifacts and Notes

Primary package artifacts live under `docs/work-packages/20260428_geneva_storm_shape_control/artifacts/`.

Required source artifacts in `/workdir/wepppyo3/geneva_core/resources/`:

    nrcs_legacy_24h_distributions.wintr20_raw.txt
    nrcs_legacy_24h_distributions.csv
    nrcs_legacy_24h_distributions.metadata.json

Required review artifacts:

    reviewer gate artifact with prompt/context, findings, dispositions, and residual risks
    qa_reviewer gate artifact with prompt/context, findings, dispositions, and residual risks

Required validation artifact:

    validation summary listing commands, working directories, pass/fail status, and any environment blockers

## Interfaces and Dependencies

Python should expose or reuse a single canonical storm-shape constant/enum for the six IDs in Geneva schema and service code. If the existing code favors tuples or sets rather than `Enum`, follow the local pattern, but avoid duplicating divergent lists.

Rust should expose a closed distribution parser or enum equivalent in `geneva_core` so `hyetograph.rs` and `frequency_panel.rs` validate the same IDs. Unsupported IDs must fail explicitly.

The Rust hyetograph response must include cumulative rainfall points and enough metadata for Python to persist the chosen distribution and extraction details. Python should not rebuild Type I/IA/II/III curves itself; it should call the Rust Geneva kernel dispatcher.

WEPPcloud JavaScript should use the selected DOM control value and only fall back to `neh4_type_b` when the control or value is missing.

Revision note, 2026-04-28 21:35 UTC: Initial ExecPlan created before coding. It records the pre-read status, implementation gates, validation commands, review-gate requirements, and source-artifact prerequisite so the package can be executed end to end without prior chat context.

Revision note, 2026-04-28 22:38 UTC: Updated living-plan sections after implementation and review-gate completion. Progress now marks all milestones complete, findings/dispositions were captured as discoveries and decisions, and outcomes summarize final validation plus known unrelated lint blocker.

Revision note, 2026-04-28 22:42 UTC: Added post-reconnect rerun evidence after user-reported remote disconnect and refreshed progress/outcomes to reflect the second full validation pass.
