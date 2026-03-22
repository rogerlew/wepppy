# Peridot Watershed Parquet + Manifest End-to-End Integration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, Peridot will directly emit watershed parquet files as first-class outputs and generate a `watershed/README.md` that documents run flags, output manifest details, and tabular schemas. WEPPpy will consume these parquet files directly for new runs, while old runs without parquet will follow an explicit legacy compatibility path rather than relying on hidden conversion behavior.

## Progress

- [x] (2026-03-21 00:00Z) Created work package scaffold and activated this ExecPlan.
- [x] (2026-03-21 20:18Z) Discover Peridot abstraction write paths, output schemas, and current tests.
- [x] (2026-03-21 20:18Z) Discover WEPPpy watershed integration path and mandatory CSV->parquet conversion callsites.
- [x] (2026-03-21 20:45Z) Implement Peridot parquet output writes in both abstraction flows.
- [x] (2026-03-21 20:45Z) Implement Peridot-generated `watershed/README.md` manifest/schema output with flag awareness.
- [x] (2026-03-21 20:50Z) Add/update Peridot Rust tests for parquet + README outputs.
- [x] (2026-03-21 20:57Z) Implement WEPPpy parquet-first integration for new runs with explicit legacy fallback.
- [x] (2026-03-21 21:00Z) Add/update WEPPpy pytest coverage for direct parquet + legacy behavior.
- [x] (2026-03-21 21:15Z) Run required validation (Rust tests, targeted pytest, real-run verification).
- [x] (2026-03-21 23:20Z) Run required subagent reviews (`reviewer`, `test_guardian`) and store artifacts.
- [x] (2026-03-21 23:45Z) Address review findings, rerun targeted validation, and close package docs.

## Surprises & Discoveries

- Observation: Query-engine catalog refresh currently rejects markdown files (`watershed/README.md`) as unsupported assets.
  Evidence: `post_abstract_watershed()` raised `ValueError: Unsupported asset type` when attempting `_update_catalog_entry(wd, "watershed/README.md")`; that call was removed.

- Observation: `Watershed.skip_flowpaths` is currently hardcoded to `True`, so representative real-run validation emitted channels/hillslopes only (no flowpaths table) by design.
  Evidence: `wepppy/nodb/core/watershed.py` `skip_flowpaths` property returns `True`; rerun on `/wc1/runs/un/unassailable-sensuousness` produced no `flowpaths.parquet` and README reported `skip_flowpaths=true`.

- Observation: Direct host Python execution for real-run orchestration lacked `utm`; containerized execution was required.
  Evidence: Module import failure on host (`ModuleNotFoundError: utm`) resolved by running scripts in compose `weppcloud` container.

- Observation: Requested run did not include WBT input `dem/wbt/subwta.tif`; Topaz abstraction path had to be used for verification.
  Evidence: `run_peridot_wbt_abstract_watershed` wait guard timed out for `/wc1/runs/un/unassailable-sensuousness/dem/wbt/subwta.tif`, while `/dem/topaz/SUBWTA.ARC` exists and succeeded.

## Decision Log

- Decision: Execute migration in two stages (Peridot producer first, WEPPpy consumer second) while preserving explicit legacy fallback.
  Rationale: Keeps behavior verifiable at each milestone and minimizes regression risk.
  Date/Author: 2026-03-21 / Codex.

- Decision: Keep CSV outputs in Peridot for compatibility during transition, but make parquet the first-class producer output.
  Rationale: Avoids breaking unknown CSV consumers while eliminating mandatory CSV->parquet conversion for new runs.
  Date/Author: 2026-03-21 / Codex.

- Decision: Make `post_abstract_watershed()` parquet-first with explicit warnings when CSV fallback is used.
  Rationale: Provides explicit old-run compatibility behavior without silently masking missing new artifacts.
  Date/Author: 2026-03-21 / Codex.

- Decision: Refresh `watershed/README.md` in WEPPpy after post-processing rewrites parquet outputs.
  Rationale: Prevents manifest/schema drift when WEPPpy adds derived columns (`wepp_id`, `chn_enum`) to canonical parquet tables.
  Date/Author: 2026-03-21 / Codex.

- Decision: Move flowpaths parquet export out of the Peridot parallel output task pool.
  Rationale: Reduces avoidable peak-memory/IO contention while preserving output behavior.
  Date/Author: 2026-03-21 / Codex.

## Outcomes & Retrospective

Completed. Peridot now emits first-class watershed parquet outputs and a flag-aware manifest README in both abstraction binaries; WEPPpy consumes parquet-first for new runs, retains explicit legacy CSV fallback/migration behavior, and refreshes README manifest/schema after post-processing so final contracts remain aligned on disk.

Subagent findings were addressed with additional code and tests. Residual accepted risk is low: very large flowpath-enabled exports still build one in-memory parquet batch (`write_subflows_metadata_to_parquet`), now serialized outside the parallel pool.

## Context and Orientation

This task spans two repositories:

- `/workdir/peridot` (Rust): watershed abstraction producers (`abstract_watershed` and `wbt_abstract_watershed`) need direct parquet writes and README manifest generation.
- `/workdir/wepppy` (Python): watershed integration currently includes CSV->parquet conversion behavior that must no longer be mandatory for new runs.

Key acceptance outcomes:

- New runs produce `watershed/hillslopes.parquet`, `watershed/channels.parquet`, and optional `watershed/flowpaths.parquet` directly from Peridot.
- `watershed/README.md` is generated by Peridot and contains executed flags, output manifest (format/size/rows where applicable), and schema summaries.
- WEPPpy reads Peridot parquet directly and keeps explicit old-run compatibility behavior when parquet is absent.

## Plan of Work

Milestone 1 establishes current producers/consumers and exact schema contracts. Milestone 2 updates Peridot write pipelines to emit parquet-first outputs and README metadata in both abstraction paths, then adds Rust regression tests validating content and conditional outputs. Milestone 3 updates WEPPpy ingestion so new runs use Peridot parquet directly and old runs use clearly gated fallback behavior, followed by pytest coverage for both paths. Milestone 4 performs required runtime validation on `/wc1/runs/un/unassailable-sensuousness`, executes subagent correctness/coverage reviews, addresses findings, and closes package artifacts/docs.

## Concrete Steps

From `/workdir/peridot`:

1. Locate abstraction functions and output writers.
2. Implement parquet write calls and README manifest generation.
3. Add/extend tests for output files, schemas, and conditional flowpath handling.
4. Run targeted Rust tests (`cargo test ...`).

From `/workdir/wepppy`:

1. Locate Peridot abstraction integration and CSV->parquet conversion callsites.
2. Make parquet-first path primary for new runs; keep explicit legacy fallback path.
3. Add pytest coverage for direct parquet and legacy behavior.
4. Run targeted tests with `wctl run-pytest`.

Runtime validation:

1. Re-run required abstraction path(s) on `/wc1/runs/un/unassailable-sensuousness`.
2. Verify parquet files and generated `watershed/README.md`.
3. Perform slope sanity check versus `wepp/runs/p*.slp` profile magnitudes.

## Validation and Acceptance

Acceptance requires all of the following:

- Peridot writes complete parquet outputs in both abstraction paths.
- Peridot writes `watershed/README.md` with correct flags, manifest, schema summary, and conditional notes.
- WEPPpy uses direct parquet path for new runs.
- Explicit legacy fallback for old runs lacking parquet remains functional and tested.
- Rust tests and targeted pytest commands pass.
- Real-run verification confirms expected files and reasonable slope/profile sanity.
- Review artifacts from `reviewer` and `test_guardian` are captured and addressed.

## Idempotence and Recovery

Changes are additive and retry-safe: rerunning abstraction should overwrite output artifacts in the run-scoped `watershed/` directory without affecting unrelated runs. Legacy behavior is preserved explicitly so old runs remain operable if new parquet outputs are missing.

## Artifacts and Notes

Artifacts will be written under:

- `docs/work-packages/20260321_peridot_watershed_parquet_manifest/artifacts/`

Planned artifacts:

- `reviewer_findings.md`
- `test_guardian_findings.md`
- `validation_summary.md`

## Interfaces and Dependencies

Peridot producer contracts to deliver:

- `watershed/hillslopes.parquet`
- `watershed/channels.parquet`
- `watershed/flowpaths.parquet` (when flowpaths enabled)
- `watershed/README.md`

WEPPpy consumer contract:

- Prefer parquet artifacts from Peridot for new runs.
- If parquet missing, take explicit legacy compatibility branch and document in code/tests.

---
Revision Note (2026-03-21, Codex): Plan completed; ready to archive under `prompts/completed/`.
