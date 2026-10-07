# Execute the warming-championship roughness experiment

Completed 2026-10-06. This execution record follows
docs/prompt_templates/codex_exec_plans.md and is retained as immutable history.

## Purpose / Big Picture

Measure how changing initial random surface roughness affects runoff timing,
volume, and outlet peaks, independently of the repaired surface-return defect.
The user selected warming-championship on forest and only its 10 cm overland
flow elements (OFEs: successive sections of a modeled hillslope).

## Progress

- [x] (2026-10-06 UTC) Verified input inventory and candidate binary hashes.
- [x] Stage and semantically validate three isolated scenarios.
- [x] Complete 864 baseline hillslope executions without failures.
- [x] Execute full-history hillslopes, watersheds, and output-mode parity.
- [x] Analyze and visually inspect figures; retain evidence and close package.

## Surprises & Discoveries

The run title is Cedar Creek, configured portland-10-mofe, not a forest-wide
uniform-management example. There are 864 hillslopes, 1,904 initial conditions,
1,885 at 0.10 m, two at 0.06 m, and 17 at 0.008 m. Preserve those 19 exceptions.
Original chan.inp requests daily peaks at a 600-second routing timestep.

Staging readback caught a residue-index selector limited to 1–3, which omitted
OFE 4; it was corrected before modeling, tested, and both staging-only attempts
retained separately. All three final cases pass semantic and byte-level checks.
Outlet sensitivity is small. Integrated printed hydrographs are about 1.3%
below the reported volume ledger in every case; this separate consistency issue
was quantified and retained, not corrected or normalized away.

## Decision Log

2026-10-06: Use corrected binaries for all cases to isolate roughness effects.
The user accepted proceeding after this recommendation. Do not change source
rrinit defaults or the original run. Alter only rrinit tokens in initial records,
not whole management-file serialization, to avoid unrelated formatting changes.
Request output mode 3 with the original timestep and outlet selection, and prove
this observer change leaves canonical outputs byte-identical in a baseline replay.

## Context and Orientation

Source executable inputs: forest:/wc1/runs/wa/warming-championship/wepp/runs.
New evidence root: forest:/workdir/warming-rrinit-20261006.
Binary root: /workdir/wepp-forest-holdouts/20261006-surface-return.6SeF9A/candidate/src.
wepp SHA256: 49a3e6cf199fa68388b76736caa82937e487ee894aaac46a1032845fa407a32c.
wepp_hill SHA256: 440fcebbeb2c51c2da46e258a53dce7ad609b783551ee2f5a6b1e18b368b2307.
Python runtime: /workdir/wepppy/.venv/bin/python. Local package is
docs/work-packages/20261006_warming_rrinit in /Users/roger/src/wepppy.

## Plan of Work and Concrete Steps

Create artifacts/run_experiment.py, copy it to forest, run its tests, then run
it with the trusted fixed source and destination paths above. It must refuse to
overwrite an existing experiment root. Snapshot input files with content hashes,
validate the rrinit parser against the existing read_management parser, then
make three cases rr10, rr17, rr60. Only rrinit tokens originally equal to 0.1 m
may change. Hash other files for equality. Preserve chan.inp's other tokens.

Execute each hillslope using wepp_hill and its pN.run input, with bounded two-job
concurrency, then execute pw0.run using wepp. Run files already reference relative
../output paths. Fresh output directories preclude stale pass-file reuse. Record
return codes and SIMULATION SUCCESSFULLY markers; retain logs on every attempt.
Use a baseline watershed replay with original chan.inp to test output parity.
Analyze fresh chan.out and ebe_pw0.txt, mapping model years to climate dates only
after verifying output conventions. Produce full-period daily comparisons,
selected multi-day hydrographs, and distribution/timing comparison figures.

## Validation and Acceptance

Test token mutation for 0.1 versus 0.06/0.008 and exact restoration; use the real
management parser to verify every consumed initial value in all three cases.
Require 864 successes per case plus watershed success, source manifest equality
before/after, no unintended input differences, and parity of canonical watershed
results across output modes. Validate finite hydrographs and full date coverage.
Figures must identify selection criteria, units, and the corrected-build scope.

## Idempotence and Recovery

Never overwrite the source. New experiment root must not exist at initial staging.
Retain failed attempts. Restart only an explicitly identified incomplete phase
with fresh output locations or validated successful terminal records. No cleanup
of unrelated files or processes. No deployment, commits, or stakeholder messages.

## Artifacts and Notes

Keep manifests, status, mutation records, and execution summaries on forest and
copy compact evidence plus figures to local artifacts. Large pass files and raw
model outputs stay on forest with exact paths documented in final results.

## Interfaces and Dependencies

Use standard-library pathlib, hashlib, subprocess, concurrent.futures, json and
existing wepppy management parser, numpy/pandas/matplotlib for analysis. No new
dependencies. This research script does not alter production APIs or defaults.

## Outcomes & Retrospective

All 2,592 hillslope runs, three scenario watershed runs, and the output-mode
control passed. All seven canonical watershed outputs match across output modes.
The 14 untouched hillslopes retain identical output sets. Original source and
consumed input hashes remain unchanged; no stderr errors or warning signatures
were found. See artifacts/results.md and artifacts/validation-review.md.

Maximum daily peak changes are -0.67153% and -0.91322% for 17 and 60 cm; total
reported runoff changes are -0.01098% and -0.02106%. Only two and three days,
respectively, have peak changes over 1%. Selected-event timing shifts are not
resolved beyond retained output precision. Figures and compact evidence are
local; raw outputs and a matching report bundle remain on forest under the
evidence root. No production default or original user run was changed.

The experiment is complete, but the hydrograph-integral/volume-ledger discrepancy
is unresolved and limits conservation claims. This is not a release-validation
claim or a finding that 17 or 60 cm roughness is physically justified.

Final revision: closed after actual execution, input-isolation, observer parity,
numerical-readback, and visual checks; retained the newly observed volume caveat.
