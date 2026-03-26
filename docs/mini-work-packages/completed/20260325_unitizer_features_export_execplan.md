# Unitizer Numeric APIs For Features Export

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and must be maintained in accordance with that template.

## Purpose / Big Picture

Features Export needs Unitizer conversions that return numbers and machine-readable metadata instead of HTML snippets. After this change, export code can convert scalar values, sequences, and table-like data using `si`, `english`, or `project` unit modes, while receiving explicit metadata and pass-through reasons for no-mapping cases. Existing template/context processor behavior for `unitizer`, `unitizer_units`, and `unitizer_with_units` remains unchanged so current routes and report rendering continue to work.

## Progress

- [x] (2026-03-25 19:24Z) Read required guidance and source files: root/local `AGENTS.md`, exec plan template, Unitizer spec, target implementation/stubs, and target tests.
- [x] (2026-03-25 19:34Z) Defined public Unitizer numeric API surface: `get_unit_class`, `resolve_target_unit`, `convert_scalar`, `convert_sequence`, `convert_table`, metadata/result dataclasses, and `preferences_fingerprint`.
- [x] (2026-03-25 19:34Z) Implemented numeric conversion APIs with explicit pass-through/no-mapping reasons and preserved legacy context-processor behavior.
- [x] (2026-03-25 19:34Z) Updated `wepppy/nodb/unitizer.pyi` for all new public APIs and dataclasses.
- [x] (2026-03-25 19:34Z) Added `tests/nodb/test_unitizer_numeric_apis.py` for conversion correctness, metadata, no-mapping signaling, project-mode resolution, table-shape support, fingerprint stability, and backward-compat context processor behavior.
- [x] (2026-03-25 21:00Z) Ran required validation commands (`pytest` targets, `stubtest`, `check-test-stubs`) and final full-suite sanity `wctl run-pytest tests --maxfail=1` (`2582 passed, 34 skipped`).
- [x] (2026-03-25 21:00Z) Completed independent correctness and QA review passes; resolved all high/medium findings (ambiguous unit-class resolution and identity type coercion) and revalidated.
- [x] (2026-03-25 21:00Z) Updated plan artifacts/outcomes and prepared final handoff summary.

## Surprises & Discoveries

- Observation: `Unitizer.context_processor_package()` currently owns helper logic like unit-class detection inside nested functions, so new numeric APIs cannot reuse it directly without extracting shared helpers.
  Evidence: `wepppy/nodb/unitizer.py` defines `determine_unitclass` only inside `context_processor_package()`.
- Observation: The `distance` class currently has `km -> mi` and `mi -> m` converter keys, so `mi -> km` is unresolved and is now surfaced as explicit `no_mapping` by the new APIs.
  Evidence: New API path `convert_scalar(..., source_unit="mi", units_mode="si")` resolves target `km` but returns metadata `pass_through_reason="no_mapping"`.
- Observation: Unit labels are not globally unique across classes (for example `ppm` appears in multiple concentration classes), so target validation must be class-local rather than using global lookup.
  Evidence: Initial explicit-target check rejected `source_unit="mg/L", target_unit="ppm"` despite `ppm` being valid for `sm-concentration`; fixed by validating membership in `precisions[unit_class]`.

## Decision Log

- Decision: Keep legacy HTML-oriented context processor functions intact and add new numeric APIs as separate public methods/classes.
  Rationale: Features Export needs machine-friendly conversion data, but report templates and routes depend on existing HTML behavior.
  Date/Author: 2026-03-25 / Codex
- Decision: Use explicit pass-through reason strings (`no_mapping`, `non_numeric`, `identity`, `missing_column`, etc.) in metadata instead of hidden fallback conversions.
  Rationale: Features Export manifesting and cache/debug flows require machine-readable explanation when conversion is not applied.
  Date/Author: 2026-03-25 / Codex
- Decision: Treat explicit `target_unit` compatibility as class-local membership (`target_unit in precisions[resolved_unit_class]`) instead of a global class lookup.
  Rationale: Some unit labels are shared by multiple classes, and global resolution incorrectly rejects valid explicit targets.
  Date/Author: 2026-03-25 / Codex
- Decision: For ambiguous source units (for example `ppm`), do not silently choose the first class; return explicit `ambiguous_unit_class` signaling unless a unique class can be inferred from an explicit target.
  Rationale: First-match resolution can produce incorrect numeric conversions and invalid metadata for export manifests.
  Date/Author: 2026-03-25 / Codex
- Decision: Preserve original value types on identity paths (`source_unit == target_unit`) while keeping `conversion_applied=False`.
  Rationale: Identity conversions should not mutate schemas (for example coercing integer columns to floats) when no conversion is applied.
  Date/Author: 2026-03-25 / Codex

## Outcomes & Retrospective

Completed. New numeric Unitizer APIs now provide scalar/sequence/table conversion, project-mode target resolution, explicit pass-through/no-mapping signaling, and stable preferences fingerprints for cache usage. Existing context processor behavior remains intact and route compatibility tests stayed green.

Independent reviewer and QA reviewer passes surfaced high/medium issues that were resolved in-tree: ambiguous unit-class resolution now emits explicit signaling, identity conversions preserve original value types, and expanded tests cover ambiguous/edge paths. Final validation runs are green.

## Context and Orientation

This change is centered in `wepppy/nodb/unitizer.py`, which currently stores conversion maps (`converters`, `precisions`), user preferences, and HTML rendering helpers exposed through `context_processor_package()`. The stub file `wepppy/nodb/unitizer.pyi` exposes current public members and must be updated to match new APIs. Existing route behavior is exercised in `tests/weppcloud/routes/test_unitizer_bp.py`, and unit preference behavior is covered in `tests/nodb/test_unitizer_preferences.py`.

In this repository, `project` units mode means converting into the persisted user preference for each unit class (for example `area -> acre` when English preference is active). `si` and `english` are global target modes based on canonical ordering in `precisions`. “No mapping” means Unitizer cannot determine a unit class or converter for the requested source/target pair; the new APIs must signal that explicitly instead of silently treating the value as converted.

## Plan of Work

First, add shared public helpers in `wepppy/nodb/unitizer.py` to determine unit class, resolve target units for a requested mode, and produce conversion metadata. Define small typed dataclasses for resolution and conversion results so callers can consume metadata without parsing HTML.

Next, add public methods on `Unitizer` for scalar conversion, sequence conversion, and table conversion. Scalar conversion will be the primitive; sequence and table helpers will call it in a loop while preserving input shape. Table conversion will support pandas DataFrame when pandas is installed and fall back to dictionary-of-sequences and list-of-dictionaries shapes.

Then, add a stable preferences fingerprint helper on `Unitizer` for cache-key usage when `units=project`. The fingerprint will hash canonical JSON with sorted keys for deterministic output.

After code changes, update `wepppy/nodb/unitizer.pyi` with all new public APIs and result dataclasses. Add targeted tests in `tests/nodb/` for numeric correctness, preference-based target resolution, metadata fields, pass-through/no-mapping signaling, table-shape support, and fingerprint stability. Keep route tests unchanged except for compatibility confirmation.

Finally, run required validation commands and independent review agents (`reviewer`, `qa_reviewer`), fix high/medium issues, and record results in this plan and final handoff.

## Concrete Steps

From `/workdir/wepppy`:

1. Create/update ExecPlan and keep living sections current while implementing.
2. Edit `wepppy/nodb/unitizer.py` to add numeric conversion APIs and metadata classes.
3. Edit `wepppy/nodb/unitizer.pyi` to mirror all new public APIs.
4. Add/update tests under `tests/nodb/` and keep existing route tests green.
5. Run:
   `wctl run-pytest tests/nodb/test_unitizer_preferences.py --maxfail=1`
   `wctl run-pytest tests/weppcloud/routes/test_unitizer_bp.py --maxfail=1`
   `wctl run-pytest <new_or_updated_unitizer_test_modules> --maxfail=1`
   `wctl run-stubtest wepppy.nodb.unitizer`
   `wctl check-test-stubs`
6. If practical, run `wctl run-pytest tests --maxfail=1` and document result or skip reason.
7. Run independent `reviewer` and `qa_reviewer` subagents, apply fixes, and re-run impacted tests.

Expected observable evidence:
- New tests demonstrate explicit no-mapping signaling and metadata output.
- Existing unitizer route tests continue passing without route contract changes.

## Validation and Acceptance

Acceptance is satisfied when all of the following are true:

- New public numeric Unitizer APIs exist for scalar, sequence, and table conversion and return metadata including `source unit`, `target unit`, `unit class`, `precision policy`, and `conversion_applied`.
- `project` mode resolves target units from persisted Unitizer preferences.
- No-mapping/pass-through cases are explicit in returned metadata (not silent).
- Existing context processor/template behavior remains intact and route tests pass.
- `wepppy/nodb/unitizer.pyi` matches runtime public APIs.
- Required tests and type/stub checks pass.
- Independent review findings are addressed for high/medium severity or explicitly justified.

## Idempotence and Recovery

Edits are additive and can be re-run safely. Tests can be rerun repeatedly without side effects. If a test fails due to an implementation mistake, revert only the affected file changes and rerun the targeted command. No data migrations or destructive operations are part of this work.

## Artifacts and Notes

Validation commands and outcomes from `/workdir/wepppy`:

1. `wctl run-pytest tests/nodb/test_unitizer_preferences.py --maxfail=1` -> pass (4 passed).
2. `wctl run-pytest tests/weppcloud/routes/test_unitizer_bp.py --maxfail=1` -> pass (2 passed).
3. `wctl run-pytest tests/nodb/test_unitizer_numeric_apis.py --maxfail=1` -> pass (29 passed).
4. `wctl run-stubtest wepppy.nodb.unitizer` -> pass (no issues found).
5. `wctl check-test-stubs` -> pass (all stubs complete).
6. `wctl run-pytest tests --maxfail=1` -> pass (`2582 passed, 34 skipped`).

Review findings and fixes:

- Correctness review:
  High resolved: ambiguous source units (for example `ppm`) no longer silently select first class; `resolve_target_unit` now signals `ambiguous_unit_class` unless a unique class is inferred.
  Medium resolved: identity path no longer coerces numeric type; `_convert_scalar_with_resolution` now preserves original `value` when no conversion is applied.
- QA review:
  No high/medium findings on final pass; coverage deemed sufficient for current scope (one low-risk non-blocking note about an untested defensive branch).

## Interfaces and Dependencies

New public interfaces will be added in `wepppy/nodb/unitizer.py` and mirrored in `wepppy/nodb/unitizer.pyi`. The expected final interface surface includes:

- Public conversion metadata/result dataclasses.
- Public unit-class and target-resolution helpers.
- `Unitizer` methods for scalar, sequence, and table conversion in `si|english|project` modes.
- Public preferences fingerprint helper for stable cache integration.

No new third-party dependencies are introduced. Pandas support is opportunistic: dataframe conversion works when pandas is present, with safe non-pandas fallback shapes.

## Revision Notes

- 2026-03-25 (Codex): Created initial ExecPlan at user-specified path after source/context review so implementation can proceed milestone-by-milestone with living-section tracking.
- 2026-03-25 (Codex): Updated plan after first implementation pass to capture completed API/stub/test milestones, a converter-map discovery, and explicit signaling decision before validation/review stages.
- 2026-03-25 (Codex): Recorded validation evidence, review findings, and final outcomes after fixing explicit-target class validation and rerunning impacted checks.
- 2026-03-25 (Codex): Refreshed validation totals after a final post-fix full-suite run to keep the plan’s acceptance evidence accurate.
- 2026-03-25 (Codex): Finalized review-resolution notes and validation counts after closing remaining QA coverage findings and rerunning required checks.
- 2026-03-25 (Codex): Reconciled plan notes with final independent review outcomes (ambiguous class handling and identity-type preservation) and updated completion timestamps.
