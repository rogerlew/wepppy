# ExecPlan: Add Backward-Compatible `QRain`/`QSnow` Support to Hillslope Element Interchange

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

WEPP binaries built from current `wepp-forest` source now append two daily runoff-partition columns (`QRain`, `QSnow`) to `H*.element.dat`. Today, WEPPpy hillslope element interchange rejects those rows because the parser enforces a fixed legacy line width and fails on trailing payload.

After this change, WEPPpy interchange will parse both legacy and new `H*.element.dat` layouts. New runs will preserve `QRain`/`QSnow` in `H.element.parquet`; older runs without those columns will remain readable and emit null values for the new fields.

## Progress

- [x] (2026-03-19 22:11Z) Authored initial ExecPlan with upstream change evidence, implementation milestones, validation commands, and review gates.
- [x] (2026-03-19 22:19Z) Implemented parser/schema updates for legacy + `QRain`/`QSnow` element layouts, including Rust optional-column normalization before schema materialization.
- [x] (2026-03-19 22:19Z) Added targeted interchange coverage for legacy, appended `QRain`/`QSnow`, mixed legacy+new file sets, and optional rust-column normalization helper behavior.
- [x] (2026-03-19 22:40Z) Completed independent correctness + QA review passes (`reviewer`, then `qa_reviewer`) over the working diff; no high/medium findings were raised.
- [x] (2026-03-19 22:40Z) No blocking review findings required code fixes; re-ran affected validation (`tests/wepp/interchange/test_element_interchange.py`) after review gates.
- [x] (2026-03-19 22:40Z) Finalized outcomes and handoff-ready evidence.
- [x] (2026-03-19 22:49Z) Added native `wepppyo3` hillslope element support for optional `QRain`/`QSnow` columns and updated `wepp_interchange` Rust schema parity.
- [x] (2026-03-19 22:49Z) Added `wepppyo3` regression tests for legacy/extended/mixed element rows and validated rust parity execution with explicit env injection inside container.

## Surprises & Discoveries

- Observation: the requested change was described as “rill/interrill outputs,” but upstream code and headers indicate the newly appended element columns are rainfall-vs-snowmelt runoff partition fields (`QRain`, `QSnow`).
  Evidence: `wepp-forest` commit `5ac577e` (“Partition daily runoff depth”) updates `src/contin.for`, `src/sedout.for`, and `src/outfil.for`, appending `QRain`/`QSnow` to `*.element.dat` output.

- Observation: current WEPPpy parser fails hard on any extra payload beyond legacy fixed-width columns.
  Evidence: `wepppy/wepp/interchange/hill_element_interchange.py::_split_fixed_width_line` raises `ValueError` when trailing non-whitespace exists after legacy widths.

- Observation: newly vendored binaries in this repo expose the new headers while older binaries do not.
  Evidence: `strings` output from `wepp_runner/bin/wepp_260319*` includes `"... SedLeave   QRain   QSnow"`, while `wepp_runner/bin/wepp_dcc52a6` and `wepp_runner/bin/wepp_251003*` do not.

- Observation: upstream FORTRAN element output appends `QRain` and `QSnow` as `2(1x,f8.3)`, i.e., two extra fixed-width fields with width 9 each including leading separator spacing.
  Evidence: `src/sedout.for` format label `1000` and `src/contin.for` format label `1200` include `...,1x,f8.3,2(1x,f8.3)`.

- Observation: `wctl run-pytest` does not propagate `WEPPPY_RUST_INTERCHANGE_TESTS=1` from the host shell into the container command environment.
  Evidence: step-7 command continued to skip with reason “Rust parity tests disabled; set WEPPPY_RUST_INTERCHANGE_TESTS=1 to enable.” while direct `docker compose ... WEPPPY_RUST_INTERCHANGE_TESTS=1 ... pytest ...` executed and passed.

## Decision Log

- Decision: model this change in interchange as optional new element columns named exactly `QRain` and `QSnow`.
  Rationale: this matches upstream WEPP headers and avoids introducing interpretation drift.
  Date/Author: 2026-03-19 / Codex

- Decision: preserve backward compatibility by accepting both old and new row layouts and storing nulls for `QRain`/`QSnow` when absent.
  Rationale: existing historical runs and fixtures must remain parseable without regeneration.
  Date/Author: 2026-03-19 / Codex

- Decision: enforce two independent review gates (`reviewer` then `qa_reviewer`) and require explicit finding resolution before completion.
  Rationale: requested by user; reduces regression risk on parser/schema changes.
  Date/Author: 2026-03-19 / Codex

- Decision: preserve existing fixed-width legacy parsing as the primary payload and parse optional `QRain`/`QSnow` strictly as a two-field fixed-width tail when present; reject any additional trailing payload beyond that tail.
  Rationale: this keeps existing parse guarantees while enabling backward-compatible extension using the exact upstream width contract.
  Date/Author: 2026-03-19 / Codex

- Decision: keep interchange dataset version unchanged in this scoped patch and update only the `hill_element` schema snapshot fields.
  Rationale: this change set is narrowly scoped to hillslope element parsing/schema and avoids unrelated snapshot churn; versioning can be addressed separately if a global interchange-version policy update is requested.
  Date/Author: 2026-03-19 / Codex

- Decision: treat step-7 rust parity output (`1 skipped`, pytest exit code `5`) as environment-gated/non-blocking while recording it in validation evidence.
  Rationale: the command was executed exactly as required and produced no runnable selected tests in this environment.
  Date/Author: 2026-03-19 / Codex

- Decision: implement native optional-tail parsing in `wepppyo3` hillslope element parser and emit nullable `QRain`/`QSnow` vectors directly from Rust, rather than relying only on Python-side column backfill.
  Rationale: preserves rust-path parity and removes behavior drift between Python and Rust parsing paths.
  Date/Author: 2026-03-19 / Codex

## Outcomes & Retrospective

Completed.

Delivered behavior:
- `hill_element_interchange` now accepts legacy fixed-width rows and extended rows containing appended `QRain`/`QSnow`, while still rejecting unexpected payload beyond the supported optional tail.
- `SCHEMA` now includes nullable `QRain` and `QSnow` fields (units `mm`), appended after `SedLeave`.
- Legacy source rows populate `QRain`/`QSnow` as null; extended rows preserve numeric values.
- Rust-column adaptation now fills missing optional columns with nulls before Arrow table construction.

Validation evidence:
- `wctl run-pytest tests/wepp/interchange/test_element_interchange.py` -> passed (`6 passed`).
- `wctl run-pytest tests/wepp/interchange --maxfail=1` -> passed (`56 passed, 3 skipped`).
- `WEPPPY_RUST_INTERCHANGE_TESTS=1 wctl run-pytest tests/wepp/interchange/test_watershed_interchange_rust_parity.py -k hillslope_element --maxfail=1` -> skipped/no collection in this environment (`1 skipped`; pytest exit code `5` because no selected tests executed).
- `wctl doc-lint --path docs/mini-work-packages/20260319_wepp_element_qrain_qsnow_interchange_execplan.md` -> passed.
- `wctl doc-lint --path wepppy/wepp/interchange/README.md` -> passed.
- `python3 -m pytest tests/wepp_interchange -q` from `/workdir/wepppyo3` after rebuilding `wepp_interchange_rust` -> passed (`5 passed`).
- `docker compose -f docker/docker-compose.dev.yml exec weppcloud bash -lc '... WEPPPY_RUST_INTERCHANGE_TESTS=1 ... pytest tests/wepp/interchange/test_watershed_interchange_rust_parity.py -k hillslope_element ...'` -> passed (`1 passed, 12 deselected`).

Review findings/resolution:
- `reviewer`: no high/medium findings; no blocking correctness regressions identified in parser/schema/test diff.
- `qa_reviewer`: no high/medium findings; minor readability suggestion on schema formatting addressed by normalizing `SCHEMA` field indentation in `hill_element_interchange.py`.
- Post-review rerun: `wctl run-pytest tests/wepp/interchange/test_element_interchange.py` remained green after readability cleanup.

## Context and Orientation

This change is localized to hillslope element interchange in WEPPpy.

Key parser and schema files:

- `wepppy/wepp/interchange/hill_element_interchange.py`
- `wepppy/wepp/interchange/hill_element_interchange.pyi`
- `tests/wepp/interchange/test_element_interchange.py`
- `tests/wepp/interchange/fixtures/schema_snapshots/hill_element.json`
- `tests/wepp/interchange/schema_snapshot.py`

Optional Rust interop touchpoint (if needed for parity behavior):

- `wepppy/wepp/interchange/hill_element_interchange.py::_parse_element_file_rust`

Upstream WEPP source evidence for the new columns:

- `/workdir/wepp-forest/src/outfil.for` (header now includes `QRain`, `QSnow`)
- `/workdir/wepp-forest/src/contin.for` and `/workdir/wepp-forest/src/sedout.for` (write `qrainp`, `qsnowp` values)
- Commit: `5ac577eaec99137b5f2904c9bbf6ef2af7faa17d`

Vendored binaries already staged in this repo:

- `wepp_runner/bin/wepp_260319`
- `wepp_runner/bin/wepp_260319_hill`

## Plan of Work

Milestone 1 updates the element parser to accept both row variants. Define legacy and extended column layouts and parse based on row length/header shape rather than assuming a single fixed width. The parser must keep current behavior for legacy files and capture `QRain`/`QSnow` when present.

Milestone 2 extends the Arrow schema with nullable `QRain` and `QSnow` fields (units `mm`, with concise descriptions). For legacy source files, populate these fields as `None`. Keep all existing column names and ordering stable, appending new fields at the end.

Milestone 3 hardens Rust-path compatibility. If Rust columns are missing the new optional fields, adapt columns before `pa.table(..., schema=SCHEMA)` so optional fields are filled with nulls rather than raising. This keeps fallback behavior robust while Rust implementation catches up.

Milestone 4 updates tests and schema snapshots. Add explicit tests for mixed compatibility and update `hill_element.json` to include new schema fields and version metadata expectations.

Milestone 5 runs validation and two independent review gates. Resolve all findings, rerun relevant tests, and update this ExecPlan sections with exact results.

## Concrete Steps

Run from repository root:

    cd /workdir/wepppy

1. Implement parser and schema support.

   Edit:
   - `wepppy/wepp/interchange/hill_element_interchange.py`
   - `wepppy/wepp/interchange/hill_element_interchange.pyi`

2. Add regression and compatibility tests.

   Edit:
   - `tests/wepp/interchange/test_element_interchange.py`

   Required new test coverage:
   - legacy rows (no `QRain`/`QSnow`) still parse.
   - rows with appended `QRain`/`QSnow` parse with exact numeric values.
   - mixed file set (legacy + new format) parses in a single interchange run.
   - optional rust-column normalization path (if Rust module present or via unit-level helper test).

3. Update schema snapshot and assertions.

   Edit:
   - `tests/wepp/interchange/fixtures/schema_snapshots/hill_element.json`
   - optionally `tests/wepp/interchange/schema_snapshot.py` only if helper behavior needs adjustment.

4. Update interchange docs to mention new columns and compatibility behavior.

   Edit:
   - `wepppy/wepp/interchange/README.md`

5. Run targeted validation.

    wctl run-pytest tests/wepp/interchange/test_element_interchange.py

6. Run broader interchange sanity.

    wctl run-pytest tests/wepp/interchange --maxfail=1

7. If Rust parity is enabled in this environment, run the relevant parity scope.

    WEPPPY_RUST_INTERCHANGE_TESTS=1 wctl run-pytest tests/wepp/interchange/test_watershed_interchange_rust_parity.py -k hillslope_element --maxfail=1

8. Run docs lint for changed docs.

    wctl doc-lint --path docs/mini-work-packages/20260319_wepp_element_qrain_qsnow_interchange_execplan.md
    wctl doc-lint --path wepppy/wepp/interchange/README.md

9. Independent correctness review gate.

   Spawn a `reviewer` subagent to inspect the full diff for correctness and regression risk. Require severity-ranked findings with file:line references.

10. Independent QA review gate.

   Spawn a `qa_reviewer` subagent to assess test adequacy, naming/readability, and maintainability; require actionable findings with file:line references.

11. Resolve all findings.

   Apply fixes, rerun affected tests, and document each finding/resolution pair in `Decision Log` and `Outcomes & Retrospective`.

## Validation and Acceptance

Acceptance is complete when all conditions below are true:

- Parser compatibility:
  - Legacy `H*.element.dat` rows parse without error.
  - New rows containing appended `QRain`/`QSnow` parse without error.

- Data correctness:
  - `H.element.parquet` contains `QRain` and `QSnow` columns.
  - New-format source rows preserve numeric `QRain`/`QSnow` values.
  - Legacy source rows emit null `QRain`/`QSnow` values.

- Backward compatibility:
  - Existing legacy-element tests continue to pass.
  - No pre-existing required columns are removed or renamed.

- Review gates:
  - `reviewer` and `qa_reviewer` passes completed.
  - All findings either fixed or explicitly documented as accepted risk.

## Idempotence and Recovery

Edits in this plan are additive and repeatable. Re-running the parser/tests should produce stable results.

If schema/test changes fail mid-way:

- Revert only touched files for the failing milestone.
- Re-run the smallest relevant test set (`test_element_interchange.py`) before continuing.
- Re-apply minimal focused changes and avoid unrelated refactors.

## Artifacts and Notes

Capture concise evidence during implementation:

- Pre-change failure evidence: line with appended `QRain`/`QSnow` triggers trailing-payload parse failure in `_split_fixed_width_line`.
- Post-change success evidence: targeted test proving mixed legacy/new file ingestion.
- Schema evidence: updated `hill_element.json` includes `QRain`/`QSnow` fields and expected metadata.
- Review evidence: summarized findings from `reviewer` and `qa_reviewer` with exact resolutions.

## Interfaces and Dependencies

Expected interface outcomes:

- `hill_element_interchange.SCHEMA` includes:
  - `QRain: float64` (`units=mm`)
  - `QSnow: float64` (`units=mm`)
- `_parse_element_file(...)` accepts both legacy and extended element-row payloads.
- Rust-path conversion in `_parse_element_file_rust(...)` remains resilient when optional columns are absent.

No new third-party dependencies are permitted.

## Fresh Agent Prompt

Use this exact prompt for a fresh agent:

    Execute `/workdir/wepppy/docs/mini-work-packages/20260319_wepp_element_qrain_qsnow_interchange_execplan.md` end to end.

    Requirements:
    1. Keep the ExecPlan as a living document: update `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` as you work.
    2. Implement backward-compatible support for new `H*.element.dat` columns `QRain` and `QSnow` in WEPP interchange.
    3. Preserve legacy parsing for files without those columns.
    4. Add/adjust tests and schema snapshot(s) exactly as needed.
    5. Run validation commands listed in the plan and report results.
    6. Run an independent `reviewer` subagent pass, then a `qa_reviewer` pass.
    7. Resolve findings and re-run affected tests before finalizing.
    8. At handoff, provide:
       - changed file list,
       - key implementation decisions,
       - test command results,
       - review findings and resolutions,
       - residual risks (if any).
