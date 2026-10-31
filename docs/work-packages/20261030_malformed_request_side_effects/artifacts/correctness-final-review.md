# MRS-01 final correctness review

Reviewer: independent `rq_contract_review` agent. Scope: RQ request adapters,
webhook ordering, declared flag/numeric consumers, multipart resources, and shared
upload promotion. Production code was reviewed without edits; this artifact is the
reviewer's only authored implementation-phase file.

## Verdict

No open correctness findings remain in the reviewed scope. The previously reported
source-loss, late-validation, valid-upload, and error-translation defects are closed
by current source inspection and the focused evidence below. This is a local
correctness verdict, not deployment approval or a claim of production observation.

The original contract checkpoint is `3ab204e9c`. Follow-up checkpoint `ca28085ac`
contains the independently approved amendment to
[the request contract](../../../schemas/request-payload-contract.md). Its reviewed
file blob is `b2be0cbb021c31f38b89651b4e5c83f0349b04e9`. The operator authorized
that checkpoint; the implementation owner reports restoring its dependent code
after the checkpoint commit. The amendment explicitly bounds active-mode Ash
fields, configured WATAR concentrations, agent TTL sentinels, and existing batch
directive keys without introducing scientific ranges or changing ignored keys.

## Findings closed

| Finding | Final behavior and evidence |
| --- | --- |
| Malformed transport became empty/default input; scalar flag containers/text enabled work | Shared typed validation reaches canonical errors through real route wrappers. RHEM aliases, deliberate defaults and false remain distinct. `test_request_payload_conformance.py`, `test_malformed_route_matrix.py`, and RHEM route/worker-boundary tests cover these paths. |
| Multipart errors could bypass bounded parsing or leak spools | Exact media-type selection, completion checks and cleanup cover rejection, disconnect, cancellation and operational failures. Generic and single-input parser tests exercise actual streams. |
| Invalid replacement uploads deleted accepted sources | Complete stream and content validation precede promotion. The reviewer reproduced same-name malformed GeoJSON deleting the original, then reran the real route after repair: HTTP 400 with original bytes preserved. Helper and batch tests retain invalid-replacement and valid-follow-up assertions. |
| Staging broke valid relative VRT dependencies | Validation uses a temporary sibling, preserving relative dependency resolution and uploaded bytes. The reviewer reproduced the temporary-directory failure with real GDAL; `test_staged_vrt_preserves_relative_raster_dependencies` verifies the repair and staging cleanup. |
| Treatments staging violated the controller's directory contract; mapping checks occurred after promotion | Prospective mapping loading and pure raster validation precede source promotion, mapping persistence and mode application. `test_treatments_upload_persistence.py` uses real HTTP, NoDb and GDAL, verifies unchanged rejected state, then reads persisted mode and generated raster values after a valid follow-up. |
| Ash, landuse and soils could apply earlier fields before rejecting later inputs | Ash validates date, active-mode numeric fields and upload metadata before application. Landuse validates upload/reuse and MOFE lookup before assignment; soils validates supplied numeric fields before source promotion. Existing omission/conversion policies remain in force. |
| SBS sanity checks missed all-nodata rasters; HUC created projects before source validation | Both Baer and Disturbed branches reject the existing invalid all-nodata condition before replacement. HUC metadata and existing read-only raster checks precede creation. Tests use real raster bytes and assert retained source/no application or no project creation. |
| Declared sentinel semantics and numeric error translation drifted | Named blank-as-false form repetitions remain compatible; Polaris/RUSLE blank values reject; WEPP sparse flags remain distinct. Expected numeric overflow and invalid MOFE lookup errors reach validation responses. |

The review withdrew two broader concerns after tracing actual behavior: ordinary
controller/cache hydration alone was not evidence of a business mutation, and the
cover-transform controller has no existing CSV-content validator to move earlier.
No new CSV schema or general rollback requirement was introduced.

## Retained test evidence

The reviewer inspected these execution logs and their test selections:

- `/tmp/mrs-final-boundaries.log`: **220 passed**, including Treatments persistence,
  shared upload boundaries, both SBS branches, HUC, batch uploads, malformed RQ
  routes, real framework conformance and Flask batch endpoints.
- `/tmp/mrs-followup-tests.log`: **175 passed**, covering the additional Flask,
  parser and batch changes following the second checkpoint.

These counts describe separate invocations, not a deduplicated test total. The
reviewer also executed disposable real-GDAL and isolated HTTP probes during the
finding/closure cycle; no production run or queue was exercised. The permanent
regression tests, rather than temporary probe scripts, retain those cases.

## Evidence limits and handoff

At review time, the required full-suite rerun in `/tmp/mrs-full-final.log` was still
in progress. This review does not claim that gate passed. The implementation owner
must retain its final outcome and remaining required checks in the package's gate
record and tracker.

The [consumer matrix](consumer-matrix.md) owns the wider route dispositions and was
being reconciled at review time. Parser conformance and this RQ review do not prove
that every record in the discovery index was independently executed. Controlled
auth/queue boundaries and disposable local data establish rejection/application
behavior; they do not establish production identity, deployment or live workflow
parity. Later storage, native computation and queue failures retain the contract's
existing failure semantics and are not promised arbitrary rollback.
