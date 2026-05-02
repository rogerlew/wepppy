# Artifacts Contract

This file documents required evidence under `artifacts/` for one incident package.

## Required Layout

```text
artifacts/
├── README.md                  # this file (filled for incident)
├── manifest.csv               # machine-readable inventory
├── checksums.sha256           # sha256 for immutable files
├── logs/                      # raw and tailed run logs per case
│   ├── fuzzy_case_results.csv # required fuzzy replay outcomes per case
│   └── fuzzy_failures.md      # required fuzzy failure ledger
├── diffs/                     # run-file/input diffs per case
├── repro/                     # copied inputs for each case
└── env/                       # host/container/binary/runtime metadata
```

## `manifest.csv` Schema

Required columns:

```csv
artifact_id,case_id,artifact_type,relative_path,description,produced_by,created_utc
```

Artifact type enum:

- `stderr`
- `stdout`
- `tail`
- `diff`
- `repro_input`
- `env_capture`
- `command_log`
- `fuzzy_case_result`
- `fuzzy_failure_ledger`
- `other`

## Minimum Required Evidence

1. One stderr artifact per matrix case.
2. One command artifact showing exact executable + input file.
3. One environment capture artifact per host/container context.
4. One diff artifact for each mutated case (not required for pure baseline).
5. One reproducibility artifact proving shared replay context capture (for example
   inventory of `wepp_ui.txt`, `pmetpara.txt`, `snow.txt`, `gwcoeff.txt`,
   `chan.inp`, `chntyp.txt`, `tc.txt` when present).
6. One fuzzy results artifact (`logs/fuzzy_case_results.csv`) for the promotion
   candidate run.
7. One fuzzy failure ledger (`logs/fuzzy_failures.md`) summarizing failures or
   explicitly stating no failures were observed.
8. Checksums for all files referenced by `manifest.csv`.

## Environment Capture Files (`env/`)

Include at minimum:

- `host.txt` (`hostname`, timestamp, role)
- `container.txt` (service/container id if applicable)
- `binary.txt` (`binary_path`, hash/version details)
- `git.txt` (repo commit sha for code that generated runs)

## Retention

- Keep artifacts alongside incident docs for auditability.
- Do not overwrite existing case artifacts; add new `case_id`s.
