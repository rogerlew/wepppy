# Artifacts Contract

This file documents required evidence under `artifacts/` for one incident package.

## Required Layout

```text
artifacts/
├── README.md                  # this file (filled for incident)
├── manifest.csv               # machine-readable inventory
├── checksums.sha256           # sha256 for immutable files
├── logs/                      # raw and tailed run logs per case
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
- `other`

## Minimum Required Evidence

1. One stderr artifact per matrix case.
2. One command artifact showing exact executable + input file.
3. One environment capture artifact per host/container context.
4. One diff artifact for each mutated case (not required for pure baseline).
5. Checksums for all files referenced by `manifest.csv`.

## Environment Capture Files (`env/`)

Include at minimum:

- `host.txt` (`hostname`, timestamp, role)
- `container.txt` (service/container id if applicable)
- `binary.txt` (`binary_path`, hash/version details)
- `git.txt` (repo commit sha for code that generated runs)

## Retention

- Keep artifacts alongside incident docs for auditability.
- Do not overwrite existing case artifacts; add new `case_id`s.

