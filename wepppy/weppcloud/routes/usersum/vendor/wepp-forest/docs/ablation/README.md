# Ablation Investigation Standard

This directory defines the canonical documentation contract for WEPP ablation investigations across:

- `forest` (development host)
- `wepp1` and `wepp2` (production hosts)

Use this standard before running new ablation work so evidence and conclusions are reproducible.

Protocol reference:

- `docs/ablation/protocol.md` for lane design and decision policy.

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
- incident metadata header with `incident_id`, `status`, and `scope`

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
- `contract_refs` and `boundary_disposition` for upstream mutation lanes (`U*`)

### `artifacts/*` (replay evidence)

Use `TEMPLATE_artifacts.md` to document required artifact contents.

Minimum required artifacts:

- command transcripts or command list
- stderr/stdout logs for each case
- run-file diffs used in ablations
- copied reproduction inputs (never mutate original run files)
- environment capture (host/container/binary/git/runtime metadata)
- fuzzy-case replay results (`artifacts/logs/fuzzy_case_results.csv`)
- fuzzy-case failure ledger (`artifacts/logs/fuzzy_failures.md`, may state no failures)
- checksum file for immutable references

## Artifact Placement and Disk Budget (Required)

Keep in repository:

- `incident.md`, `notes.md`, `matrix.csv`
- `artifacts/manifest.csv` and `artifacts/checksums.sha256`
- lane stderr/stdout logs, run-file diffs, and compact summaries needed to audit conclusions
- minimal replay capsules (only files needed to replay documented lanes)

Hold out of repository:

- full mirrors of large watershed run trees (`/wc1/runs/.../wepp/runs`)
- full-period watershed replay payload trees and dense output mirrors
- core dumps and debugger memory images
- any single artifact larger than 100 MB or incident payloads that materially grow repo size

Execution/storage policy for large watershed incidents:

- prefer running full-period watershed ablations on `wepp1`/`wepp2` in isolated workspaces under `/wc1`
- prefer storing large held-out payloads under `/wc1` holdout paths, not under `/workdir` system disk
- keep only compact, audit-sufficient evidence in git; reference held-out payload location in incident docs when retained

Automated gate:

```bash
python tools/check_ablation_artifact_policy.py
```

Notes:
- legacy exemptions are tracked in
  `docs/ablation/artifact_policy_legacy_exemptions.txt`
- watershed incident payloads exceeding policy budget must be moved to `/wc1`
  holdout storage and replaced with compact in-repo evidence
- policy-era incident aggregate budgets are enforced by default:
  - `--max-file-mib` (default `100`)
  - `--max-incident-artifacts-mib` (default `500`)
  - `--max-watershed-repro-mib` (default `250`)

## Watershed Durability Metadata (Required)

For watershed/mixed incidents, `matrix.csv` must include:

- `durability_lane` (`decisive|exploratory|na`)
- `configured_simulation_years`
- `simulated_years_completed`

`python tools/ablation_protocol.py finalize --incident-id <incident_id>` enforces
these fields (for policy-era watershed incidents) and requires full-period
completion for decisive `PASS` rows. Resolved watershed statuses must include at
least one decisive full-period pass.

## Upstream Mutation Contract Metadata (Required)

For policy-era upstream mutation lanes (`U*`), `matrix.csv` must include:

- `contract_refs`
- `boundary_disposition`

`python tools/ablation_protocol.py finalize --incident-id <incident_id>` enforces
that every `U*` row either cites semicolon-separated `SC-...#INV-...` references
or records `boundary_disposition` as `model_gap` or
`requires_scientific_review`.

### `hillslope_watchlist.csv` (permanent resolved-seed gate)

Canonical path:
- `docs/ablation/hillslope_watchlist.csv`

Purpose:
- defines the permanent hillslope regression seed set executed before vendoring
  WEPP binaries.

Required policy:
- when a hillslope incident package status is promoted to
  `resolved`, `resolved-and-hardened`, or `closed`, add/update that incident's
  seed coverage in `hillslope_watchlist.csv` in the same change set.

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
- For hillslope/watershed replays, copy both target `p<id>.*` files and
  run-shared context files from the same `runs/` directory
  (`wepp_ui.txt`, `pmetpara.txt`, `snow.txt`, `gwcoeff.txt`, `chan.inp`,
  `chntyp.txt`, `tc.txt` when present).
- Do not classify a source-only signature as "non-reproducible" until replay
  has been validated with full shared context.
- Keep changes single-factor per lane.
- Upstream scientific mutation lanes are allowed only when
  `docs/ablation/protocol.md` eligibility and gate requirements are met
  (scientific rationale + invariants + non-regression gates).
- Do not promote remediation without a passing fuzzy-regression gate and
  documented fuzzy outcomes/failures.
- Record negative results; failed hypotheses are required evidence.
- Keep artifact paths stable and relative to the incident directory.

## Naming and Status Conventions

- `pass_fail` values: `PASS`, `FAIL`, `ERROR`, `UNKNOWN`.
- `host_role` values: `dev`, `prod`.
- `scope` metadata values in `incident.md`: `hillslope`, `watershed`, `mixed`.
- Use UTC in machine-readable files (`matrix.csv`), local time optional in `notes.md`.

## Bootstrapping a New Incident Package

Preferred (automated):

```bash
incident_id="YYYYMMDD_<runid>_<scope>_<signature>"
python tools/ablation_protocol.py init --incident-id "${incident_id}"
```

After adding artifacts, regenerate `manifest.csv` and `checksums.sha256`:

```bash
python tools/ablation_protocol.py finalize --incident-id "${incident_id}"
```

Fallback (manual bootstrapping only):

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

## Existing Incident Records

- `docs/ablation/20260414-numerical-stability-patches.md`
- `docs/ablation/20260418_p325_sigfpe_ablation.md`
- `docs/ablation/20260418_suppurative-skunk_pw0_sigfpe-wshdrv/`
