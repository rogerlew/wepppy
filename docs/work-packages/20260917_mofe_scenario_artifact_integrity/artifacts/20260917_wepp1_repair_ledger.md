# wepp1 repair ledger - Abdisa Rithet Creek runs

**Status**: blocked; no production mutation authorized yet
**Prerequisite 1**: Forest acceptance PASS, 2026-09-18 UTC
**Prerequisite 2**: Roger must deploy the accepted revision to WEPPcloud and
explicitly confirm completion

## Deployment Confirmation Gate

- Forest-accepted implementation: `f4152ac69`; image built at `ffa241766`,
  config-only fork-worker correction `253188229`. Later package-evidence commits
  do not change runtime source; verify deployed hashes against the Forest record.
- Forest acceptance reviewers: independent `correctness_review` and `qa_review`,
  both PASS on 2026-09-18 UTC; see the Forest artifact's Acceptance Verdict.
- Roger deployment confirmation text: pending.
- Confirmation timestamp and timezone: pending.
- Deployed wepp1 revision: pending.
- Deployed relevant container revisions/checksums: pending.
- Queue/service health: pending.

Do not submit a repair job until every item above is populated and the deployed
revision equals the Forest-accepted revision or an explicitly reviewed descendant.

## Repair Inventory

| Scenario | Run ID | Intended state | Known pre-repair defect | Status |
| --- | --- | --- | --- | --- |
| Baseline | `ventilated-gag` | Saved unburned assignments, including 13 class-200 segments | Eight hillslopes still encode forest for class 200 | Blocked |
| Low severity | `equestrian-bonheur` | Effective class 406 | Baseline-equivalent MOFE managements | Blocked |
| Moderate severity | `tactful-aging` | Effective class 418 | Baseline-equivalent MOFE managements | Blocked |
| High severity | `incorporate-cerebrum` | Effective class 405 | Baseline-equivalent managements; distinct soils | Blocked |
| SBS | `choice-feminist` | Spatial 406/418/405 mix | Persisted mix but baseline-equivalent managements | Blocked |
| Prescribed burn | `neoliberal-dictate` | Effective class 410 | Baseline-equivalent MOFE managements | Blocked |
| 30% thinning | `acetic-surprise` | Class 424; canopy 0.30 | Generated canopy 0.40 | Blocked |
| 50% thinning | `uncrowned-bolt` | Class 424; canopy 0.50 | Generated canopy 0.40 | Blocked |

## Preflight and Preservation

Preserve saved scientific choices, including initial saturation 0.75 and
`kslast=0.0001`; the existing run-WEPP payload must include the latter explicitly.
Do not change the class-200 template or force the SBS raster's classes to match
saved global-remap assignments. Carry forward the baseline/SBS comparability and
large gross erosion/deposition caveats from the
[Forest evidence](20260917_forest_acceptance.md#fresh-hillslope-summary).

Before each run changes, record:

- wepp1 `hostname`, `/workdir/wepppy` revision, relevant container identity, and
  service health;
- host and container run-path existence using the two-character run prefix;
- active RQ job state and confirmation that the run has no conflicting job;
- controller/NoDb checksum and intended class/override summary;
- sorted SHA-256 manifests for current landuse, soil, prepared WEPP, and relevant
  output artifacts;
- current job IDs/status, log excerpts, and report/output timestamps;
- location/checksum of a normal project archive or other canonical recoverable
  pre-repair snapshot.

Old and failed artifacts are project records. Keep them visible and archivable;
do not delete them to make freshness checks pass.

## Per-Run Repair Record

Complete one copy of this record for every inventory row:

- Scenario/run ID: pending.
- Start/end timestamps with timezone: pending.
- Pre-repair archive/manifest path and SHA-256: pending.
- Persisted intended assignment/override: pending.
- Supported landuse rebuild operation and job ID: pending.
- Required soil rebuild operation and job ID, or explicit not-applicable reason:
  pending.
- WEPP preparation operation and job ID: pending.
- WEPP run job ID and public/canonical job-tree evidence: pending.
- Terminal state and failure/retry history: pending.
- Post-repair landuse/soil/WEPP input manifests: pending.
- Parsed management classes and cover values: pending.
- Output freshness and summary row: pending.
- Reviewer disposition: pending.

If any leaf job fails, stop that run's sequence, retain the failure, diagnose from
canonical RQ evidence, and retry only the supported bounded operation. Do not edit
NoDb or generated files directly. Do not advance a run based on file existence or
mtime alone.

## Required Sequence

1. Verify the deployment confirmation gate and wepp1 preflight.
2. Capture the complete pre-repair snapshot for one run.
3. Rebuild landuse from persisted scenario intent through the corrected workflow.
4. Rebuild scenario-dependent soils when the normal workflow requires it.
5. Prepare WEPP inputs and verify their parsed content before running WEPP.
6. Run WEPP and verify job-tree completion plus output freshness/content.
7. Complete that run's ledger entry and review it before starting the next run.
8. Repeat until all eight runs, including baseline, are complete.
9. Regenerate the eight-row hillslope response summary and compare it with the
   original attachment.

## Final Summary Comparison

- Original file SHA-256:
  `042c546ee7ea9c61daf63967d2cc7ffcf4de2881739df31a95c0aa8c37bac063`.
- Repaired summary path: pending.
- Repaired summary SHA-256: pending.
- Row count/scenario inventory: pending.
- Exact equality groups remaining: pending.
- Input-level explanation for any remaining equality: pending.
- Reviewer conclusion: pending.

## Completion Gate

- [ ] All eight pre-repair snapshots are retained and recoverable.
- [ ] All eight supported rebuild/rerun sequences have recorded job IDs.
- [ ] Every terminal success is backed by parsed generated-input content.
- [ ] SBS and global burn scenarios encode the intended effective classes.
- [ ] Thinning managements encode 0.30 and 0.50 canopy respectively.
- [ ] Refreshed outputs and summary are traceable to the repaired generation.
- [ ] No direct file/NoDb patch or silent cleanup was used.
- [ ] Independent correctness and QA reviewers accept the production evidence.

Package closure is prohibited until this checklist and the root tracker are
complete.
