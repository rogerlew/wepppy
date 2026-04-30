# Uncapped-Spectacular H2637 Ablation Campaign ExecPlan

**Status**: Completed (2026-04-30)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this campaign, investigators have lane-by-lane evidence for the `H2637` anomaly (1987 day 44 spike) and whether the behavior reproduces consistently across Linux and `wepppy-win-bootstrap.exe` on `blarhg`.

## Progress

- [x] (2026-04-30 19:10 UTC) Package scaffold created in `docs/work-packages/20260430_uncapped_spectacular_h2637_ablation_campaign/`.
- [x] (2026-04-30 19:10 UTC) Source snapshot staged from `wepp1` (`p2637.*` and `H2637.*.dat`) with manifest/checksums.
- [x] (2026-04-30 19:15 UTC) Documentation lint passed for campaign package docs and `PROJECT_TRACKER.md`.
- [x] (2026-04-30 19:27 UTC) Incident folder initialized in `/workdir/wepp-forest/docs/ablation/`.
- [x] (2026-04-30 19:29 UTC) Linux baseline replay lane (`C000`) executed with copied production binary `wepp_260429_hill`.
- [x] (2026-04-30 19:29 UTC) Linux historical comparator lane (`C010`) executed with `wepp_dcc52a6_hill`.
- [x] (2026-04-30 19:31 UTC) `blarhg` comparator inventory captured and Windows baseline lane (`C020`) executed with `wepppy-win-bootstrap.exe`.
- [x] (2026-04-30 19:41 UTC) Lane summaries generated and incident package finalized (`manifest_rows=88`, `checksummed_files=93`) after trimming redundant repro payloads to pass artifact-budget policy.
- [x] (2026-04-30 19:44 UTC) Evidence snapshot synced into package artifacts and package closure docs updated.

## Surprises & Discoveries

- Observation: Local `/wc1/runs/un/uncapped-spectacular` mount did not contain populated interchange outputs, while `wepp1` production path had full artifacts.
  Evidence: local `wepp/output` empty vs `wepp1:/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange` populated.

- Observation: Source day-44 spike reproduces only in the production-binary lineage lane (`C000`) and is absent in both comparator lanes (`C010`, `C020`).
  Evidence: `artifacts/incident_snapshot/lane_day44_legacy_closure.csv`.

## Decision Log

- Decision: Pull both run inputs and hillslope outputs during intake rather than only run inputs.
  Rationale: Avoid a second production fetch before lane execution; preserve full reproducibility context.
  Date/Author: 2026-04-30 / Codex.

- Decision: Treat `blarhg` Windows comparator as baseline lane requirement.
  Rationale: User explicitly requested parity validation against `wepppy-win-bootstrap.exe`.
  Date/Author: 2026-04-30 / Codex.

- Decision: Close this package as attribution-complete and defer routine-level root-cause isolation.
  Rationale: Lane matrix answered attribution questions; no in-scope source mutation was planned.
  Date/Author: 2026-04-30 / Codex.

## Outcomes & Retrospective

- Campaign objective met: reproducible lane evidence captured for Linux production binary, Linux historical comparator, and Windows bootstrap comparator.
- Key attribution outcome: day-44 legacy closure spike (`-180.31779 mm`) reproduces in source + `C000`, but not in comparator lanes `C010`/`C020`.
- Erin-check outcome: day-44 anomaly is confirmed; day-45 is near zero; dominant spike term is OFE 19 rather than OFE 14 in this replay/evaluation.
- Remaining work: isolate routine/state-level cause under `wepp_260429_hill` in follow-up package.

## Context and Orientation

Target run and hillslope:
- Run root (host): `wepp1:/geodata/wc1/runs/un/uncapped-spectacular`
- Hillslope: `H2637`

Comparator requirement:
- Windows binary host: `blarhg`
- binary path: `C:\src\wepppy-win-bootstrap\bin\wepppy-win-bootstrap.exe`

Incident execution package:
- `/workdir/wepp-forest/docs/ablation/20260430_uncapped-spectacular_h2637_hillslope_closure-spike/`

## Validation and Acceptance

Acceptance criteria for this package:
- [x] Source bundle staged with integrity records.
- [x] Linux baseline + one-change comparator lanes executed.
- [x] Required `blarhg` Windows comparator lane executed.
- [x] Lane matrix and incident docs finalized with evidence links.
- [x] Package artifacts include evaluation summary and incident snapshot for handoff.

## Artifacts and Notes

Package evidence snapshot:
- `docs/work-packages/20260430_uncapped_spectacular_h2637_ablation_campaign/artifacts/incident_snapshot/`

Package evaluation summary:
- `docs/work-packages/20260430_uncapped_spectacular_h2637_ablation_campaign/artifacts/evaluation_summary.md`

Incident canonical artifacts:
- `/workdir/wepp-forest/docs/ablation/20260430_uncapped-spectacular_h2637_hillslope_closure-spike/`
