# wepp1 repair ledger - Abdisa Rithet Creek runs

**Status**: all eight production runs PASS, 2026-09-18 UTC
**Prerequisite 1**: Forest acceptance PASS, 2026-09-18 UTC
**Prerequisite 2**: Roger-authorized deployment PASS on all three production hosts,
2026-09-18 by 10:44 UTC; see [deployment evidence](20260918_production_deployment.md).

## Deployment Confirmation Gate

- Forest-accepted implementation: `f4152ac69`; image built at `ffa241766`,
  config-only fork-worker correction `253188229`. Later package-evidence commits
  do not change runtime source; verify deployed hashes against the Forest record.
- Forest acceptance reviewers: independent `correctness_review` and `qa_review`,
  both PASS on 2026-09-18 UTC; see the Forest artifact's Acceptance Verdict.
- Roger delegated deployment: "proceed with deploy on wepp1, wepp2, and wepp3."
  This superseded the earlier operator-only deployment gate, not the repair checks.
- Deployment completion timestamp: 2026-09-18 by 10:44 UTC (all hosts).
- Deployed wepp1 revision: `f22ac0d549c141c8784dc1b5e2364e2ffd889421`.
- Relevant live source hashes and 1002:130 identities: PASS; deployment evidence
  records exact values for web/API/default/batch/fork workers.
- Queue/service health: canonical deployment gates PASS; web HTTP 200 and
  rq-engine health `ok`. Repeat live queue/run preflight before each repair.

Do not submit a repair job until every item above is populated and the deployed
revision equals the Forest-accepted revision or an explicitly reviewed descendant.

## Repair Inventory

Roger explicitly requested remediation and validation of this exact inventory
on 2026-09-18 after all deployment checks passed. Current production readback
is authoritative: fire scenarios also retain 13 grass/bare-remapped segments
(low 431, moderate 430, high 429, prescribed 432). Both thinning runs retain
1,021 class-424, 43 class-90 and one class-200 segment. Preserve these choices;
do not replace them with the simplified Forest clone assignments.

Baseline pre-repair archive job: `240eb7af-489a-4fd3-9ce2-8fac07b9e029`.
Read-only snapshot and 455-hillslope pre-repair parse are retained under
`/tmp/mofe-production-evidence/`; eight hillslopes reproduce the stale-management
defect. No scientific rebuild is submitted before archive content verification.

At 11:02 UTC, all eight read-only snapshots and pre-repair management parses
were captured. Failed semantic checks affect 8 baseline hillslopes, all 455
hillslopes in each of the five fire scenarios, and 434 hillslopes in each
thinning scenario. Baseline's 36 GB project includes 31 GB of historical `_pups`
data; the canonical full archive retains those records and is still running.

| Scenario | Run ID | Intended state | Known pre-repair defect | Status |
| --- | --- | --- | --- | --- |
| Baseline | `ventilated-gag` | Saved unburned assignments, including 13 class-200 segments | Eight hillslopes still encode forest for class 200 | PASS |
| Low severity | `equestrian-bonheur` | Classes 406/431 | Baseline-equivalent MOFE managements | PASS |
| Moderate severity | `tactful-aging` | Classes 418/430 | Baseline-equivalent MOFE managements | PASS |
| High severity | `incorporate-cerebrum` | Classes 405/429 | Baseline-equivalent managements; distinct soils | PASS |
| SBS | `choice-feminist` | Spatial 406/418/405 mix | Persisted mix but baseline-equivalent managements | PASS |
| Prescribed burn | `neoliberal-dictate` | Classes 410/432 | Baseline-equivalent MOFE managements | PASS |
| 30% thinning | `acetic-surprise` | Saved 424/90/200 subset; canopy 0.30 | Generated canopy 0.40 | PASS |
| 50% thinning | `uncrowned-bolt` | Saved 424/90/200 subset; canopy 0.50 | Generated canopy 0.40 | PASS |

## Preflight and Preservation

Preserve saved scientific choices, including initial saturation 0.75 and
`kslast=0.0001`; the existing run-WEPP payload must include the latter explicitly.

Soil reuse gate: all eight read-only `check_soil_intent.py` proofs pass for
455 hillslopes / 1,065 segments each, matching canonical synthesis from preserved
base soils, saved classes, and the active disturbed lookup. Full scientific
tokens include 9002 hydraulic columns. Every generated-soil hash matches its
pre-repair snapshot; baseline's full rebuild also left these bytes unchanged.
The remaining runs therefore reuse soils only after repeating this proof after
management repair, confirming unchanged hashes, and validating full prepared
soil tokens. A failed proof requires the supported rebuild. Independent
correctness review accepted this bounded decision; see the ExecPlan Decision Log.
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

### Baseline — ventilated-gag

- Archive finished 2026-09-18 11:34:55 UTC:
  `archives/ventilated-gag.20260918T105055Z.zip` (5,965,546,773 bytes), SHA-256
  `6a9c5627420e4e9921875be28904c6782d24464b2f77489f90d4df71e54d8a97`.
  All 3,774 non-log snapshot members match their archived SHA-256 values.
- Fresh pipeline has no active operation; direct RQ readback found zero queued
  or started jobs in default, batch, and fork-archive. The documented
  `wctl rq-info --detailed` option is unsupported by the installed RQ CLI.
- Identity mapping 90 → 90 via `modify-landuse-mapping`, job
  `2e311ae7-5b47-4050-a41c-d4b018672415`, finished 11:37:38 UTC. All 455
  generated management files pass semantic readback; exact saved dominant/OFE
  assignments, mapping namespace, and canopy overrides are unchanged.
- `build-soils` job `3db1de8b-851b-41a3-aa0b-f1b1fca52a52` started 11:38:20 UTC;
  payload preserves initial saturation 0.75 and soil version 9002; finished
  11:56:27 UTC. All 455 generated soil hashes remain unchanged.
- Preparation `f24a5e34-d726-44b2-a972-d672a92bdfaf`: 6/6 finished 11:59:47 UTC;
  generated/prepared management and soil readback PASS.
- WEPP `723f9306-39a5-40cc-b4ec-cf4fa1bae2d5`: 15/15 finished 12:10:55 UTC.
  Final 455-hillslope readback passes, including full prepared soil serialization
  with 9002 hydraulic columns. Only eight generated/prepared management files
  changed; soils and saved scientific settings are unchanged.
- Fresh 22-year summary: runoff 738.918169 mm/year, sediment 128.4518 tonnes/year.
  Independent recomputation matched all 65 numeric columns. Parquet SHA-256
  `e2b61c31a3a92923651801b7f38c5d8ae0a89b6650505e96ef60241228be413a`.
  Browser run page and authenticated management/parquet downloads PASS; served
  bytes match the remotely captured hashes.

### Low severity — equestrian-bonheur

- Archive `317ae19a-681a-4731-bb5c-a526a65642b3` finished; preserved file
  `archives/equestrian-bonheur.20260918T122055Z.zip` (976,316,900 bytes), SHA-256
  `740272c8a499757e2e7546bf9a95f09e20179a407fe6aee743b8287ea3fb54c8`.
  All 3,779 non-log snapshot members match.
- Identity mapping 406 → 406, job `ceb94f4a-999b-41f8-96bf-740ac4a783e0`:
  finished, 455-hillslope management readback PASS; exact 406/431 assignments
  unchanged. Post-management soil proof PASS (1,065 segments); every generated
  soil hash equals preservation snapshot. Full soil rebuild not required.
- Preparation `d1710103-b2f2-46e8-8ff9-2ce15b99cb7d` started 12:30:26 UTC;
  6/6 finished 12:35:32 UTC. Existing saturation 0.75, kslast 0.0001, and
  disabled clipping preserved; full prepared-input token checks PASS.
- WEPP `bb40f4ee-9c65-49e5-af75-d8c0d50d0d84`: 15/15 finished 12:49:57 UTC.
  Final input readback PASS. Fresh summary: runoff 941.757189 mm/year,
  sediment 771.6286 tonnes/year; independent review recomputed all 65 metrics.
  Output SHA-256 `d20424849b458bfd5d79d1e2f8d0abed4548437011a8edfc06716d5baa6a068e`.
- Private-page validation: archived/current PUBLIC marker absent, canonical
  owner count 1 (no personal details retained), normal post-CAP anonymous 404.
  Run-scoped authorized management/parquet downloads return 200 with matching
  hashes. Owner-authenticated UI NOT TESTED; no access setting changed. The
  initial public-page smoke assumption was corrected, not the privacy policy.
  Independent correctness review accepts the scientific and serving evidence.
  Secondary QA PASS, 2026-09-18 13:45 UTC.

### Moderate severity — tactful-aging

- Archive `b4e7f210-4fe4-4e62-8636-d3dcf85bea11` finished; all 3,781 non-log
  members match preservation snapshot. File `archives/tactful-aging.20260918T124207Z.zip`,
  976,317,988 bytes, SHA-256
  `981f5f1e4f5aa3ff86731ac9b70b897f607e26d79cbce5a748207ee5aebfc49d`.
- Fresh pipeline idle and saved landuse file hash unchanged immediately before
  identity mapping 418 → 418. Job `d6705347-91ef-4441-865c-2bff7e24b923`
  submitted 13:02:03 UTC; finished with 455-hillslope management readback PASS.
  Post-management soil-intent proof and unchanged soil hashes PASS; no full
  soil rebuild required.
- Preparation `a95d743c-f4c3-4730-92f4-ff891654192d`: 6/6 finished 13:09:34 UTC;
  full prepared-input readback PASS.
- WEPP `e9c0b388-0503-4562-bc50-7b1c0bf7c1e2`: 15/15 finished 13:25:40 UTC.
  Final 455-hillslope input readback PASS; saved scientific choices unchanged.
  Fresh runoff 949.476160 mm/year, sediment 979.628 tonnes/year. Output SHA-256
  `0e56c6bb31abe2435370c230803547850a9ccf65d35e916363371969cc6f89c8`.
- Preserved private access verified (PUBLIC absent before/after, owner count 1,
  expected anonymous 404); authorized management/output downloads match hashes.
  Owner-authenticated UI NOT TESTED.
  Independent correctness and secondary QA PASS (QA 13:45 UTC).

### High severity — incorporate-cerebrum

High pre-repair archive `daed109a-624c-4c47-a3cf-6e1e2a367d2e` verified 3,781
members; file `archives/incorporate-cerebrum.20260918T125034Z.zip`, 1,023,423,872
bytes, SHA-256 `8822a092ff06fc24a1a7286b2c53717e547d663b80e9d8a8cd083639519412c2`.
High identity mapping 405 → 405, job `df5b055d-3de8-4581-a1be-5534d664064b`,
submitted 13:31:51 UTC after fresh idle preflight and unchanged landuse hash.
Management and soil-intent readbacks pass; all generated soil hashes unchanged.
Preparation `4dd35556-cab4-433b-8cda-167dcf951ddb` finished 6/6 at 13:37:00 UTC;
full prepared readback passes 455 hillslopes with exact 405/429 assignments.
WEPP `bc7b53c5-33df-488b-8941-d684119d9d31` started 13:40:50 UTC.
Finished 15/15 at 13:51:06 UTC. Final 455-hillslope input checks PASS;
scientific settings and soils unchanged. Fresh runoff 1,046.572946 mm/year,
sediment 4,513.5104 tonnes/year; all 65 metrics independently recomputed.
Output SHA-256 `9521405695f5b580503c0fe598578ab96d99e74896e0fe5b117b23de5827b759`.
Authorized downloads match; private anonymous denial preserved. Owner UI not
tested. Independent correctness review PASS, no blocking findings.

### SBS — choice-feminist

Archive `929ef0e2-22aa-455d-ace7-807d637c6c15` preserved all 3,794 non-log
members in `archives/choice-feminist.20260918T125922Z.zip` (978,034,785 bytes),
SHA-256 `38c4a055f30d1921e59d5b17337712c62147f8cf2ec81c37713fe0378a2b9442`.

All eight canonical pre-repair archives now verify. Remaining archive receipts,
full SHA-256 values, and per-member checks are retained in each role's
`*-archive-verification.json` evidence. SBS request independently reviewed:
explicit C3S 2010, gridded mode 0, buffer 0, shrub burn true, grass burn false,
and `c3s-disturbed`. Full build recomputes maps, so exact saved dominant and OFE
map equality is required before advancing, not just matching class counts.

SBS full landuse rebuild `45683e48-ae24-4910-88dc-c374dfe1ad49` finished at
13:57:24 UTC. Exact saved dominant/OFE assignments pass: 418:627, 406:422,
405:16 segments. Generated management and post-management soil proof PASS;
all soil hashes unchanged. Preparation `006b7179-deba-48fb-89cb-9f705ed76c6c`
started 13:59:12 UTC with preserved saturation/kslast/clipping choices.
All 6/6 preparation jobs finished 14:04:06 UTC; exhaustive prepared readback
PASS at 14:15 UTC (455 hillslopes, zero failures). SBS has 86 distinct full soil
serialization keys versus 25 for global scenarios; its longer validation is
expected (independently counted read-only). WEPP
`1a0a2e80-bed5-44e9-a9ec-30d8af38df73` started 14:15:33 UTC.
Finished 15/15 at 14:27:02 UTC. Final full readback PASS, 455 hillslopes /
1,065 segments; exact maps, scientific settings, raster and soil hashes retained.
Fresh runoff 948.658728 mm/year, sediment 2,186.0559 tonnes/year; all 65 metrics
independently recomputed. Output SHA-256
`c2c06270f4eb05e951f93586c78b1ffaa37314be6e550b56059827f5ffa2f0e1`.
Private anonymous denial and authorized exact downloads PASS; owner UI not
tested. Independent correctness acceptance PASS.

### Prescribed burn — neoliberal-dictate

Prescribed archive `02c93fe0-0771-4767-91e5-6dec0d0f07ad` verified 3,781 members;
`archives/neoliberal-dictate.20260918T130809Z.zip`, 976,308,234 bytes, SHA-256
`7279a8ff16d6fe6043f4b88a44ff54ab842a317832c5ae63357ced5d22ad8a18`.
Identity mapping 410 → 410, `0f503495-5364-4df7-bcb9-1090deab19c8`, submitted
14:38:58 UTC after unchanged saved-state and idle-queue checks. Management and
soil proofs PASS, exact assignments and all soil hashes unchanged. Preparation
`5b47e082-b102-455d-9780-3cb95c8cf0c8` started 14:40:28 UTC.
Preparation finished 6/6 at 14:43:33 UTC; full prepared readback PASS.
WEPP `5b456e1e-b148-4c0f-88a9-597fb0a75724` started 14:46:43 UTC.
Finished 15/15 at 14:56:18 UTC. Final input readback PASS, 455 hillslopes /
1,065 segments, saved scientific choices unchanged. Fresh runoff 904.907557
mm/year, sediment 238.3798 tonnes/year. Output SHA-256
`8eeb4acb048e3f368ed5c2aa019c61a2b96d767bf46a27e906881981b168d71a`.
Authorized exact downloads and preserved private anonymous denial PASS; owner
UI not tested. Independent correctness review PASS; all 65 metrics recomputed.

### Thinning — acetic-surprise and uncrowned-bolt

Thinning used the existing synchronous `modify-landuse-coverage` operation,
dom 424 / cover `cancov` / saved value .3 or .5. Identity remapping is rejected
because its summary rebuild clears existing inrcov/rilcov override metadata.
The canopy endpoint preserves those stored .9/.8 fields and exact assignments;
MOFE ground cover remains the existing template .75 (no new activation).
Record the synchronous response rather than a nonexistent landuse job ID.

30% thinning archive `3e3322bb-a385-467b-8e38-68826ae1ce0e` verified 3,778 members;
`archives/acetic-surprise.20260918T131637Z.zip`, 987,472,974 bytes, SHA-256
`7fdebf8ca6054f20ff31d7c0a23d61f4a82e77bd35a5f09c76ad974c8d551daf`.
Same-value canopy request returned HTTP 200 at 15:00:43 UTC; 455-hillslope
management readback PASS. Exact 424:1021 / 90:43 / 200:1 assignments and all
three override fields retained; class424 canopy .30, effective ground .75.
Post-management soil proof and unchanged hashes PASS. Preparation
`6df0b254-d5a5-4d9b-8531-62da41910516` started 15:02:04 UTC.
Preparation 6/6 finished 15:05:30 UTC; full prepared readback PASS.
WEPP `743bda97-16b7-4436-b1f7-e1ad4dfd9830` started 15:09:11 UTC.
Finished 15/15 at 15:18:44 UTC. Final full readback PASS (455 hillslopes /
1,065 segments); all saved management metadata retained and soil hashes unchanged.
Fresh runoff 972.925870 mm/year, sediment 10,261.2636 tonnes/year; all 65 metrics
independently recomputed. Output SHA-256
`d7e703c8efacefd02e0be260dda5e44f6e3b98cfb4365b5ccad12c83b90966a8`.
Private anonymous denial and authorized exact downloads PASS; owner UI not tested.

50% thinning archive `e2aad4a0-286e-4b45-8fef-c5141f8540c5` verified 3,778 members;
`archives/uncrowned-bolt.20260918T132454Z.zip`, 985,449,010 bytes, SHA-256
`b8f11c13d4ecf5314d20d97ed913c08bb85176e3c6a79af0f35e135c764f3b44`.
Same-value canopy request returned HTTP 200 at 15:23:50 UTC; management readback
PASS with exact maps and all saved overrides, class424 canopy .50 / ground .75.
Post-management soil proof and unchanged hashes PASS. Preparation
`b84cea0f-f9fa-4fd5-be5e-9b8f3fd8e2e5` started 15:25:01 UTC.
Preparation finished 6/6 at 15:29:02 UTC; full prepared readback PASS.
WEPP `740dbc4d-90c7-4fb6-b346-b8234eaa489a` started 15:32:15 UTC.
Finished 15/15 at 15:41:51 UTC. Final full readback PASS, 455 hillslopes /
1,065 segments; saved scientific settings and management metadata unchanged.
Fresh runoff 947.851906 mm/year, sediment 7,200.9095 tonnes/year. Output SHA-256
`9fbb851c6e29a4e265e7a00c48a7822ee69284bdc17e9fbb184f3a6016349ff5`.
Private anonymous denial and authorized exact downloads PASS; owner UI not tested.

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
7. Complete that run's ledger entry and review it before starting the next
   scientific repair. Canonical preservation archives may run ahead for untouched,
   idle inventory targets, one archive at a time on the existing queue. Verify
   contents and reconfirm unchanged intent before each target's mutation; check
   disk headroom and shared I/O while archiving. This does not authorize parallel
   management, preparation, or model repairs.
8. Repeat until all eight runs, including baseline, are complete.
9. Regenerate the eight-row hillslope response summary and compare it with the
   original attachment.

## Final Summary Comparison

- Original file SHA-256:
  `042c546ee7ea9c61daf63967d2cc7ffcf4de2881739df31a95c0aa8c37bac063`.
- Repaired summary: [eight-row CSV](mofe-production-hillslope-response-summary.csv).
- Repaired summary SHA-256:
  `ba96a5381295dfa67b1f00c0d4fe5f6baa87b5241ed56d3eb77b23c98bd1ac51`.
- Eight scenarios, 66 original columns, 455 hillslopes and 22 simulation years
  per scenario. No response-vector equality remains. Original low/moderate/
  prescribed rows were identical, as were thin30/thin50; neither group remains.
- Inequality alone is not acceptance: all 3,640 hillslopes / 8,520 segments
  pass generated/prepared input checks tied to saved intent and fresh outputs.
- Reviewer conclusion: independent correctness PASS for all eight runs,
  including 520 recomputed numeric values; secondary QA evidence checks PASS.

| Scenario | Runoff mm/year | Sediment tonnes/year |
| --- | ---: | ---: |
| Baseline | 738.918169 | 128.4518 |
| Low | 941.757189 | 771.6286 |
| Moderate | 949.476160 | 979.6280 |
| High | 1046.572946 | 4513.5104 |
| SBS | 948.658728 | 2186.0559 |
| Prescribed | 904.907557 | 238.3798 |
| 30% canopy | 972.925870 | 10261.2636 |
| 50% canopy | 947.851906 | 7200.9095 |

Interpretation limits: the corrected baseline includes the saved class-200
bromegrass mapping; SBS retains its raster-derived forest assignments, so that
comparison is not fire-only. Large gross erosion/deposition remains a scientific
interpretation issue, not proof of interchange error. Thinning labels describe
canopy cover, not percent biomass removal; stored ground-cover metadata remains
inactive in MOFE and effective source ground cover stays .75. No parameters or
templates were tuned to obtain different outputs.

## Retained Evidence

[Production bundle](production-evidence.tar.gz), SHA-256
`ae4a365b4db44902135b36b2e2b7a1204271804df4e3a7b9e2650578f617aa80`,
contains per-role preservation/preflight, before/after states and manifests,
parsed management/soil checks, API receipts/job trees, fresh summaries, original
report, comparison JSON, and browser/download records. Tokens are excluded.
Full recoverable project archives remain in each production run's normal
`archives/` directory; exact paths and hashes are recorded above and in the bundle.
Source output hashes are also retained in [summary provenance](mofe-production-summary-sources.json).
Private-run owner-authenticated UI was not tested; normal anonymous denial and
authorized exact-byte downloads passed without changing access controls.

## Completion Gate

- [x] All eight pre-repair snapshots are retained and recoverable.
- [x] All eight sequences record job IDs or synchronous operation receipts.
- [x] Every terminal success is backed by parsed generated-input content.
- [x] SBS and global burn scenarios encode the intended effective classes.
- [x] Thinning managements encode 0.30 and 0.50 canopy respectively.
- [x] Refreshed outputs and summary are traceable to the repaired generation.
- [x] No direct file/NoDb patch or silent cleanup was used.
- [x] Independent correctness and QA reviewers accept the production evidence.

Package closure is prohibited until this checklist and the root tracker are
complete.
