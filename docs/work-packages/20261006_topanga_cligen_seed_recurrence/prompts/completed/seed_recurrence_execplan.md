# Execute Topanga seed recurrence study

Completed 2026-10-06: validated pilot and 100-seed inference; report and retained
evidence are in the WEPPpy investigation. Original-date Ksat recurrence 78%,
1986 cover/dense recurrence 0%; different dates remain frequent. All 20 selected
lane cases reproduce with source-checked branch operands. See tracker for
qualified quality warnings, unchanged-seed retries and diagnostic limitations.

This living ExecPlan follows WEPPpy docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture

Determine how often known Hill 106 peak anomalies recur when CLIGEN regenerates
subdaily storms over the same 1980–2024 daily record. Deliver actual event tables,
seed recurrence probabilities and manually reviewed mechanism evidence.

## Progress

- [x] (2026-10-06 UTC) Read the original audit, approved design and input manifests.
- [x] Recover pinned observer/replay and pass immutable original fixtures.
- [x] Reproduce climate, freeze 100 inference seeds and five pilot seeds.
- [x] Execute pilot and repeatability gate on openwepp compute.
- [x] Execute inference sample and reconcile all outputs.
- [x] Review representative events and prepare reproducible public conclusions.

## Surprises & Discoveries

The observer binary at the historical path no longer matches the accepted hash.
Frozen snapshots remain intact. The source run was changed by a later soil
experiment and must not replace frozen fixtures. CLI headers misstate record
length; parse dates. Local WEPPpy checkout predates observed-mode seed support;
forest HEAD 35cfc8ec5 includes that support but has unrelated dirty documents.

## Decision Log

2026-10-06: Preserve original fixture parameter pairs and separate them from
small-mutation census results. This measures recurrence of the already known
cases without silently changing their definition. Use forest for evidence/builds
and existing openwepp compute for simulation. No new services or dependencies.

## Outcomes & Retrospective

Original-fixture validation passes on forest and cluster. Cluster repeat is
byte-identical. The five-seed pilot and all 100 inference seeds passed final
artifact validation. Primary-date recurrence is 78%, 0%, 0% for Ksat, cover and
dense; any-date recurrence is 100%, 85%, 77%. The public investigation retains
confidence intervals, raw evidence identities and selected manual packets.
The package tracker records numerical host-parity bounds and the explicit
observed-variable quality-warning policy adopted before seeded WEPP execution.
Two inference seeds needed an explicitly recorded completion of the allowed
frozen-daily-variable name list; both reran unchanged. Historical replay's
pre-surplus remax assumption failed on five storm-only lane cases. A separate
source-checked operand replay matched all 20 reviewed lane cases exactly.
No model equations, production defaults, routing or small-mutation brackets
were changed. Remaining scientific generalization is follow-up, not unfinished
execution of this bounded sample.

## Context and Orientation

WEPPpy tools/peakflow_gate21_acceptance.py checks two Ksat lanes, three 1986
management lanes, active/inactive observer parity, immutable event packets,
isolated APPMTH/HDRIVE replay and inactive ksatfac negative control.
tools/peakflow_phase1_replay.py provides packetize/replay functions.
The replay driver is docs/work-packages/20260808_peakflow_phase1/artifacts/
peak_replay_driver.for. Observer source commit is
ea25ad79ef7dab20206bca095b2958786f5ae317 in forest's
/home/workdir/wepp-forest_260430_baseline repository. Never build in that dirty
worktree; export the pinned source into a new study directory.

## Plan of Work and Milestones

First export only required pinned source/build inputs and rebuild with existing
/usr/bin/gfortran. Capture make configuration and hashes. Execute acceptance
using new output directories and recorded build manifests; never overwrite the
old Phase 1 evidence. Exact binary hashes may depend on build paths/compiler;
any mismatch needs explicit provenance plus fixture numerical/packet and parity
validation, not relabeling as the old binary.

Next stage immutable ws.prn, ca041484.par and Hill 106 original climate. Rebuild
unseeded climate using the recorded CLIGEN version and -t6 -I2 arguments. Resolve
the spatial transformation from watershed climate to consumed p106.cli and
prove numerical equality for all records. Freeze each effective daily input;
seed variation must not alter dates or observed meteorology. Stop if this fails.

Generate five pilot climates and repeat seed 12345. Execute full 45-year histories
for each frozen pair, with observer diagnostics enabled. Read canonical outputs
and diagnostics; enforce identical climate within pairs and only intended
parameter differences. Review known dates and all-event flags. Continue to the
100-seed sample only after pilot invariants and repeatability pass.

For each seed and pair, outer-join date/OFE/solver ordinal. Compute existing
candidate flags with floors and track separate event presence. Estimate the
fraction of seeds flagged on each focal date and with any flag over the history.
Report 95% Wilson intervals, missing/failed counts, and precise conditioning.
Inspect persistence/loss/new cases with frozen packets and isolated replay.

## Concrete Steps

Create WEPPpy docs/work-packages/20261006_topanga_cligen_seed_recurrence and
docs/investigations/2026-10-06-topanga-cligen-seed-recurrence. Keep scripts in the
investigation directory and bulk evidence under a separately hashed study root.
Record every actual command and output location in tracker/artifact manifests
as targets are resolved. Run gate21 acceptance with --artifacts pointing to the
new study acceptance directory. Existing source projects remain read-only.

## Validation and Acceptance

Original fixture peaks and full-precision replay must pass. Date and observed
daily values must match across all seeds at the model-consumed path. Same-seed
repeat must match. Each seed must have complete fresh outputs and known binary
identity. Recompute counts from retained raw data; manual samples must support
mechanism claims. Validate documentation and scientific scripts proportionally;
no production code or deployment changes are part of this study.

## Idempotence and Recovery

Each seed/lane has an isolated directory and terminal manifest. Never silently
reuse partial results. Preserve failures and retry in a named new attempt.
Stop only study jobs/processes if invariants fail. Never mutate source archives,
shared builds, active user branches, or existing project data.

## Interfaces and Dependencies

Use existing CLIGEN binary, pinned WEPP observer, standalone Fortran replay,
WEPPpy Python tools, and installed scientific libraries. No new infrastructure.
The seed list and run manifests identify all exact inputs, outputs, executable
hashes, tool revisions, dates, lane definitions and retained evidence locations.
