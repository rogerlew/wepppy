# Investigate roads lateral flow and water-depth inflation


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes &
Retrospective together with the package tracker.

## Purpose / Big Picture


Explain why Marta Basso's UM1 roads output reports zero lateral flow and very
large runoff/baseflow. The deliverable is a reproducible diagnosis and a bounded
repair proposal, preserving the original run for subsequent validation.

## Progress


- [x] (2026-10-22 20:05 UTC) Open investigation and reproduce artifact symptom on forest.
- [x] (2026-10-22 20:05 UTC) Capture hashed inputs and annual totals.
- [x] (2026-10-22 UTC) Trace raw assembly and native aggregation.
- [x] (2026-10-22 UTC) Validate the causal hypothesis on scratch inputs.
- [x] (2026-10-22 UTC) Complete diagnosis and repair recommendation.

## Surprises & Discoveries


Roads WAT includes only 34 road segments with zero lateral volume, while roads
PASS includes 66 baseline hillslopes plus 34 segments. Totalwatsed uses
4,127.15 m² instead of baseline 441,820.29 m². These observations explain where
to investigate; they do not yet establish the entire causal chain.

## Decision Log


2026-10-22 20:05 UTC / Codex: Preserve the synced run and begin with input
population selection. Roger requested opening an investigation; untested
formula changes or in-place regeneration would destroy useful evidence.

## Outcomes & Retrospective


Investigation opened and initial mismatch retained. Full diagnosis, scratch
replay, repair implementation, and deployment remain outstanding. The initial
comparison demonstrates why populated output files alone do not prove correct
water accounting.

## Context and Orientation


Forest run root is `/wc1/runs/cl/clogging-starch`; source was
`wepp1:/geodata/wc1/runs/cl/clogging-starch/`. Project name is UM1, scenario
reference, configuration disturbed9002-wbt-mofe. Baseline outputs reside in
`wepp/output`; roads outputs reside in `wepp/roads/output`. Each has an
`interchange` directory containing Parquet tables. WAT records water balance;
PASS carries hillslope contributions to routing. `wepp_id` identifies a
hillslope or synthetic road segment. Raw WAT `latqcc` is local lateral depth; aggregated totalwatsed `latqcc` is volume (m³);
`Lateral Flow`, `Runoff`, and `Baseflow` are depths (mm). `Area` is m².

Roads orchestration is `wepppy/nodb/mods/roads/roads.py`; inspect workspace
preparation, hillslope PASS composition, and `_regenerate_roads_report_resources`.
`wepppy/wepp/interchange/totalwatsed3.py::run_totalwatsed3` passes H.pass and
H.wat to native `wepppyo3` aggregation. Locate that implementation in the local
wepppyo3 checkout and record its revision before drawing formula conclusions.
Read nearest AGENTS and the output-scope and hillslope-water aggregation
contracts before any proposed edits.

## Plan of Work


Milestone 1 captures the original symptom. It is complete: the retained JSON
contains six input hashes, populations, area extrema, and all annual totals.

Milestone 2 traces assembly. Compare raw H*.wat.dat and H*.pass.dat inventories
with their interchange IDs, inspect roads.nodb settings and roads.log, and
follow baseline PASS copying/augmentation into target hillslope files. Locate
where baseline WAT is included or omitted. Trace native PASS sums, WAT area
selection, lateral flow, percolation, and baseflow initialization. Record code
locations and concrete daily examples. Acceptance is an explanation of the
first incorrect boundary, with alternatives such as stale outputs distinguished
from current source behavior.

Milestone 3 tests causality without changing source evidence. Copy only required
inputs to a separate scratch workspace, record dependency versions, and exercise
the existing aggregation boundary with justified input populations. Compare
all 16 annual totals and selected daily values. Check segment overlap separately
from missing baseline WAT; do not claim simply adding WAT fixes double counting.
Preserve baseline hashes. Acceptance is a falsifiable explanation of both zero
lateral flow and inflated depths, plus a minimal repair and regression proposal.
No implementation or production rollout is part of this plan.

## Concrete Steps


From `/workdir/wepppy`, repeat the read-only inventory with:

    .venv/bin/python docs/work-packages/20261022_roads_lateral_flow_investigation/artifacts/inspect_inputs.py /wc1/runs/cl/clogging-starch

Expect 5,844 totalwatsed rows in each scope, 34 roads WAT IDs, and 100 roads
PASS IDs. Retain new replay results separately from initial-inputs.json.
Inspect the source with:

    rg -n 'run_totalwatsed3|_prepare_roads_output_workspace|pass_relpath|baseline_output' wepppy/nodb/mods/roads/roads.py

Record exact scratch replay commands and environments in a new artifact before
marking milestone 3 complete; no invocation should write into the synced run.

## Validation and Acceptance


The final diagnosis must explain the reported lateral flow and the runoff and
baseflow anomalies using semantic artifact contents, physical units, and
contributing IDs. Separate confirmed observations from hypotheses. Any proposed
repair must include absent/empty inputs, ordinary and road IDs, overlapping
contributions, baseline isolation, and area normalization regression cases.
Documentation changes require scoped `wctl doc-lint`; production test suites
are required only if a later authorized implementation changes runtime code.

## Idempotence and Recovery


Inventory reads are repeatable. Store replay outputs in distinct scratch paths
and verify source hashes afterward. Never regenerate reports in the retained
run or edit production. A scratch replay can be discarded and reconstructed
from the hashed originals.

## Artifacts and Notes


Initial evidence is `artifacts/initial-inputs.json`, with reproducible reader
`artifacts/inspect_inputs.py` relative to the package root. Calendar-year 2001
baseline/roads lateral totals are 1021.097540/0 mm; runoff is
183.022941/20082.365246 mm; baseflow is 60.107896/1273.251164 mm.

## Interfaces and Dependencies


Use installed PyArrow for bounded incident inspection and the existing native
interchange API for any replay. Do not introduce a Python replacement for
production aggregation. No new dependencies or schema changes are authorized.

Revision note: 2026-10-22 — created from Roger's investigation request and
forest artifact readback; diagnosis remains open.

## Completion — 2026-10-22 UTC

Diagnosis and repair recommendation are complete in `../../diagnosis.md` relative
to this plan. The four native replays confirm missing baseline WAT, runoff area
mismatch, and duplicate standalone segment contributions. Original roads water
metrics reproduce exactly, and all source hashes remain unchanged. Baseflow
inflation comes from road-only percolation rather than PASS duplication.

Decision: retain replay candidates as diagnostics only; the follow-up repair
must specify additive road water accounting and replacement WAT selection.
No repair is implemented. Earlier open-diagnosis statements are historical
checkpoints superseded by this completion entry.
