# Forest acceptance - MOFE scenario artifact integrity

**Status**: Forest acceptance PASS; correctness and QA PASS
**Target**: `forest1.local` test production
**Gate**: accepted for operator-owned deployment; run repair waits for Roger's
explicit WEPPcloud deployment confirmation

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

## Artifact Checks

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

All eight full soil builds use the supported API with saved initial saturation
0.75 and soil version 9002. All 455 hillslope management/soil files per scenario
pass semantic checks at both generated and prepared boundaries. Each final
manifest also retains the additional `pw0` watershed management/soil file.
All eight complete WEPP trees contain 15 finished jobs, with fresh 22-year
interchange outputs, 455 exact hillslope IDs, and finite summary metrics.

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

The fresh baseline yields 738.9182 mm/year runoff and 128.4518 tonnes/year
sediment, versus the reporter's 736.6318 and 12.6926. Independent comparison
confirms that sediment/soil-loss changes occur only on the eight hillslopes with
13 saved class-200 segments. All 455 slope/climate files are byte-identical and
all parsed soils are identical to the original; only those eight prepared
management files differ. Class 200 is labeled "Bare areas" but its established
template is `GeoWEPP/grass.man` (bromegrass, cover 0.50/0.50/0.50), not a new
bare-soil parameterization. This package preserves that mapping.

Scientific interpretation caveat: gross soil loss and deposition become very
large on several of those hillslopes. Hillslope 341's raw WEPP output itself
reports 679,334,263.6 kg/year loss and 679,334,109.5 kg/year deposition; this is
not an interchange/unit-conversion error. Artifact fidelity does not establish
physical calibration. Outside the eight affected hillslopes, sediment and soil
loss are unchanged; hillslope 82 has only a 0.1 m3/year runoff rounding difference.

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

Final browser checks loaded all eight run pages through normal CAP verification.
Sample management and final hillslope-result parquet downloads used the existing
run-scoped service bearer token, returned HTTP 200, and matched local bytes.
The 30% and 50% sample hashes differ as intended. Anonymous download returned
HTTP 401 and is not claimed to pass. Browser access/download is tested here;
scientific mutations used the supported authenticated API, not browser clicks.

## Scenario Execution Inventory

| Scenario role | Forest run ID | Landuse job ID | WEPP-prep job ID | WEPP job ID | Terminal state |
| --- | --- | --- | --- | --- | --- |
| Baseline | mofe-0918-baseline | 66d34197-942a-43dc-8fde-7e92d93b1457 | de832c9c-7e4d-4cb0-9b7f-cb83c57000e8 | d79c99a7-8b52-4186-a1bd-d7cddbc1d552 | finished |
| Low severity | mofe-0918-low | 1c5fb339-d5e1-4881-a74a-bdaee98a7dce | e29db012-0d94-40f0-9349-6e1a65025ef5 | 466b4804-e35d-4e93-ae7d-c18598520071 | finished |
| Moderate severity | mofe-0918-moderate | a17a1b56-3338-4f72-8aec-6ff912302bc6 | 8c258b98-cbca-49bf-bf74-52d62c07fdd1 | 28b40fc7-5eaa-4f21-ac3b-50b45da37d3b | finished |
| High severity | mofe-0918-high | 3d933c56-d248-49af-b088-174d372a59db | 2540bd15-393c-425f-b89b-40276cb30cf5 | d29e0159-debb-4e2b-bf94-a23b4787a171 | finished |
| SBS | mofe-0918-sbs | 10a4b15f-3b3e-4c12-b3dd-7d266a4d703f | 73e13ce5-53cf-4dcd-9c34-b20032597279 | 90d66862-fcfa-443c-9b6d-bfad9b52c1bf | finished |
| Prescribed burn | mofe-0918-prescribed | 4037aba0-b513-4d10-af37-c0374b7e970d | de355520-59e0-44ec-ac82-95abac2cae48 | 89e5ee57-f731-48ac-a11c-5f79124072a4 | finished |
| 30% thinning | mofe-0918-thin30 | 5918022e-0ade-4c0d-a684-702cb4b355a9 | fc3ccc45-073e-4480-8b18-cf309c32373c | 82375362-d3fb-42eb-ad38-72c9fc0f3374 | finished |
| 50% thinning | mofe-0918-thin50 | fa80d842-a6ef-49da-837f-c0c948717607 | cfbb40c5-f15d-404b-b92d-2a6bc692233b | 7d9dda07-7031-42f6-a0f3-4ca60899f40f | finished |

## Retained Generated-Artifact Evidence

The [evidence bundle](forest-evidence.tar.gz) retains every scenario's terminal
job trees/status, complete parsed per-segment observations and sorted SHA-256
manifests, failure/retry/restore captures, runtime identity, and final browser
results/screenshots. Bundle SHA-256:
`d99c9c85ff79e203a0f3fe7b222b733b8df41333d081fbcfe7b1f35ba1f49b21`.
It contains no credentials. The following evidence is covered:

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
| Baseline vs low | Effective eligible management classes encode low severity | PASS: 453 management files and parsed soils differ |
| Low vs moderate | Classified/selected management classes differ as configured | PASS: 453 management files and parsed soils differ |
| Moderate vs high | High-severity management and required soil inputs differ as configured | PASS: 453 management files and parsed soils differ |
| Baseline vs SBS | SBS spatial mix reaches generated management and soil inputs | PASS: all 455 management files and parsed soils differ |
| Baseline vs prescribed | Prescribed class reaches generated managements | PASS: 453 management files and parsed soils differ |
| 30% vs 50% thinning | Applicable combined and prepared managements contain 0.30 vs 0.50 canopy | PASS: 453 management files differ; parsed soils identical |
| Landuse vs WEPP prep | Prepared files preserve the corrected combined input semantics | PASS: all 3,640 hillslopes / 8,520 segments |
| Inputs vs results | Any equal results are explained from verified effective inputs | PASS: all eight aggregate runoff/sediment pairs differ |

Two all-class-200 hillslopes legitimately retain identical management files across
global scenarios. Soil file headers include run paths, so soil hashes differ
even where parsed parameters match; thinning soil equivalence is semantic, not
inferred from hashes.

## Fresh Hillslope Summary

[Full reporter-shaped CSV](mofe-forest-hillslope-response-summary.csv) and
[output hashes/provenance](mofe-forest-summary-sources.json) were generated by
`summarize_forest.py`. Formula checks independently reproduce the reporter's
original baseline, including sample standard deviations. Annual interchange
values are not divided by 22 again. Area is 1,807.5 ha for all eight scenarios.

| Scenario | Runoff (mm/year) | Sediment yield (tonnes/year) |
| --- | --- | --- |
| Baseline | 738.9182 | 128.4518 |
| Low | 943.5181 | 897.0849 |
| Moderate | 951.6108 | 1,149.7958 |
| High | 1,048.2389 | 4,875.6990 |
| SBS | 948.6587 | 2,247.7876 |
| Prescribed | 906.8019 | 364.5123 |
| 30% thinning | 982.8661 | 10,528.0770 |
| 50% thinning | 956.9823 | 7,433.2373 |

These prove propagated scenario inputs and fresh outputs, not calibration or an
expected severity ordering. The baseline/template and SBS comparability caveats
above remain important when interpreting this table.

## Failure and Retry Evidence

- Controlled writer failure: job `5f258c9a-3788-40fb-9e2f-ccfc72d68b90`
  failed with a real `PermissionError` at the combined-management `open()`.
  Only disposable `landuse/hill_101.mofe.man` was temporarily changed from mode
  0644 to 0444; verified regular file, one link, distinct source inode, worker
  identity 1000:993. An EXIT trap restored exact mode 0644, including on errors.
- No false completion: captured live landuse status stream has the exact job's
  `EXCEPTION` and no `COMPLETED` or completion trigger. The log retains 114
  completed synthesis tasks before the failure; prior files remain inspectable.
- Persisted rollback: `domlc_d`, `domlc_mofe_d`, and management selections match
  the successful pre-failure archive exactly. Full parsed-input readback still
  passes because the injected identity remap preserves scientific intent.
- Failed-state archive job `9d1152d0-5ef7-49d1-9241-3299dd8e4a7f` finished.
  `archives/mofe-0918-baseline.20260918T042733Z.zip` contains the diagnostic
  `landuse.log` byte-for-byte: SHA-256
  `aca506cbacff518c85965bb42d5ec269304ac933f4971701ecf16d75b60e8ba7`.
- Supported identity-remap retry `4ae64813-6ae5-41bf-9d4b-b00b59394553` finished;
  every management/soil manifest matches the pre-failure result exactly.
- Successful archive job `4b3b17c8-23e7-4a2e-9366-64a86d89fe79` finished.
  `archives/mofe-0918-baseline.20260918T042149Z.zip` holds the completed baseline;
  restore job `0456c405-426e-444d-861b-4b629cb8fc02` finished and all 7,897
  pre-archive file hashes match. Restore replaced only the disposable baseline
  contents; both completed and failed-state archives remain available.
- Completed archive SHA-256:
  `9d08ba831b22ab8c114e5d5dfce96a5f53ed1a71f4c09e1c840eca69fabae79c`.
- Failed-state archive SHA-256:
  `6b6b8d17d202aa711427a86859bb3c7b4457ea9e8ecaa1de77a962070704de8b`.

## Acceptance Verdict

- Exact candidate verified in all relevant containers: yes, five services.
- Actual-project generated-output gate: PASS, all eight scenarios.
- No unresolved High/Medium correctness or QA findings: yes.
- **Forest gate**: PASS, 2026-09-18 UTC.
- Independent correctness: `correctness_review`, PASS; verified all 14,576 live
  input-file hashes and recomputed all numeric summary fields.
- Independent QA: `qa_review`, PASS, 2026-09-18 04:39 UTC; independently checked
  job trees, observations, browser/provenance hashes, retries, restore, and bundle.
- Final queue check at 04:40 UTC: zero queued/executing default, batch, and
  fork/archive jobs. Intentional failed-job evidence remains available.

This gate passed. Present the evidence to Roger and stop. Do not deploy to
WEPPcloud or mutate the Abdisa production runs. The next phase begins only after
Roger records explicit deployment confirmation in the production repair ledger.
