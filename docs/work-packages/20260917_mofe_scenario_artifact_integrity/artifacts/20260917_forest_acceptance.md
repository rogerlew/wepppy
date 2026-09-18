# Forest acceptance - MOFE scenario artifact integrity

**Status**: preflight completed; deployment and scenario execution not run
**Target**: `forest1.local` test production
**Gate**: production deployment and run repair are blocked until this artifact
passes independent review

## Candidate Identity

- Reviewed contract revisions: `ecda89e45`, `f1a4a75b4`.
- Candidate implementation revision: `f4152ac69` (local broad gates passed).
- Forest pre-deploy revision: `a4877628676388817b4a68671f6144e91d174683`.
- Forest post-deploy revision: pending.
- Relevant host/container image and source checksums: pending.
- Rollback revision: pre-deploy revision above; canonical entry point
  `/workdir/wepppy/scripts/deploy-production.sh`.

Preflight at 2026-09-18 01:50 UTC verified hostname `forest1`, repository
`/workdir/wepppy`, clean branch `feature/project-owned-config`, and zero executing
default/batch jobs. The documented IP `192.168.1.108` works with SSH
`HostKeyAlias=forest1.local`; local name resolution fails. The saved host key
matches. Plain `wctl rq-info` works; `--detailed` is unsupported by the installed
RQ version. Deployment `--print-plan` selects full production Compose.
The initial branch-switch question was resolved without a switch: Git verifies
the existing Forest revision is an ancestor of `f4152ac69`. Fast-forward the
existing branch to the exact validated candidate, then use the canonical script's
supported `--skip-pull --no-flush-rq-db --skip-docker-prune` options. The existing
branch name and history remain intact. No deployment has yet been attempted.

## Preconditions

- [x] Local focused and broad gates pass.
- [x] Correctness and QA reviews have no unresolved high/medium findings.
- [ ] Candidate revision is available to the canonical Forest deployment path.
- [ ] `hostname`, repository path, installed `wctl` preset, queue state, and
      service health are verified.
- [ ] No active default/batch job would be interrupted by deployment.
- [ ] Actual Rithet Creek project clone/archive provenance and checksum are
      recorded without mutating the production source.

## Project Provenance

Read-only source discovery found `/wc1/runs/ve/ventilated-gag` on the shared
run storage with landuse, soils, watershed, and WEPP artifacts. Its README names
configuration `canada-wbt-mofe`. This is a candidate source for a supported Forest
fork; source provenance and disposable-clone identity still need verification.
It has not been mutated by this work.

- Production source run/archive: pending.
- Supported transfer method: pending; use normal clone or archive/restore only.
- Source archive SHA-256: pending.
- Forest disposable run IDs: pending.
- Configuration and project identity checks: pending.
- Source remains read-only: pending confirmation.

## Scenario Execution Inventory

| Scenario role | Forest run ID | Landuse job ID | WEPP-prep job ID | WEPP job ID | Terminal state |
| --- | --- | --- | --- | --- | --- |
| Baseline | pending | pending | pending | pending | not run |
| Low severity | pending | pending | pending | pending | not run |
| Moderate severity | pending | pending | pending | pending | not run |
| High severity | pending | pending | pending | pending | not run |
| SBS | pending | pending | pending | pending | not run |
| Prescribed burn | pending | pending | pending | pending | not run |
| 30% thinning | pending | pending | pending | pending | not run |
| 50% thinning | pending | pending | pending | pending | not run |

## Required Generated-Artifact Evidence

For every scenario, add links or paths to retained evidence for:

- persisted `domlc_d`, `domlc_mofe_d`, effective management map, and cover
  overrides;
- classified SBS segment distribution where applicable;
- sorted SHA-256 manifests of `landuse/hill_*.mofe.man` and relevant soils;
- parsed management classes and cover values across all applicable segments, with
  representative excerpts;
- sorted SHA-256 manifests and parsed values for `wepp/runs/*.man` and soils;
- RQ job trees, terminal status, logs, and visible failure diagnostics;
- WEPP output freshness and regenerated hillslope response summary;
- normal browser/download access and archive/restore byte preservation.

## Required Comparisons

| Comparison | Required observation | Result/evidence |
| --- | --- | --- |
| Baseline vs low | Effective eligible management classes encode low severity | pending |
| Low vs moderate | Classified/selected management classes differ as configured | pending |
| Moderate vs high | High-severity management and required soil inputs differ as configured | pending |
| Baseline vs SBS | SBS spatial mix reaches generated management and soil inputs | pending |
| Baseline vs prescribed | Prescribed class reaches generated managements | pending |
| 30% vs 50% thinning | Applicable combined and prepared managements contain 0.30 vs 0.50 canopy | pending |
| Landuse vs WEPP prep | Prepared files preserve the corrected combined input semantics | pending |
| Inputs vs results | Any equal results are explained from verified effective inputs | pending |

## Failure and Retry Evidence

- Controlled disposable-project writer failure: pending.
- No false completion event: pending.
- Partial artifacts and diagnostics remain visible: pending.
- Supported retry converges from persisted assignment state: pending.
- Archive/restore retains completed and failed evidence: pending.

## Acceptance Verdict

- Exact candidate verified in all relevant containers: no.
- Actual-project generated-output gate: not run.
- No unresolved correctness/QA findings: no.
- **Forest gate**: fail / not run.
- Reviewer and timestamp: pending.

When this gate passes, present the evidence to Roger and stop. Do not deploy to
WEPPcloud or mutate the Abdisa production runs. The next phase begins only after
Roger records explicit deployment confirmation in the production repair ledger.
