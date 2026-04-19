# Ablation Investigation Standard

This directory defines the canonical documentation contract for WEPP ablation investigations across:

- `forest` (development host)
- `wepp1` and `wepp2` (production hosts)

Use this standard before running new ablation work so evidence and conclusions are reproducible.

## Scope

This standard applies to investigations where we vary one input or behavior at a time to isolate a failure trigger (for example `SIGFPE`, hangs, parity drift, missing success markers).

## Required Directory Layout

Create one directory per incident:

```text
docs/ablation/<incident_id>/
├── incident.md
├── notes.md
├── matrix.csv
└── artifacts/
    ├── README.md
    ├── manifest.csv
    ├── checksums.sha256
    ├── logs/
    ├── diffs/
    ├── repro/
    └── env/
```

Recommended `incident_id` format:

```text
YYYYMMDD_<runid>_<scope>_<signature>
```

Examples:

- `20260418_suppurative-skunk_pw0_sigfpe-wshdrv`
- `20260418_srivas42-claustrophobic-shortcut_p325_sigfpe-param`

## Required Files

### `incident.md` (decision record)

Use `TEMPLATE_incident.md`. This is the executive and technical summary for handoff.

Required content:

- what failed and where
- production impact and blast radius
- baseline reproduction command and outcome
- minimal failing vs nearest passing case
- ablation conclusion with evidence links
- chosen remediation and rollback/guardrails
- open questions and follow-up tasks

### `notes.md` (chronological operator log)

Use `TEMPLATE_notes.md`. This is a timestamped activity log, not a polished summary.

Required content:

- exact commands executed
- environment context captured at run time
- observations after each ablation lane
- explicit assumptions and corrections

### `matrix.csv` (machine-readable run matrix)

Use `TEMPLATE_matrix.csv`. One row per ablation run. Never summarize multiple runs into one row.

Required contract:

- immutable lane id and case id
- explicit mutation description
- binary and environment used
- deterministic pass/fail signal
- failure signature fields (signal, frame, stderr tail path)
- artifact paths for replay

### `artifacts/*` (replay evidence)

Use `TEMPLATE_artifacts.md` to document required artifact contents.

Minimum required artifacts:

- command transcripts or command list
- stderr/stdout logs for each case
- run-file diffs used in ablations
- copied reproduction inputs (never mutate original run files)
- environment capture (host/container/binary/git/runtime metadata)
- checksum file for immutable references

## Environment Capture Requirements

Every incident must document where runs were executed:

- `host_role`: `dev` or `prod`
- `host_name`: `forest`, `wepp1`, or `wepp2`
- `container_service`: `rq-worker`, `rq-worker-batch`, or `none`
- `binary_path` and binary identifier
- UTC timestamp of each run row

If the same incident uses both dev and prod contexts, keep one shared `incident.md` and one `matrix.csv`, but include environment fields on every row.

## Safety and Reproducibility Rules

- Do not edit `/wc1/runs/...` originals in place for ablation.
- Copy run inputs to a staging location and mutate copies only.
- Keep changes single-factor per lane.
- Record negative results; failed hypotheses are required evidence.
- Keep artifact paths stable and relative to the incident directory.

## Naming and Status Conventions

- `pass_fail` values: `PASS`, `FAIL`, `ERROR`, `UNKNOWN`.
- `host_role` values: `dev`, `prod`.
- `scope` examples: `p325`, `p326`, `pw0`, `watershed`, `hillslope`.
- Use UTC in machine-readable files (`matrix.csv`), local time optional in `notes.md`.

## Bootstrapping a New Incident Package

```bash
incident_id="YYYYMMDD_<runid>_<scope>_<signature>"
root="docs/ablation/${incident_id}"
mkdir -p "${root}/artifacts/"{logs,diffs,repro,env}
cp docs/ablation/TEMPLATE_incident.md "${root}/incident.md"
cp docs/ablation/TEMPLATE_notes.md "${root}/notes.md"
cp docs/ablation/TEMPLATE_matrix.csv "${root}/matrix.csv"
cp docs/ablation/TEMPLATE_artifacts.md "${root}/artifacts/README.md"
touch "${root}/artifacts/manifest.csv" "${root}/artifacts/checksums.sha256"
```

