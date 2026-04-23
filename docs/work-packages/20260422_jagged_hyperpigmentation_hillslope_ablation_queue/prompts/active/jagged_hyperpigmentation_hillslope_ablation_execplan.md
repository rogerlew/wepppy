# Jagged Hyperpigmentation Hillslope Ablation (`H3507` + `H1271`)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `/workdir/wepppy/docs/prompt_templates/codex_exec_plans.md` and operational ablation standards in `/workdir/wepp-forest/docs/ablation/README.md` and `/workdir/wepp-forest/docs/ablation/protocol.md`.

## Purpose / Big Picture

Queue and execute a focused ablation investigation for run `jagged-hyperpigmentation/disturbed9002-10-mofe` where hillslopes `H3507` and `H1271` show abrupt `element.dat` anomalies (`*******`) and dominate outlet sediment yield. After this plan is executed, we will have a reproducible incident package with baseline signatures, lane-by-lane outcomes, and an evidence-backed recommendation for next action.

## Progress

- [x] (2026-04-22 20:35 UTC) Intake captured and queue package scaffolded in `wepppy` docs.
- [x] (2026-04-22 20:39 UTC) Confirmed source artifact root on wepp1: `/geodata/wc1/runs/ja/jagged-hyperpigmentation`.
- [x] (2026-04-22 20:41 UTC) Initialized incident directory under `/workdir/wepp-forest/docs/ablation/`.
- [x] (2026-04-22 20:43 UTC) Copied immutable source evidence and built runnable staged replay workspace.
- [x] (2026-04-22 20:43 UTC) Executed baseline local replays (`p1271`, `p3507`) and captured logs.
- [ ] Execute observe-only lane(s) for source-signature windows.
- [ ] Execute first hypothesis lane set (single change group per lane) and classify outcomes.
- [ ] Finalize recommendation after causal attribution evidence is complete.

## Surprises & Discoveries

- Observation: The target run directory is not visible in local `/wc1/runs` on this workspace.
  Evidence: `find /wc1/runs -maxdepth 3 -type d -name 'jagged-hyperpigmentation'` returned no matches on 2026-04-22.
- Observation: Source root initially provided without `/runs/` segment.
  Evidence: Direct path checks failed until corrected to `/geodata/wc1/runs/ja/jagged-hyperpigmentation`.
- Observation: Source snapshot contains starred signatures while isolated staged replays do not.
  Evidence: `C099` log has matches for `*******`; `C100` staged scan log is empty.

## Decision Log

- Decision: Create queue package immediately instead of waiting for campaign slot availability.
  Rationale: Avoid re-scoping delay and preserve context from Marta's report while details are fresh.
  Date/Author: 2026-04-22 / Codex.

- Decision: Limit first ablation pass to `H3507` and `H1271`.
  Rationale: Reported issue is localized to these two hillslopes; narrow scope keeps attribution deterministic.
  Date/Author: 2026-04-22 / Codex.

- Decision: Perform artifact staging immediately when requested, before hypothesis lanes.
  Rationale: Makes next-lane execution ready without additional setup handoff.
  Date/Author: 2026-04-22 / Codex.

## Outcomes & Retrospective

Staging milestone complete: incident package is execution-ready with source snapshot, runnable staged inputs, baseline replay logs, and finalized manifest/checksums. Root-cause attribution remains open.

## Context and Orientation

The source report points to:
- URL: `https://wepp.cloud/weppcloud/runs/jagged-hyperpigmentation/disturbed9002-10-mofe`
- Anomaly: abrupt rows in `element.dat` for hillslopes `H3507` and `H1271` containing starred numeric fields.
- Confirmed source root on wepp1: `/geodata/wc1/runs/ja/jagged-hyperpigmentation`.

Ablation operations and canonical incident artifacts are maintained in `/workdir/wepp-forest`, not in `wepppy`.

Key execution docs/tools:
- `/workdir/wepp-forest/docs/ablation/README.md`
- `/workdir/wepp-forest/docs/ablation/protocol.md`
- `/workdir/wepp-forest/tools/ablation_protocol.py`
- `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/`

## Plan of Work

Milestone 1 (complete) established reproducible evidence: source artifacts copied from wepp1 into incident storage and runnable local staging prepared. Milestone 2 (next) adds observe-only lanes around source-signature windows. Milestone 3 runs one-change-per-lane hypotheses and records keep/rollback decisions. Milestone 4 finalizes recommendation and handoff.

## Concrete Steps

From `/workdir/wepp-forest`:

    incident_id="20260422_jagged-hyperpigmentation_hillslope_elementdat-stars"

Incident already initialized and finalized once for staging. For next lane cycle:

    cd docs/ablation/${incident_id}/artifacts/repro/staged/runs
    /workdir/wepp-forest/src/wepp_hill < p1271.run > ../logs/C1xx_p1271_<lane>.stdout.txt 2> ../logs/C1xx_p1271_<lane>.stderr.txt
    /workdir/wepp-forest/src/wepp_hill < p3507.run > ../logs/C1yy_p3507_<lane>.stdout.txt 2> ../logs/C1yy_p3507_<lane>.stderr.txt

After each lane set:

    cd /workdir/wepp-forest
    python tools/ablation_protocol.py finalize --incident-id "${incident_id}"

## Validation and Acceptance

Acceptance for execution readiness is met when:
- Incident package exists with source snapshot and runnable staged inputs.
- Baseline lane logs exist for both target hillslopes.
- Manifest and checksums are regenerated.

Final acceptance requires at least one hypothesis lane with clear keep/rollback outcome and explicit recommendation.

## Idempotence and Recovery

`tools/ablation_protocol.py init` can be rerun with `--force` only when intentionally resetting templates. Source snapshot remains immutable under `artifacts/repro/source_wepp1`; all lane mutations should occur only in `artifacts/repro/staged`. Preserve negative-result logs and roll back no-effect behavioral edits.

## Artifacts and Notes

Primary output locations:
- `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/incident.md`
- `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/notes.md`
- `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/matrix.csv`
- `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/artifacts/`

## Interfaces and Dependencies

Required interfaces and tools:
- `python tools/ablation_protocol.py init|finalize` for incident lifecycle.
- Stable lane contract fields from `TEMPLATE_matrix.csv` (`lane_id`, `case_id`, `pass_fail`, signature metadata, artifact paths).
- Existing WEPP binary used by campaign lanes (`/workdir/wepp-forest/src/wepp_hill`).
