# hillslope_daily_closure_audit Tool (single hillslope; MOFE + single OFE)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, analysts can run a repeatable daily closure audit for one hillslope directly from interchange artifacts (`H.wat`, `H.pass`, optional `H.soil`, `H.element`) instead of relying only on watershed-level `totalwatsed3` audits. The tool will support both `wepp_id` and `topaz_id`, will preserve MOFE-correct aggregation behavior, and will emit summary/top-day artifacts aligned with existing closure-audit conventions.

Observable outcomes:
- `tools/hillslope_daily_closure_audit.py` exists and runs from CLI,
- tests validate single-OFE and MOFE closure behavior,
- evaluation artifacts exist for representative MOFE and single-OFE hillslopes,
- independent review findings are dispositioned.

## Progress

- [x] (2026-04-30 08:18 UTC) ExecPlan authored and linked to package tracker.
- [x] (2026-04-30 10:31 UTC) Implemented `tools/hillslope_daily_closure_audit.py` CLI, selector contract, hillslope aggregation, and closure outputs.
- [x] (2026-04-30 10:43 UTC) Added regression tests in `tests/tools/test_hillslope_daily_closure_audit.py` (single OFE, MOFE, selector/CLI, invalid selector combination).
- [x] (2026-04-30 10:57 UTC) Ran exemplar evaluations and saved artifacts for MOFE and single-OFE hillslopes.
- [x] (2026-04-30 11:06 UTC) Completed independent review, applied finding fixes, and recorded disposition.

## Surprises & Discoveries

- Observation: MOFE exemplar hillslopes in `uninsured-deformation` (`H78`, `H43`, `H97`) had zero runoff throughout the run in recorded PASS-derived runoff depth.
  Evidence: `artifacts/uninsured_deformation_H*/hillslope_daily_closure_audit_summary.json` (`max_reported_runoff_mm=0`).

- Observation: single-OFE exemplars in `bovine-clipboard` show expected non-zero runoff, including high daily `runoff/precip` ratios when precipitation is near zero.
  Evidence: `artifacts/bovine_clipboard_H*/hillslope_daily_closure_audit_summary.json`.

## Decision Log

- Decision: Mirror closure semantics and naming from `totalwatsed3_daily_closure_audit.py` (primary precipitation basis plus rain+melt diagnostic basis).
  Rationale: Maintains comparability and avoids introducing competing closure definitions.
  Date/Author: 2026-04-30 / Codex.

- Decision: Real-run evaluation must include both MOFE (`uninsured-deformation`) and single-OFE (`bovine-clipboard`) hillslopes.
  Rationale: Stakeholder requirement and direct process contrast.
  Date/Author: 2026-04-30 / Codex.

## Outcomes & Retrospective

Delivered tool + tests + evaluation artifacts.

- Added `tools/hillslope_daily_closure_audit.py` with:
  - `--wepp-id` / `--topaz-id` selector contract,
  - MOFE outlet-only lateral-flow accounting,
  - PASS `runvol` runoff basis,
  - optional `TSMF` + `QRain`/`QSnow` diagnostics,
  - repeatable summary/top-day outputs.
- Added `tests/tools/test_hillslope_daily_closure_audit.py` (5 tests).
- Produced evaluation artifacts for 6 exemplars plus topaz-selector verification and consolidated summary (`artifacts/evaluation_summary.{md,csv}`).
- Independent review findings dispositioned in `artifacts/20260430_code_review_disposition.md`.

## Context and Orientation

Relevant files and modules:
- Baseline closure logic: `tools/totalwatsed3_daily_closure_audit.py`
- Hillslope interchange readers/schemas:
  - `wepppy/wepp/interchange/hill_wat_interchange.py`
  - `wepppy/wepp/interchange/hill_pass_interchange.py`
  - `wepppy/wepp/interchange/hill_soil_interchange.py`
  - `wepppy/wepp/interchange/hill_element_interchange.py`
- Reference MOFE handling patterns: `wepppy/wepp/interchange/totalwatsed3.py`
- Topaz/wepp mapping API: `wepppy/nodb/core/watershed.py` via `Watershed.getInstance(...).translator_factory()`

Run roots and exemplar hillslopes:
- MOFE: `/wc1/runs/un/uninsured-deformation`
  - `wepp_id` {78, 43, 97} / `topaz_id` {341, 201, 411}
- Single OFE: `/wc1/runs/bo/bovine-clipboard`
  - `wepp_id` {1, 2, 3} / `topaz_id` {22, 23, 31}

## Plan of Work

Milestone 1 builds the tool skeleton and selector contract. Add a new CLI tool at `tools/hillslope_daily_closure_audit.py` with required run path arguments and mutually exclusive selector options (`--wepp-id` and `--topaz-id`). Implement translator-backed `topaz_id` resolution against run root.

Milestone 2 ports and narrows closure arithmetic from watershed to single-hillslope scope. Compute reported and reconstructed depth terms from the selected hillslope rows. Preserve MOFE behavior by aggregating across OFEs with outlet-OFE-only lateral-flow handling and PASS `runvol` runoff basis. Keep optional terms null-safe.

Milestone 3 adds tests. Introduce synthetic fixtures in `tests/tools/test_hillslope_daily_closure_audit.py` that validate single-OFE closure, MOFE closure, selector logic, and output artifact generation.

Milestone 4 runs exemplar evaluations and captures artifacts. Execute tool runs for the defined MOFE/single-OFE exemplar sets and store outputs under this package `artifacts/`.

Milestone 5 performs independent review and disposition. Dispatch reviewer, address or explicitly disposition findings, rerun affected tests, and update package tracker.

## Concrete Steps

Working directory: `/workdir/wepppy`

1. Implement tool skeleton and selector contract.

    rg -n "compute_daily_audit|build_summary|parse_args" tools/totalwatsed3_daily_closure_audit.py
    $EDITOR tools/hillslope_daily_closure_audit.py

2. Implement hillslope aggregation + closure calculations.

    rg -n "latqcc|runvol|_safe_depth|_resolve_ofe_column" wepppy/wepp/interchange/totalwatsed3.py
    rg -n "SoilWaterTotal|ProfileDepth|ProfilePorosityCap|ProfileFCStore|ProfileWPStore|TSMF|QRain|QSnow" tools/hillslope_daily_closure_audit.py

3. Implement tests.

    $EDITOR tests/tools/test_hillslope_daily_closure_audit.py
    wctl run-pytest tests/tools/test_hillslope_daily_closure_audit.py --maxfail=1

4. Regression guard on existing watershed audit tool.

    wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py --maxfail=1

5. Real-run evaluation and artifacts.

    wctl run-python tools/hillslope_daily_closure_audit.py /wc1/runs/un/uninsured-deformation/wepp/output/interchange --wepp-id 78 --output-dir docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/uninsured_deformation_H78
    wctl run-python tools/hillslope_daily_closure_audit.py /wc1/runs/un/uninsured-deformation/wepp/output/interchange --wepp-id 43 --output-dir docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/uninsured_deformation_H43
    wctl run-python tools/hillslope_daily_closure_audit.py /wc1/runs/un/uninsured-deformation/wepp/output/interchange --wepp-id 97 --output-dir docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/uninsured_deformation_H97

    wctl run-python tools/hillslope_daily_closure_audit.py /wc1/runs/bo/bovine-clipboard/wepp/output/interchange --wepp-id 1 --output-dir docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/bovine_clipboard_H1
    wctl run-python tools/hillslope_daily_closure_audit.py /wc1/runs/bo/bovine-clipboard/wepp/output/interchange --wepp-id 2 --output-dir docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/bovine_clipboard_H2
    wctl run-python tools/hillslope_daily_closure_audit.py /wc1/runs/bo/bovine-clipboard/wepp/output/interchange --wepp-id 3 --output-dir docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/bovine_clipboard_H3

6. Code review and disposition.

    (Dispatch reviewer agent on diff; record findings + disposition in package tracker/artifact.)

## Validation and Acceptance

Acceptance requires all of the following:
- Tool works with either `--wepp-id` or `--topaz-id` and rejects invalid selector combinations.
- MOFE case confirms outlet-OFE lateral-flow handling in computed closure terms.
- CLI writes both `hillslope_daily_closure_audit_summary.json` and `hillslope_daily_closure_audit_top_days.csv`.
- Unit tests pass for synthetic single-OFE and MOFE scenarios.
- Existing watershed-level audit tests remain green.
- Artifact evidence captured for all six exemplar hillslopes.
- Independent review completed with explicit dispositions.

## Idempotence and Recovery

- Tool runs are read-only against run interchange inputs; repeated runs overwrite or refresh output artifacts only.
- If `topaz_id` mapping fails, operator can rerun with explicit `wepp_id`.
- If optional columns are absent (legacy producers), tool must still run with null-safe diagnostics.

## Artifacts and Notes

Expected artifact layout:
- `docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/<run>_H<wepp_id>/hillslope_daily_closure_audit_summary.json`
- `docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/<run>_H<wepp_id>/hillslope_daily_closure_audit_top_days.csv`
- `docs/work-packages/20260430_hillslope_daily_closure_audit/artifacts/<date>_code_review.md` (review findings + disposition)

## Interfaces and Dependencies

Required interface at completion:
- `tools/hillslope_daily_closure_audit.py` CLI:
  - positional `interchange_dir`
  - one selector (`--wepp-id` or `--topaz-id`)
  - optional `--output-dir`, `--top-n`
- Summary contract includes closure-basis labels matching watershed tool semantics.
- Uses local mounted run data under `/wc1/runs/...`.

## Revision Notes

- 2026-04-30 / Codex: Initial ExecPlan authored for hillslope-level closure-audit tool delivery, tests, exemplar evaluation, and review disposition.
