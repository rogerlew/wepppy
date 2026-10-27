# Actual forest API/model baseline — RQ 1.16.2

Captured 2026-10-27 19:12–19:16 UTC on forest. This is pre-upgrade evidence only.

## Fixture and boundary

Source `/wc1/runs/rl/rlew-international-refuge`, configuration
`disturbed-wbt-profile`, 28 hillslopes, 11 channels, observed climate years
2000–2005. The source was preserved. Actual authenticated HTTPS fork submission
created `/wc1/runs/rq/rq212-20261027-baseline`; no ad hoc project copy was used.
`skip_wepp_runs_output=true` omitted inherited executable decks/output so fresh
execution could be distinguished. The disposable project is retained for paired
upgraded acceptance (36 MiB after baseline).

Authentication used the existing dev-agent account: materialize its server-side
Flask-Security session, then actual HTTP profile retrieval, CSRF-protected profile
token mint, and bearer-authenticated rq-engine requests through the forest HTTPS
proxy. Credentials/tokens/cookies are not retained in artifacts. This proves the
HTTP session/token/API boundary, not password-login/CAP interaction. Initial
read-only worker inspection found all 11 workers idle. Installed worker pools
executed every job; no SimpleWorker or mocked execution was used.

## Real failure and recovery

The first fork succeeded (`c86de069-19ed-444b-b2d5-794a014cf41c`). Initial run root
`d44c253c-3c29-42da-a3a9-1d28b767a4c1` reached `_prep_remaining_rq`, which rejected
the fixture's historical `wepp_250915` executable because its runtime provenance
check could not resolve libgfortran. This is an existing binary/fixture issue,
not an RQ migration regression; no break-glass bypass was used.

Through the ordinary run-wepp API, explicitly selected installed
`wepp_261026` for both sides of the planned comparison and resubmitted. Root
`aa023d14-9f19-4e7a-ae17-ae50dcdaa5bd` completed all 18 graph nodes, including
parallel input preparation, all 28 hillslope executions, strict downstream
watershed execution, parallel postprocessing and final completion/export.
The old graph's completed preparation was retained, failed prerequisite stayed
failed, and all 12 never-started strict descendants became canceled during
normal reconciliation. They were not released to consume missing output.

Evidence: `acceptance_baseline_initial_failure.json`,
`acceptance_baseline_obsolete_graph.json`, `acceptance_baseline.json`.

## Generated and user-facing readback

`acceptance_baseline_readback.json` reloads normal NoDb readers and records the
selected binary (`wepp_261026`), pass family (`legacy_ascii`), config and climate
mode. It inventories 184 consumed-input files with SHA256 and timestamps,
including all 28 hillslope run decks, referenced management/slope/climate/soil
names, six-year simulation count, climate headers and final records, and soil/
slope format headers. This reads the executable paths under `wepp/runs`.

All 25 fresh output Parquets were opened, with schemas, row counts and numeric
column counts/minima/maxima/sums retained. Representative semantics:

- `H.wat.parquet`: 61,376 rows, years 2000–2005 (28 hillslopes × 2,192 days).
- `loss_pw0.hill.parquet`: 28 hillslopes; `loss_pw0.chn.parquet`: 11 channels.
- `totalwatsed3.parquet` and watershed event output: 2,192 daily rows.
- Actual authenticated summary CSV retrieval returned HTTP 200 for outlet,
  hillslopes and channels, with 9, 29 and 12 rows including their headers.
- Outlet report: area 426.26 acre, precipitation 30.204 in/year, stream discharge
  4.069 in/year, sediment discharge 4.52 ton/year. These are paired acceptance
  reference values, not a scientific calibration claim.

CSV content is retained in `acceptance_baseline_{outlet,hillslopes,channels}.csv`.
The readback records UID 1000, GID 993 and supplementary groups; broader runtime
mount/image/worker identity evidence is in `baseline_environment.md`.

## Reproduction and remaining gate

Sanitized reproducible harnesses are retained alongside this record as
`acceptance_baseline_harness.py`, `acceptance_baseline_resubmit_harness.py`,
`acceptance_readback_harness.py` and `acceptance_upgraded_harness.py`.
They contain no credential, cookie or bearer values; these stay in process memory.
The corresponding temporary harnesses are `/tmp/rq212-acceptance/baseline.py` (initial fork/run),
`resubmit.py` (normal binary selection and failed-graph reconciliation),
`graph.py` (read-only old-graph status) and `readback.py` (semantic/readout checks).
Each executes with `wctl docker compose exec -T weppcloud /opt/venv/bin/python -`
using the file on stdin. No code/dependency/container upgrade occurred here.
Repeat the same API request and readback only after the rebuilt runtime is
verified as 2.12.0. Preserve this baseline evidence. Additional upgraded
cancellation/recovery and independent review gates remain open.
