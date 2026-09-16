# Kf implementation security review

Status: **PASS — final security disposition; zero unresolved findings.**
Reviewer: independent `security_reviewer` agent (`contract_security`).
Review time: 2026-09-16T22:56:52Z. Accepted contract ancestor and current HEAD:
`9395f4722dd09128b6391cb428f6b7b5e8cbbe6a`. Scope: working implementation
diff against that ancestor. Final live evidence reviewed 2026-09-16 UTC.
This disposition closes the package security gate, not the still-running full
test-suite gate or unrelated production deployment authority.

## Findings

| ID | Severity | Exploit or failure path and evidence | Required remediation | Status |
| --- | --- | --- | --- | --- |
| IS-01 | Medium | Original `kf_source.acquire_kf` opened a mutable native pathname with unrestricted GDAL decoding; a substituted VRT could read beyond the source boundary. A real-file probe confirmed this behavior. | Repaired with bounded `io.open_local` bytes, acquisition hash verification, GTiff-only `MemoryFile`, disabled sidecar discovery and final retained-native hash equality. Real-file valid/substitution/post-decode-replacement regressions passed. | Resolved 2026-09-16T23:07:50Z |
| IS-02 | Medium | Original `production.execute_model` could accept the old model/frequency after the selection endpoint changed them during processing. | `check_attempt` now verifies attempt ownership, phase, snapshot, active dNBR and selections before/after preparation and inside publication. Acquisition-time model/frequency changes and final-lock frequency change tests preserve previous acceptance and passed. | Resolved 2026-09-16T23:07:50Z |
| IS-03 | Medium | Original new-M1 source snapshots retained POLARIS completion, invalidating Kf results after an unrelated change. | POLARIS completion is excluded for explicit Kf M1; legacy checks remain. The real-owner source-dependency regression passed. | Resolved 2026-09-16T23:07:50Z |

All code findings are resolved without risk acceptance. Repairs remain within
the accepted contract; they introduce no new service, cache or workflow.

### Repair re-review

The native decoder repair now uses `io.open_local`, a bounded immutable byte
snapshot hashed against child evidence, and GTiff-only `MemoryFile` with PAM and
directory discovery disabled. Before completion it compares the retained native
pathname's bytes to that same snapshot hash, so a later replacement cannot
become a newly blessed native hash in the manifest. The reviewer inspected the
final check and `test_native_replacement_after_decode_cannot_be_blessed`.

The inspected `check_attempt` repair for IS-02 checks identity, model, phase,
snapshot, active dNBR and selected model/frequency before/after acquisition and
inside final locking. Added production tests change model/frequency during
acquisition and frequency immediately before the real final state change,
asserting that prior acceptance survives. IS-03 now has a real-owner source
snapshot regression verifying independence from POLARIS completion and retained
legacy checks. The reviewer inspected the successful execution logs:

- `wctl run-pytest tests/nodb/mods -k postfire_debris_flow --maxfail=1`:
  **633 passed**, 1047 deselected, 196.44 seconds. Retained log:
  [module-tests.log](logs/module-tests.log). This includes Kf boundary tests, production
  selection/publication regressions and model-source dependency regression.
- `wctl run-pytest tests/rq/test_project_rq_archive.py -k postfire --maxfail=1`:
  **1 passed**, 21 deselected, 9.99 seconds. Retained log:
  [archive-test.log](logs/archive-test.log). The canonical archive test includes Kf range,
  native raster, publisher metadata and failed/incomplete record categories.

The archive regression uses fixture bytes. Live generated-file archival evidence
was subsequently supplied and independently checked as recorded below.

## Review method and concrete evidence

Reviewed `kf_source.py`, `source_transport.py`, `integration.py`,
`predictor_v2.py`, `production.py`, `rainfall_io.py`, result/report changes and
the accepted/Redis advisory policy dispatch. Inspected inherited source
supervision, M3 preparation, local raster and descriptor helpers, state locking,
the selection route and existing boundary tests.

The IS-01 probe created one 1x1 GeoTIFF outside a disposable attempt and a
VRT referring to it under the name `attempt/native_kf.tif`. The original
alignment opening operation returned:

```text
{'decoder': 'VRT', 'external_sample': 0.4169999957084656, 'filename_suffix': '.tif'}
```

This exercised real GDAL decoding and file reads without network access. It
demonstrates the original missing format boundary, not a remotely reachable
write primitive. The threat model already includes malformed and concurrently
replaced project files. The scratch directory was removed after the probe.

No runtime implementation or tests were changed by this reviewer. Review
messages were delivered promptly so the parent could repair the findings while
completing its implementation and validation work.

## Surface assessment

Security impact remains **high** under package policy because source acquisition,
filesystem decoding, worker processing and report payloads change. This does
not mean the observed findings have high severity.

- Fixed network endpoints remain internal constants. `RangeFile` accepts only
  THICK/KFFACT, defaults to THICK for existing callers and pins strong ETag,
  exact ranges, object length and final identity. The changed code adds no
  redirects, retry loop or user-selected endpoint. Existing process supervision
  remains in use; final tests must exercise Kf through it.
- Predictor schema 3 validates exact source policy, preparation manifest identity,
  immutable artifact inventory, target grid and actual common-mask Kf mean. It
  does not follow provenance strings as arbitrary paths. Old schemas retain
  their dispatch; invalid policy is rejected.
- Retained source requests, raw bodies, native/aligned rasters and source metadata
  remain under visible attempt paths. Accepted production records include the
  Kf directory's files. Final ordinary-browser and real archive checks below
  confirm this layout is inspectable and preserves generated bytes.
- Report reads remain on existing authorized routes and accepted-attempt checks.
  Curve evaluation is bounded to the contracted sample count, and new textual
  CSV context still passes through the existing escaping function. No new
  endpoint or credential surface was observed.
- Advisory preflight branches only on explicit Kf policy; absence preserves
  legacy tasks and unknown policy cannot claim completion. The projection is
  not authoritative artifact validation.

## Valid-state and final acceptance obligations

The first valid Kf run must work without a preexisting Kf directory, RUSLE or
POLARIS artifacts. Present-empty and failed attempts must remain inspectable,
and retry must create a fresh attempt. Legacy M1 and M3 must remain usable.
Security repairs must not reject these states or silently initialize optional
state during reads.

Reviewed focused tests exercise real changed file and publication boundaries,
including preserved acceptance after superseded work. Existing bounded transport
tests remain applicable to the fixed-source extension; both live runs also used
actual KFFACT acquisition. Fixture archives cover failed/partial records, and
real generated archives cover completed source/result records. Correctness and
dedicated UX have separate artifacts; the root agent owns QA/test evidence under
this package's accepted review plan.

## Final live evidence

- [Restart validation](forest_restart_validation.md) records the authorized
  installed development Compose restart and preflight recovery after Redis
  `LOADING`. No other-host deployment or push is claimed. Normal workers then
  completed both recorded browser submissions.
- [Named run](nervous_mesquite_e2e.md) and [generic no-RUSLE run](generic_e2e.md)
  have finished job trees, accepted schema-3 identities, actual bounded-source
  request evidence and source browse status 200. Each browser evidence file
  records all five downloaded artifacts. The reviewer independently matched
  all ten attachment hashes to their corresponding accepted archive records.
- The generic fixture begins without RUSLE/POLARIS artifacts or completed tasks.
  Its normal upload/run succeeds, and postfire remains visible and current
  immediately after RUSLE removal and after both reloads. The named run and
  materially different fixture use the same generic source preparation.
- [Preservation evidence](nervous_preservation.json) reports 387 protected
  files, no scientific changes and no replaced earlier attempt files. The sole
  byte difference is `climate.nodb`'s serialization timestamp; its scientific
  settings remain equal. This is recorded explicitly rather than claiming
  every protected file was byte-identical.
- [Named archive](nervous_archive_roundtrip.json) and
  [fixture archive](fixture_archive_roundtrip.json) retain canonical archive/
  restore results for isolated module copies. The reviewer read every restored
  file and independently recomputed all **137 + 62 hashes**, with zero
  mismatches. They include request bodies, native/aligned Kf, publisher metadata,
  preparation/predictor manifests, results and historical attempts. The archive
  harness substitutes orchestration dependencies only for isolated copies;
  this proves real member selection and restoration, not production restore
  API authorization. No live project was restored.
- [M3 browser evidence](browser_m3/browser.json) records ordinary browsing and
  downloads, no model mutations or page errors, explicit stale identity, and
  23 unchanged protected files. Missing rainfall provenance stays unknown.
- Named and fixture numeric evidence matches retained raster means, every saved
  event/design/inverse result and displayed-unit curve exports. This supports
  source/artifact integrity; it is not a predictive-calibration certification.
- Retained browser JSON/log/source evidence was checked for serialized bearer
  headers and JWT material; none was found. Login credentials are read from the
  existing environment file and not recorded in the evidence. This scoped check
  is not a general secret-scanner certification.

The independent correctness code review and dedicated UX review both report
no unresolved findings. The root agent's final QA record owns broad test-suite
completion; security sign-off does not require a separate QA-agent approval.
The full pytest sanity run was still running when this final disposition was
written, so its completion is not claimed here.

## Final verdict

**Security gate PASS: zero unresolved high, medium or low findings.** Code,
retained tests and real forest acceptance satisfy this bounded security review.
Residual risks are the documented trust in the external publisher, existing
legacy readers/host boundaries and the limited scope of automated browser
evidence. No new risk acceptance is required. Final package closure still owns
the full-suite result and completion of its final documentation records.
