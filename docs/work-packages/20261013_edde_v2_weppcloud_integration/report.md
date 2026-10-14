# EDDE v2 WEPPcloud integration acceptance

Runtime candidate: `202ab65f3` (base implementation `d2ca5821b` plus reviewed published-calendar correction); contract checkpoint: `75b47f61f`; additive reader floor: `26c9e86ca`. Implemented and exercised on the forest development Compose stack. No production deployment was performed.

## Delivered behavior

Future EDDE v2 is an additive locale/catalog method with explicit model/scenario and full future years, Single or eligible Multiple PRISM spatialization, optional existing seed and supported precipitation scaling. Saved capability graphs retain their existing choices until explicit supported refresh. Historical EDDE and Multiple Interpolated are excluded. Raw EDDE precipitation/temperatures and the existing station-generated auxiliary fields follow ADR-0091; no added bias or elevation correction. ADR-0092 native PRISM temperature-ordering repair remains in use.

All required locations undergo native-cell eligibility checks; PRISM requires valid normals at the watershed and hillslopes. Source acquisition, replay, native revision and scaling occur in retained attempt directories. Publication validates actual final CLI contents, compares fresh inputs and uses existing atomic finalization/rollback. Failures preserve previous published climate. Reports identify the published source, station, period, seed, requested coordinates and native cell; diagnostic artifacts remain downloadable and archivable.

Durable contracts and rationale: [EDDE-WEPP-01](../../schemas/edde-v2-weppcloud-contract.md), particularly **Choices and compatibility**, **Acquisition, eligibility and execution**, and **Existing PRISM normal product identity**. User/operator guidance: [Future EDDE v2 climate](../../dev-notes/edde-v2-future-climate.md).

## Actual project and artifact evidence

| Case | Operation and result | Retained proof |
| --- | --- | --- |
| British Columbia, (-119.5310, 51.0063), 53 hillslopes | Single, MPI SSP3-7.0, 2060, seed 1001; real acquisition and full WEPP pipeline pass | `ca-job-tree.json`, `artifact-readback.json` |
| Idaho, (-116.8946, 46.8015), 83 hillslopes | Multiple PRISM, same projection/year/seed; real acquisition and full WEPP pipeline pass | `us-wepp-final-job-tree.json`, `artifact-readback.json` |
| British Columbia Multiple PRISM | Actual browser submission reaches RQ; rejects missing PRISM normals before annual weather acquisition and preserves prior publication | `negative-browser-submission.json`, `negative-job.json`, downloaded failed status |
| Malformed selection/auth | Invalid projection, year bounds, spatial method and AnnualMonthlies return 400 without changing climate NoDb or published CLI bytes; unauthenticated mutation rejected | `hostile-http-no-mutation.json` |
| Older saved US capabilities | Numeric17 and explicit catalog requests both rejected with unchanged climate state | `legacy-catalog-rejection.json` |
| Reader compatibility | Eight locale/input/OFE combinations reopen using committed reader-floor graph class/catalog plus current dependencies; stored config bytes unchanged | `reader-floor-reopen.json`; this is not a full rollback deployment test |
| Browse and download | Saved controls/report render; authenticated raw CLI/provenance/status/archive retrieval matches local SHA-256 | `browser-readback.json`, `browser-download-hashes.json` |
| Archive and restore | Canonical API/RQ operations preserve all 104 completed-case and 117 failed-case climate members; attempt directories remain 0700 | `archive-before-restore.json`, `archive-after-restore.json`, restore job receipts |
| Subsequent successful rebuild | Both prior completed and failed attempts retain exact bytes | `retention-readback.json`, `retention-rebuild-job.json` |

Every one of 136 prepared `wepp/runs/p*.cli` files matches its published source hash. All 136 fresh `H*.wat.dat` files parse into 366 finite daily rows for 2060, with precipitation matching the exact prepared CLI within output precision. The evidence script hydrates controllers in a fresh process. Both full job trees have 18 finished nodes, including watershed execution and interchange/export consumers.

The first US WEPP attempts correctly failed because the copied source project had no built soils or landuse. Those inputs were built through their existing authenticated APIs; final retry passed. These initial failures are retained separately and are not climate-method failures. A manually copied negative-test project also inherited the original run's workflow IDs; its inherited associations were removed only in that isolated clone before browser submission. Original projects were never rebuilt.

Existing PRISM source XML confirms the owned Wmesque 800m M4 normals use 1991–2020, precipitation mm/month and temperature C. Acquired response metadata identifies products but does not carry an explicit normal period; the contract states that limitation and retains actual raster/source hashes. Original source metadata is retained under `artifacts/prism-source-metadata/`.

## Runtime and acquisition limits

Configured worker, API and browse processes run as UID 1000/GID 993, groups 993; worker umask 0022. Acceptance uses the canonical writable `/wc1` run mount and existing source bind mount. Attempt directories retain 0700 through archive restore. See `runtime-environment.json`. Existing climate RQ timeout is 216000 seconds. Each real 2060 weather acquisition planned 1,164,990,696 bytes; private annual caches use the existing four-billion-byte budget and discard raw NetCDF after retaining manifests/extracted records. Multiyear total transfer can be much larger. No new dependency, queue or privilege was introduced.

## Validation status

- Focused catalog/parser/router/RQ checks: 187 passed; later schema/EDDE checks: 97 passed; final review regressions: 45 passed. These runs overlap and are not summed.
- Frontend: 118 suites/980 tests passed; lint passed after replacing an existing conditional assertion in the climate test with parameterized expected labels. Final climate controller rerun: 19 passed. Bundle rebuild completed.
- Climate stubtest and test-stub inventory passed.
- Changed broad-exception enforcement against the integration ancestor passed with net delta 0. The origin/master comparison flags an earlier PRISM helper allowlist line drift outside this integration; no new broad catch was added.
- Code-quality observability completed; retained report is non-blocking telemetry. New builder keeps collection, validation and publication ordering explicit; existing large schema/parser owners remain shared integration points.
- Scoped documentation lint passed. Independent correctness and security reviews pass runtime candidate `d2ca5821b` with no unresolved findings; security final focused run passes 59 tests. Full Python suite remains running; its final result will be recorded before closeout.

## Remaining scope

Production rollout is separate work. Preserve reader floor `26c9e86ca` after any additive graph has been saved. Existing source availability, coarse-grid bias/elevation limits, station-derived auxiliary fields and automatic-seed reproducibility limitations remain disclosed; none is silently corrected or waived.

## Final audit corrections and broad-suite disposition

A valid replacement period previously changed `input_years` before staged publication, and `calendar_start_year` preferred pending future bounds. Both could misdescribe retained climate after a failed rebuild. EDDE now updates simulation length only during successful publication and reads downstream calendar start from the active CLI. Other methods retain their existing precedence, including CLI-backed readers without mode metadata. A live 2061–2062 request with generic `input_years=99` failed PRISM eligibility while retaining the published one-year 2060 climate and exact CLI hash; see `failed-period-readback.json`. Parser/legacy CLI/EDDE regressions pass 62 tests. Both independent reviewers accepted the bounded amendment.

The initial broad run stopped after 2,783 passed/48 skipped on `test_ag_fields_config_defaults_new_projects_to_capacity_32_wepp`: it expected 260714 even though accepted ADR-0089 and commit `69cfd68aa` changed the default to 261010. Corrected the stale in-memory/persisted expectations and obsolete capacity-specific test name; no agricultural runtime or configuration changed. All 34 tests in that backend-contract module pass. Original failed output is retained in `broad-initial-failure.log`. The continuation excludes only files that completed in the initial run; its exact arguments are retained in `broad-continuation-command.json`. This is segmented coverage, not a claim that the original run passed.

Final worker replay after the calendar amendment: Canadian job `c5b3fd2d-5f7a-4bbd-8f8c-757348fb4d4f` and US job `b29c389e-e8f6-4638-8404-e36fabc2cd3c` each finished all 18 nodes. Fresh output readback again matches all 136 prepared climate files and their 2060 daily precipitation. See `final-calendar-wepp-job-trees.json` and refreshed `artifact-readback.json`.

The first continuation stopped after 2,329 passed/4 skipped on the current named-preset catalog expectation, which omitted the newly added EDDE choice. Updated only current US/Canada expectations; historical saved graph expectations remain unchanged. The next continuation again excludes only completed files. Results and exact argument lists remain separate so repeated tests are not summed into a misleading unique count.

The second continuation stopped after 102 passed/1 skipped on the same missing current EDDE registry membership. Corrected the component set and current US builder-description list. The registry/catalog/control-render sweep then passed 299 tests. The final continuation enumerates all 395 remaining existing test modules from the collected node cache, cross-checked exactly against test files on disk at/after that boundary; it avoids costly repeated exclusion scans without omitting remaining tests.
