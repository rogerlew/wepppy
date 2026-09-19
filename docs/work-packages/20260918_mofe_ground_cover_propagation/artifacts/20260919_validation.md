# Forest validation evidence

Candidate `0fd1a6eca`; contract ancestor `824457074`, base `8dbf8f037`.
Production `landuse.py` SHA-256 (candidate and runtime match):
`db3241ffd64888aafe8dcb7425d0e337beb235a5a2fdd831be471a2064d4c7d2`.
Forest dev API/default/batch workers were idle before targeted restart. API,
worker and validation process identity is UID 1000/GID 993, group 993.

## Tests and independent reviews

The pre-fix real-management regression failed: selected interrill 0.0 produced
0.75. After correction, 62 focused tests pass (real combined/prepared parser,
process pool, independent values, zero/one, legacy absence, disturbed precedence,
RAP canopy, missing assignments, writer failure/retry and summary preservation).
Expanded focused run: 93 tests pass, including three explicit single-OFE cases
and the full canonical archive suite. Three ground-record archive/restore cases
cover working, failed and completed management/diagnostic records. Stub completeness passes.
Broad `wctl run-pytest tests --maxfail=1`: **9,044 passed, 99 skipped**, exit 0,
1,543.48 seconds. The six late-added single-OFE/ground-archive cases were not in
that collection; they pass in the separate 93-test run. Scoped docs lint has zero
errors/warnings; diff whitespace and changed-file broad-exception gates pass.

Independent contract reviewers `/root/ground_contract1` and `ground_contract2`
approved before ancestor commit. Their artifact-acceptance finding was resolved.
Final code reviewer `/root/ground_correctness` found no production blocker;
validator inventory completeness finding was corrected with key equality and
exact 455-hillslope/1,065-segment assertions. Independent final evidence review
passed, including a fresh post-restore validator run.

## Supported source and workflow

Source `/wc1/runs/eq/equestrian-bonheur`, `canada-wbt-mofe`, `wepp_260803`.
`cover_defaults_d=None`. Fork API used `undisturbify=false`,
`skip_wepp_runs_output=true`, `skip_omni_scenarios_contrasts=true`, destination
`mofe-ground-cover-validation-20260918`. Fork job
`aca432a3-29cd-453d-b3e6-71cd9d9e8b08` finished 2026-09-19 04:11:10 UTC.
Source landuse/soil/WEPP NoDb hashes are pinned in `validate_forest.py`.

Normal coverage API set class 406 `inrcov=0.9`, then `rilcov=0.9`; both HTTP 200.
Class and canopy remain low severity/0.75. Identity mapping API 406→406 job
`8c6ce840-0f4b-4d7c-9001-d1b72eeb13ea` finished 04:16:56 UTC; fresh summary
readback retained both overrides. This is a validation-only ground edit, not a
new canonical low-severity parameterization.

Every combined and prepared file passed semantic checks: 455 hillslopes,
1,065 segments, 910 management files, covers 0.75/0.90/0.90. Source still parses
0.75/0.85/0.85 and its three NoDb hashes remain unchanged. The script emits
complete relative-path SHA-256 manifests for both target and source managements.

## Execution and validation correction

Initial parent `50cf0f92-54e8-47eb-bebc-9dd5a74a716d` was submitted with `{}`.
Input parity check caught the existing parser clearing saved `_kslast=0.0001`
when the field is omitted; prepared soils then retained source-profile bottom
conductivity instead. This attempt proves cover propagation but is not accepted
as a cover-only numerical comparison. It is superseded by an explicit-payload
rerun with `kslast=0.0001`, `initial_sat=0.75`, `wepp_bin=wepp_260803`.
No production code outside the ground-cover defect is changed.

Corrected parent: `64167456-bc50-4b40-9d19-da3715de63ba`, started 04:24:52 UTC.
Prepared input parity passed all 455 hillslopes: climate/slope bytes identical,
parsed soils identical (excluding provenance comments), and canonical management
serialization identical after normalizing only interrill/rill cover to the source
0.85. Thus no other checked prepared hillslope inputs differ in this comparison.
Watershed/channel input parity is not separately claimed.
The two complete 910-file source management manifests remained identical:
SHA-256 of `jq -S '.source_management_hashes'` output is
`142e5a8563dc73d53fb81d9114b1dad59479d84672a91a8199cc74e8b02bfcf0`.
Target manifest SHA-256 (`jq -S '.management_hashes'`):
`0cb3a94c863bc22379e5ed1090c32b891f215e7da13787ebe3949ab8b4433f59`.

Corrected parent and all 14 children finished 04:32:27 UTC. WEPP executable SHA-256:
`4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`.
Fresh 22-year output contains exactly the 455 expected unique hillslope IDs and
finite runoff/area/sediment metrics. These are measured outcomes, not acceptance
thresholds or new defaults:

| Metric | Original 85% ground | Validation 90% ground |
| --- | --- | --- |
| Area-weighted hillslope runoff, mm/year | 942.001705 | 942.933781 |
| Sum hillslope sediment yield, tonnes/year | 3497.9702 | 3348.4272 |
| Outlet sediment discharge, tonnes/year | 3195.7 | 2983.1 |

Fresh `loss_pw0.hill.parquet` SHA-256:
`cc7c81fc8be56a15713c7d808b21ba53729519338671469ab2add1d165e96ee1`.
Source output SHA-256:
`31190d1549e53c0f3b00816fe464860912bf41333abf5942675c6d8b4cc5293d`.

## Browser/download and archive

Headless Chromium loaded the normal Forest run page, passed its CAP gate and
found the landuse form. All three authenticated normal downloads returned HTTP 200
and byte-matched local files:

- `landuse/hill_101.mofe.man`: `617a1aa092a3f5c4b18931b191ca86d2ac0cd415e6c1699205adf5d9e097fdd2`.
- `wepp/runs/p1.man`: `6e2102ab3609a176a3a727ca257048f8f8ecdb8e4d7fdd922db42a54e6926dbe`.
- Fresh `wepp/output/interchange/loss_pw0.hill.parquet`: HTTP 200 and exact match
  to the corrected output hash above.

Reusable browser and readback scripts are retained alongside this evidence.
Archive job `972c864f-7e6d-4b78-8508-b48b911b29c5` finished 04:35:38 UTC.
Archive `archives/mofe-ground-cover-validation-20260918.20260919T043237Z.zip`
SHA-256 `1a42b1bb90dc9ec8d6f58e140902b722f30226527ff09b5df4833e563997d294`.
All 910 management members match current bytes, and NoDb files, landuse/WEPP
logs and fresh output are present. Pre-restore full semantic/input/output parity
passes. Supported restore job `665ea9c9-ff43-4550-a7fc-363432c5ae42` finished
04:38:17 UTC. Full post-restore cover/input/output checks pass and the entire
readback JSON is byte-identical to pre-restore (SHA-256
`5d52ed6e988de465df00fc5876bd5b0db4c39e2298086c3b67d75889c06be40b`).
This verifies all 910 management member bytes, scientific input parity, fresh
results and unchanged source NoDb/managements across canonical restoration.
Discovery metadata for those operations
returns 404 even though canonical OpenAPI lists both routes; request fields were
verified against the existing route contract/source, not invented. This is a
pre-existing metadata limitation, not authority to redesign those APIs here.

## Remaining scope

All execution gates and final independent evidence review pass. Production
deployment and production-project repair remain outside scope.
No production deployment or project repair; original equestrian-bonheur remains
the user's untouched low-severity run. `hysterical-sourdough` remains unrepaired.
