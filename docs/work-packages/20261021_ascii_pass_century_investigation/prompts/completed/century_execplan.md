# Investigate the 200-year ASCII PASS watershed failure

This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Diagnose the reported post-century event shift and the explicit SOURCES3 date
mismatch in chemotherapeutic-scope. Deliver reproducible evidence and a bounded
repair recommendation. Scope is observation only, not implementation or release.

## Progress

- [x] (2026-10-21) Identify released binary and original year-102 guard stop.
- [x] (2026-10-21) Establish climate/PASS century day-count discrepancy.
- [x] (2026-10-21) Both isolated full-request replays reproduce exit 1/year 102.
- [x] (2026-10-21) Probe confirms requested (103,365), stored (102,365); all six release/probe outputs match and all 104 hill PASS inputs are unchanged. Original numerical parity is limited to master PASS and plot output.
- [x] (2026-10-21) Retain findings and robust repair design including CLIGEN, EOF and HBP policy compatibility.

## Surprises & Discoveries

The climate has 73,048 daily rows; H1, H104 and master PASS have 73,050.
Climate years 100 and 200 have 365 days; PASS has 366. The guard trips in
simulation year 102, rather than immediately at the first differing day.
Release/probe outputs are exact; four original numerical outputs differ already
in year 1 for an unresolved reason. Dates and guard failure remain reproducible.

## Decision Log

2026-10-21: User expanded the investigation to identify a robust fix and supplied
`/workdir/jimf-cligen532`. Recommend Gregorian execution, all-record date checks
and EOF validity tracking; retain the existing CLIGEN climate. Design is in
`artifacts/repair-design.md`; implementation remains outside this investigation.

2026-10-21: Use a new package because earlier routing and schema-2 fix packages
are closed. The user requested investigation of the ASCII release, which does
not use the binary reader corrected previously. Preserve the live project and
released binary. Probe only an isolated archive of the exact released source.

## Outcomes & Retrospective

Artifact audits diagnose the calendar mismatch and EOF buffer reuse. The proposed
repair includes all writers/readers and explicit compatibility, not only the
SOURCES3 guard. Runtime comparison reproduces the exact stop with byte-identical outputs.
Investigation is complete; no implementation or recovered-run claim.

## Context and Orientation

Source project: `/wc1/runs/ch/chemotherapeutic-scope`. The 104 hillslope ASCII
PASS files are `wepp/output/H*.pass.dat`; master is `pass_pw0.txt`. PASS means
saved daily hillslope fluxes consumed by watershed routing. SOURCES3 supplies
source-component data only for EVENT records. The crash is in `wepp/runs/pw0.err`.
Release `wepp_runner/bin/wepp_261010` has SHA256
`1dd1ca75cf53f9a0606cf5a598312d4e680e161df631156360d4a20dbcb6f17e`, native
source commit `7471bb5e981d14d0b8c1cdb88a16af305aed1b67` in
`/workdir/wepp-forest`. It uses ASCII components v3, with HBP disabled.

## Plan of Work

Milestone 1: retain provenance and stream-parse climate and all hillslope/master
PASS dates. Compare sequential dates across years 100 and 200, including event
records and watershed output labels. Acceptance is an exact first mismatch.

Milestone 2: use `wepppy.rq.project_rq_fork.prepare_fork_run` to create a complete
isolated project under `/workdir/wepp-century-investigation-20261021`.
Replay the unchanged released binary and full 200-year card. Preserve original
failed outputs before replay; compare generated output contents. Archive release
source and add only bounded date diagnostics around `mixreadmaster` if needed.
Acceptance is repeatable failure with exact expected/read date keys.

Milestone 3: retain concise evidence in `artifacts/`, source attribution and
repair criteria. No calendar-policy change, binary vendoring or deployment.

## Concrete Steps

Run `PYTHONPATH=/workdir/wepppy .venv/bin/python
/workdir/wepp-century-investigation-20261021/fork.py` from WEPPpy. Run the release
with `wepp_261010 < pw0.run` from the fork's `wepp/runs`, capturing stdout/stderr.
Inspect released files with `git -C /workdir/wepp-forest show 7471bb5:src/FILE`.
Use isolated archived source for rebuilds; never switch the native working tree.

## Validation and Acceptance

Require actual parsed artifact dates, unchanged input hashes, repeatable guard
failure from the full configured request, and explanation of delayed detection.
A failed 200-year request diagnoses failure but does not validate 200-year
completion. No physical closure or universal attribution of Jackson's separate
run without its inputs. Lint package Markdown with `wctl doc-lint --path`.

## Idempotence and Recovery

All writes are to this package and dedicated local investigation workspace.
Keep original artifacts separate from fresh outputs; never rerun into the live
project. Record the path of each attempt. No rollback of production is needed.

## Artifacts and Notes

Large artifacts stay in `/workdir/wepp-century-investigation-20261021`.
Commit-sized audit summaries and scripts belong in this package's `artifacts/`.

## Interfaces and Dependencies

Use existing fork helper, Python standard library, released binary, and native
Fortran make toolchain. No new dependencies or scientific formulas.

Revision: initial investigation plan, 2026-10-21.

Revision: completed runtime parity and robust repair design, 2026-10-21.
