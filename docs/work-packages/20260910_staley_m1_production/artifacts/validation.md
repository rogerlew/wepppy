# Production M1 validation

Status: completed 2026-09-10. Development browser/worker acceptance and required
validation gates passed.
Runtime changes are uncommitted. Contract ancestors: `5c0a172ee`, `595816476`.

## Actual browser and worker workflow

Development host `wc.bearhive.duckdns.org`, disposable project
`pfdf-smoke-d9fc3c69`, config `disturbed9002_wbt`. Controlled synthetic 10 m
terrain/SBS/K/dNBR with real project NoDb owners and ClimateFile parquet export
from the repository's test climate. This validates workflow and preservation,
not regional scientific accuracy. Existing authentic Wallow predictor/rainfall
validation remains in the predecessor packages.

[Browser script](browser_smoke.cjs) and [passing log](browser_smoke.log) verify:

- Auto resolves the uploaded ×1000 map and publishes the new accepted ID.
- A new RQ M1 job completes, its accepted result ID matches the attempt and
  freshness is current. The authenticated events download is 129,050 bytes.
- Accepted filename survives reload; 10 m displays as 33 ft under English units.
- The out-of-study-range warning remains nonblocking; unavailable NOAA is disabled.
- Ambiguous replacement preserves accepted dNBR. Explicit scale correction
  succeeds from the retained candidate, without retransferring the map.
- [Keyboard smoke](keyboard_smoke.log) verifies tab order from the raster picker
  through scale, upload, rainfall source and Run; native select keyboard behavior,
  associated dNBR label and live status role are retained. This is targeted UI
  behavior evidence, not a full accessibility conformance audit.
- Removing/restoring the actual Climate completion timestamp changes prerequisite
  readiness and Run availability through the real preflight connection.

[Rendered control](control_completed.png) and [RQ job trees](live_jobs.json)
record actual execution. All four exact jobs finished. Web/rq-engine/worker share
the development Compose run mounts; worker UID 1000, GID 993, umask 0022, durable
NoDb mode 0644. Accepted files were downloaded through the authenticated route.
The partial result is expected from the short climate sample's unsupported ranks;
missing probabilities remain unavailable rather than fabricated.

The full synthetic run page has an unrelated Soils report error because it lacks
complete watershed report metadata. The M1 control, upload, model, download and
preflight paths passed independently on that page. This fixture is disposable.

## Regression and gate results

- Production: 14 tests passed, including actual NoDb owners, real raster pipeline,
  verified predictor reuse, upload source races, publication reconciliation,
  feature enablement and owner freshness.
- Encoding: 9 tests passed, plus frozen real-product evaluation in
  [auto_scale_evaluation.json](auto_scale_evaluation.json).
- Transport: 17 tests passed; actual multipart/disconnect/handle boundaries,
  invalid requests, authorization/config/readonly checks and candidate binding.
- Climate export: 12 passed. Test doubles now include the real owner's `wd`
  required for postfire publication notification.
- OpenAPI: 13 passed, including route metadata and canonical budget checks.
- Frontend: lint passed; 109 suites, 841 tests passed.
- Preflight: `wctl run-preflight-tests` passed, including unchanged-checklist frame
  delivery after an opaque domain revision. Native host Go is older than the
  module toolchain; the canonical builder is the validation authority.
- RQ graph/catalog: 145 edges, regenerated and verified; actual job trees checked.
- Broad-exception gate and test-stub completeness passed.
- `wctl run-stubtest wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow`
  passed. The new facade has a matching typed stub. A package-wide attempt also
  traverses existing scientific helpers and stops on missing rasterio/pyarrow/WBT
  typing and pre-existing inferred dictionary annotations; it is not a passing
  package-wide typing claim.
- Full Python: **8,312 passed, 77 skipped**, 939.28 s. The three newly added
  reconciliation/enablement cases passed in the separate 14-test production run;
  they were added after full-suite collection.
- Module/package and affected shared-document lint passed; `git diff --check`
  passed. Spelling normalization was previewed; unrelated existing text and
  code identifiers were preserved.

The real [receipt regression](runtime_regression.py) injects Redis marker failure
and asserts exact planned receipt recovery, no reuse of a previous job and durable
state restoration. It uses real Redis/NoDb against this disposable run only.

Earlier browser drafts advanced before the expected operation completed and
could accept an earlier filename/result; they are not acceptance evidence. The
retained script explicitly polls exact job phases and checks accepted IDs. An
atomic reconciliation race found during this work also has regression coverage.
An earlier full-suite run was interrupted by a development-container restart;
subsequent failures in OpenAPI size and a Climate test double were corrected.
Only final successful runs establish the gates.

## Installation and handoff limits

[Local WBT install](local_wbt_install.json) records the owned release build,
capability check, hash and backup. The development worker executed StaleySlopeSbs.
No production host installation or deployment occurred. Other hosts require the
canonical WBT release cutover and actual workflow preflight before rollout.

The owner can enable Post-fire debris flow in an eligible WBT project, prepare
POLARIS Nomograph K through RUSLE plus soils/SBS/climate, upload dNBR and run M1.
The intended next acceptance is the owner's real 10 m burned watershed. Reports,
event dashboard and production M3 are deferred. Display units do not change SI
model files. Retained private attempts are not automatically deleted; operator
cleanup may remove only verified unreferenced directories.

Independent [correctness/UI](correctness_review.md) and [security](security_review.md)
reviews approved the implementation with all medium/high findings closed. Their
final full-suite/browser conditions are now satisfied.
