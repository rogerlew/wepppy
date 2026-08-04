# Operator-only: WEPPcloudR HTML rendering (Plumber)

WEPPcloudR is a containerized Plumber API that renders WEPPcloud HTML reports (R Markdown) using the run’s interchange parquet assets.

Do not use this reference for normal WEPPcloud web users.

## When to use

Use WEPPcloudR when the user wants an HTML report artifact similar to the canonical “DEVAL Details” output and the run directory already contains the interchange parquet assets.

## Key ideas

- Run directories are typically under `PRIMARY_RUN_ROOT` (default `/geodata/weppcloud_runs`), but may also be partitioned under `PARTITIONED_RUN_ROOT` or batch roots.
- The renderer resolves a `run_dir` from `runid` + `config` (and optional pup), then writes outputs under:
  - `<run_dir>/export/WEPPcloudR/`

## Endpoint shape

- `GET /runs/<runid>/<config>/report/deval_details`

Service docs live in `wepppy/weppcloudR/README.md` and the resolver logic is implemented in `wepppy/weppcloudR/plumber.R` (`resolve_run_dir()`).
