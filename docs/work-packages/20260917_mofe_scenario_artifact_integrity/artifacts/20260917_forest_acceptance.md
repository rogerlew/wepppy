# Forest acceptance - MOFE scenario artifact integrity

**Status**: deployment and clone recovery PASS; scenario execution in progress
**Target**: `forest1.local` test production
**Gate**: production deployment and run repair are blocked until this artifact
passes independent review

## Candidate Identity

- Reviewed contract revisions: `ecda89e45`, `f1a4a75b4`.
- Candidate implementation revision: `f4152ac69` (local broad gates passed).
- Forest pre-deploy revision: `a4877628676388817b4a68671f6144e91d174683`.
- Exact candidate checkout: `ffa241766` (implementation `f4152ac69`, plus evidence).
- Forest post-deploy revision: `ffa241766e2587c7e35726caa6f4e6dc32420711`.
- Subsequent config-only correction: `253188229`; the same built image/source
  remains in use. Only the stopped fork worker was recreated with the missing
  token-file mount, matching the dedicated wepp3 service.
- Worker identity: `uid=1000(roger) gid=993(docker)`.
- Worker `landuse.py` SHA-256:
  `86be20117e7958a0dd23ded739e111984a5c0d470f2824d456057304ae176070`.
- Worker `project_rq.py` SHA-256:
  `f72c5f74c045dba5342a590042c5eafaba0992d91a1762cb9115dbc911f9fe35`.
  Both match the reviewed local source. Canonical deployment verified candidate
  image identity, service health, stable restart counts, worker registration,
  renderer identity/data sharing, and functional CAPTCHA before completing.
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
branch name and history remain intact. The fast-forward and canonical deployment
started at approximately 02:20 UTC; transcript `/tmp/mofe-forest-deploy.log`.
The latest idle-queue check at 02:19 UTC found zero queued or executing jobs.
Docker's documented Forest procedure also requires explicitly starting the
existing `fork-archive` profile before submitting disposable clone jobs.

## Resolved Forest Dependency

The canonical fork request for `mofe-0918-baseline` was accepted as job
`d947f1db-f1fc-4e68-bcd1-47a5070950b2`, then failed at 02:32:40 UTC before
the task body or target directory creation. Retained job response:
`/tmp/mofe-fork-baseline-jobinfo.json`. The import chain is
`project_rq -> wepp_rq -> wepp_rq_stage_finalize -> discord_client`, ending in
`FileNotFoundError` for
`/workdir/weppcloud2/weppcloud2/discord_bot/.bot_token`.

The production Compose fork profile previously mounted only the Redis secret, unlike the
other workers' Discord token-file mount. Archive and restore use the same queue
and module, so neither was an alternate path around this failure.

The newly started fork consumer was stopped after confirming zero queued and
zero started fork/archive jobs; the failed job remains available for diagnosis.
Roger explicitly approved the separate minimal dependency fix. Commit
`253188229` adds the existing token-file secret alias to this profile. Seven
existing worker-startup contract tests passed; resolved Compose validation and
the real `project_rq` import passed as `1000:993`. Independent correctness review
PASS. Retry job `75be1635-6808-4df0-bf13-0fec0a475d66` completed, followed by seven
successful fork jobs for the remaining scenario roles. No Python, image,
identity, queue, or notification behavior changed. Source
`ron.nodb` and `landuse.nodb` hashes remained unchanged after the failed request.

## Preconditions

- [x] Local focused and broad gates pass.
- [x] Correctness and QA reviews have no unresolved high/medium findings.
- [x] Candidate revision is available to the canonical Forest deployment path.
- [x] `hostname`, repository path, installed `wctl` preset, queue state, and
      service health are verified.
- [x] No active default/batch job would be interrupted by deployment.
- [x] Actual Rithet Creek project clone/archive provenance and checksum are
      recorded without mutating the production source.

## Project Provenance

Read-only source discovery found `/wc1/runs/ve/ventilated-gag` on the shared
run storage with landuse, soils, watershed, and WEPP artifacts. Its README names
configuration `canada-wbt-mofe`. This is the verified source for the eight
supported Forest forks.
It has not been mutated by this work. Read-only checks on wepp1 and Forest's
shared storage match both `ron.nodb` SHA-256
`9a983dd4f64260909907edf6178b53b919aac15ff917aa869f448c256d43a717`
and `landuse.nodb` SHA-256
`02742ada3f8cea4d5b2fbf2811878578927ad278f4937aa1e34bc57ac1826ce5`.
The project name is `Rithert_MOFE`, mapping `c3s-disturbed`, with 455 hillslopes
and 1,065 segments (1,052 class 90; 13 class 200). Before regeneration, eight
hillslopes have stale forest management where saved assignments specify bare
ground, in both landuse and prepared files. Regenerate the disposable baseline
from its saved assignments before comparing results.

The original SBS input was copied read-only from
`wepp1:/geodata/wc1/runs/ch/choice-feminist/disturbed/prediction_wgs84.tif`
to `/tmp/mofe-original-sbs.tif`; SHA-256
`47b4c7f7aeb603d0ecbf00cf736b1d0699d257ee6bff7833b9b5cf6ac87452cf`.
The source's classification breaks are `[-1, 0, 1, 2]`, nodata `[255]`.

- Production source run: `ventilated-gag`, matching hashes above.
- Supported transfer: normal authenticated `/fork` API, no hand-copy/NoDb edit.
- Source archive SHA-256: not applicable (fork selected); source state and SBS
  input hashes retained above.
- Disposable IDs: `mofe-0918-` followed by `baseline`, `low`, `moderate`, `high`,
  `sbs`, `prescribed`, `thin30`, or `thin50`.
- Configuration: `canada-wbt-mofe`; original 22-year climate (2002-2023).
- No scientific state of the source was modified; fork metadata is recorded by
  the normal API. Production deployment/repair remains operator-gated.

## Interim Artifact Checks

Read-only parser checks passed for all 455 management files in every scenario,
including 30% and 50% thinning. Checks compare segment counts,
canopy/interrill/rill cover against intended class templates/explicit override,
and synthesized source-stack entries against the effective map. Baseline and
global scenarios retain 13 saved class-200 segments and alter only the 1,052
class-90 forest segments. SBS regenerated from the byte-identical original C3S
raster and real uploaded map yields 422 class-406, 627 class-418, and 16
class-405 segments. Native zonal readback of the original C3S raster returns
1,052 class-71 and 13 class-70 segments; both are forest classes, unlike the
saved manual class-200 assignments retained by the global-mapping scenarios.
SBS zonal classification independently returned 422/627/16 codes 131/132/133.
The public coverage operations produced 0.30 and 0.50 canopy, respectively,
with 0.75 interrill/rill cover on every applicable segment.

Full soil builds use the supported API with saved initial saturation 0.75 and
soil version 9002. The first six builds completed; both thinning builds remain
active. All 455 prepared management and soil files pass semantic checks for
baseline, low, moderate, high, prescribed, and SBS. Completed outputs,
archive/restore, and final comparisons remain pending; these interim checks
alone are not Forest acceptance.

| Class | Canopy | Interrill/rill cover |
| --- | --- | --- |
| 90 baseline | 0.90 | 1.00 |
| 406 low | 0.75 | 0.85 |
| 418 moderate | 0.60 | 0.60 |
| 405 high | 0.40 | 0.30 |
| 410 prescribed | 0.85 | 0.85 |
| 424 thinning | explicit 0.30 / 0.50 | 0.75 |

Readback uses finite numeric checks and exact segment order. Prepared soils
match generated soils after the source's existing saturation and restrictive-
layer transformations. For representative hillslope 101, baseline soil has
`ki=400000`, `kr=0.00003`, top-layer `ksat=50`; high severity has
`ki=1000000`, `kr=0.0001`, `ksat=15`. These are observed existing model choices,
not changed formulas or defaults. SBS output comparisons include the documented
13 bare-to-forest assignments and must not be attributed solely to fire severity.

The first queued baseline WEPP submission
`66f6d2bb-43b4-4581-aaaf-4c14ce299ea2` was canceled before starting when readback
showed an omitted advanced `kslast` field cleared the saved 0.0001 value.
The discovery schema omits this existing UI field. Its supported form contract
is `controls/wepp_pure_advanced_options/bedrock.htm`; the run-payload handler
explicitly accepts it. All subsequent WEPP requests include `kslast: 0.0001`,
`clip_soils: false`, and `initial_sat: 0.75`, preserving source choices.
Baseline retry is `d79c99a7-8b52-4186-a1bd-d7cddbc1d552`. No API or scientific
parameter code was changed; prepared-soil readback must account for this existing
restrictive-layer override.

Browser checks loaded all eight run pages through normal CAP verification.
Sample management downloads used the existing run-scoped service bearer token,
returned HTTP 200, and matched local bytes. Anonymous download returned HTTP 401
and is not claimed to pass. Logs/screenshots are `/tmp/mofe-browser*`; repeat the
check after final execution so the 50% sample reflects its completed mutation.

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
