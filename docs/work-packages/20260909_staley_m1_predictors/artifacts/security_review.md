# Security review: Staley M1 prepared predictors

## Findings

| ID | Severity | Surface and failure path | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Final source verification originally hashed only the initial companion set. Adding an external mask after initial discovery could change effective samples without changing the source TIFF digest. | `integration._sources` and `build_m1_predictors`; direct GDAL mask-addition probe and `test_added_external_mask_detected`. | Rediscover and compare the complete admitted source set before completion; translate added, removed, changed, or newly forbidden companions into `source_changed`. | Resolved; direct probe and regression pass. |
| SEC-02 | Medium | Filename admission did not constrain GDAL's implicit inputs. A VRT disguised as `.tif.msk` could read an unrecorded raster; an unrecognized `.tifw` worldfile could supply an unrecorded transform. GeoTIFF masks without GDAL mask flags were silently ignored. | `m1_inputs.companions`, `read_raster`; direct container probes, `test_disguised_vrt_external_mask_rejected`, `test_unrecorded_worldfile_rejected`, `test_external_mask_dnbr`, `test_external_mask_without_gdal_flag_rejected`. | Validate external masks as bounded, self-contained GeoTIFF masks with supported flags before base decoding. Restrict georeferencing to internal metadata and reject recognized worldfile companions. Preserve genuine GDAL external masks. | Resolved; direct probes and regressions pass. |

No high findings. These are source-integrity findings within the trusted local
contract; neither requires a hostile concurrent directory owner.

## Metadata and triage

- Package: `docs/work-packages/20260909_staley_m1_predictors/`.
- Reviewer: dedicated independent `m1_security` agent, 2026-09-09.
- Baseline: `0cac0f3a03295075aa805240f7e5b7209e1e2042`, uncommitted package changes.
- Scope: `integration.py`, `m1_inputs.py`, `docs/m1_predictors.md`, and
  `tests/nodb/mods/test_postfire_debris_flow_integration.py`; supplemental
  read-only review of [reproduce.py](reproduce.py),
  [reproduce_wallow.py](reproduce_wallow.py), and the Wallow fixture importer.
- Security impact: **high**; dedicated review required for new file preparation,
  subprocess invocation, and local artifact publication boundaries.
- Related correctness artifact: [correctness_review.md](correctness_review.md),
  final C01–C04 closure reviewed. Independent correctness runs passed 9 and 4
  targeted cases. This package requires correctness/security reviews; it does
  not require a separate QA artifact. Broader validation remains the executing
  agent's responsibility.

The caller authorizes explicit trusted local files and a trusted executable
identified by SHA-256. Source and output ancestor directories have trusted
ownership. Fresh private scratch directories are the only publication target.
No public upload, HTTP endpoint, NoDb mutation, RQ wiring, production deployment,
or hostile-directory concurrency protection is included.

Valid states include complete inputs, missing optional inputs, valid zeros,
negative normalized dNBR, partial/empty support, unresolved T, legacy provenance,
and supported internal/external masks. Missing optional inputs must retain other
predictor diagnostics; controls must not reject a genuine GDAL external mask.

## Verdict

**Gate: pass for the trusted local interface.** Unresolved: high 0, medium 0,
low 0. Final sign-off follows the closed correctness review and the validation
below. Accept the reviewed local security boundary; authentic-data acceptance
and any production shipping remain separate gates.

## Surface checks

| Surface | Assessment |
| --- | --- |
| Auth, sessions, JWT, CSRF | No changed service or browser entry point. The local caller is the authorization boundary. |
| Secrets | No new credentials, secret mounts, secret defaults, or secret-bearing arguments. |
| Input and deserialization | JSON objects only, finite-value validation, 1 MiB JSON cap; scalar GeoTIFF restriction with 512 MiB and 10-million-cell caps. No pickle/eval or shell interpolation. SEC-02 covers implicit GDAL inputs. |
| Filesystem | Explicit source paths are read-only; final symlinks and nonregular source files are rejected. Atomic directory creation reserves mode 0700 output; existing output is rejected. Parent symlink/concurrent-owner containment is outside the accepted scope. |
| Subprocess | Explicit binary path and digest, capability query, list arguments, per-process cwd, 300-second timeout, local exclusive logs. No global cwd mutation, shell, fallback tool, or queue changes. |
| Agentic tooling | No production permission, MCP, or role-configuration changes in scope. |
| Network | No intended external calls. SEC-02 closes GDAL's hidden-source route; production egress controls remain separately scoped. |
| Supply chain and CI/CD | Owned WBT plus existing NumPy/rasterio dependencies. Binary digest records identity; it does not establish trust in arbitrary caller-selected executables. No CI/CD changes. |
| Integrity and concurrency | Sources and prepared/output artifacts have SHA-256 identities. Final source rediscovery addresses SEC-01. Fresh output retains incomplete evidence on failure. No NoDb/Redis shared state changes. |
| Logs and recovery | Local logs and explicit error codes retain diagnostics. Absolute source/executable paths and copied outlet/K metadata are intentional local provenance; artifacts need audience review before any future public export. Retry in a fresh directory. |

## Validation evidence

Reviewer used `wctl exec -T weppcloud python -` with real rasterio/GDAL files in
temporary directories; probes left no source-project changes and performed no
network calls.

1. **Mask-set mutation:** create the test fixture; inject a real GDAL external
   DEM mask immediately after initial `_sources`. Base TIFF digest remains
   unchanged. After SEC-01 remediation, final discovery raises `source_changed`
   because the newly created `.msk` lacks expected provenance; no final manifest
   is published.
2. **Disguised mask:** write a 3-by-3 source GeoTIFF and a separate byte mask.
   Store VRT XML in `dem.tif.msk`, with `INTERNAL_MASK_FLAGS_1=2` and a
   `SimpleSource` referencing that separate mask. Before remediation,
   `companions()` admits the VRT and `read_raster()` reflects its masked center
   cell. The referenced TIFF is not included in companion identities.
3. **Worldfile alias:** write a source GeoTIFF with EPSG:32611 and no transform;
   add `dem.tifw` containing `30, 0, 0, -30, 500015, 3999985` on separate lines.
   Before remediation, `companions()` returns an empty list and
   `read_raster(target_grid=True)` accepts transform
   `[30, 0, 500000, 0, -30, 4000000]` from that unsigned sidecar.

4. **Remediation closure:** repeat both SEC-02 probes against the fixed reader.
   VRT mask and worldfile are rejected with `invalid_input`. A genuine GDAL
   external Byte mask is accepted with the expected 8-of-9 valid cells. External
   masks commonly lack georeferencing; the preflight correctly checks their
   dimensions and scalar type without requiring a separate CRS.
5. **Mask metadata:** an otherwise valid Byte GeoTIFF mask without
   `INTERNAL_MASK_FLAGS_1` was initially accepted and silently ignored by GDAL
   (9 valid cells instead of 8). The final reader rejects that malformed state
   with `invalid_input`. Direct file probes verify both supported values `0`
   (per band) and `2` (per dataset) preserve the expected 8-of-9 validity.

Reviewer regression command:

```bash
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_integration.py \
  -k 'external_mask or worldfile or source_digest or midbuild or existing_output or direct_executable_failure or resource_limit' \
  --maxfail=1
```

Result: **13 passed, 34 deselected**, 10.90 seconds, no skips. This selection
exercises real file/binary behavior, valid mask admission, invalid implicit
inputs, source changes, preexisting output preservation, a failing executable,
and a pre-decode resource limit. Existing dependency deprecations and the
expected unreferenced external-mask warning are nonfailing.

After final mask-metadata remediation, this additional selection passed
**4 tests, 46 deselected**, 9.93 seconds, no skips:

```bash
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_integration.py \
  -k 'external_mask_without_gdal_flag_rejected or external_mask_dnbr or disguised_vrt_external_mask_rejected or unrecorded_worldfile_rejected' \
  --maxfail=1
```

Artifact lint: `wctl doc-lint --path` this artifact passed, 0 errors/warnings;
`uk2us` preview is unchanged. `git diff --check` passed at final review.

The demonstration script copies fixed authentic project inputs to a fresh
scratch tree, checks statistics-only PAM XML, compares effective source/copy
arrays, masks and grids, and rechecks original file hashes. Its source paths are
fixed local evidence inputs. It does not weaken the runtime sidecar admission
contract or write project data. This review does not treat those incomplete
authentic inputs as complete T/F/S acceptance.

## Wallow archive and provenance addendum

The owner-supplied Wallow archive and project add an authentic local evidence
source; they add no runtime route, worker, publication, or acquisition behavior.
Reviewed `artifacts/reproduce_wallow.py`, the Wallow fixture
`import_archive.py`, fixture manifest/tests, and extracted source metadata.
No additional medium/high security findings.

Both scripts pin archive SHA-256
`423eb8b0edf87a733a1d441d64e11295b6fb65db3c18c30b00bab250998ecaaf`
before decoding. They use explicit member names with `ZipFile.read`, then write
fixed local destination names; they do not extract archive-controlled paths.
The fixture importer decodes the selected HFA members from a private temporary
directory and validates existing fixtures instead of overwriting them.
The project demonstration exclusively creates a mode-0700 scratch directory,
reads project files, validates copy samples/masks/grids, and checks original
hashes again. NoDb files are read as plain JSON; no object deserialization or
controller mutation occurs. Generated project copies and the source ZIP cache
are gitignored.

The initial project evidence used `originalBARC_20110701`, whose uploaded BARC
digest matched the project's upload at that checkpoint. Its dNBR and metadata are from that same
July 1 collection. Committed fixtures independently use `FinalSoilBurnSeverity`
and retain their June 23 identity. The archive does not justify relabeling the
July 1 project assessment as the field-validated June 23 final collection.

Independent container checks, using real archive and fixture bytes, passed:

- Archive SHA-256 and all three final fixture source-member/output hashes.
- Both retained final-collection metadata files match their archive members.
- July 1 project upload, extracted dNBR, and extracted metadata match the
  explicit July 1 archive members.
- A wrong ZIP containing a `../escape.txt` member is rejected at the archive
  hash guard. Fixture file hashes remain unchanged; no extraction occurs.
- The documented Python execution environment has assertions enabled. These
  scripts are fixed-archive development utilities using assertion-based
  verification, not generalized upload parsers or optimized `python -O` tools.

Initial July 1 evidence reviewed:
`artifacts/generated/wallow-final/evidence.json` and its bundle manifest.
An independent read-only container check verified all 23 original project file
hashes, 10 bundle source hashes, 5 prepared-file hashes, and 4 WBT output hashes;
archive dNBR/upload/metadata members and normalization/evidence/bundle linkage
also match. The actual executable SHA-256 is
`6647d55c2d8d28680addd16adc4d9d406857a7ccb394cd4260a2d61d7d8ffc42`.
The recorded execution identity is UID 1000, GID/group 993; output and bundle
directories are mode 0700. This is local evidence, not production parity.

That evidence completed processing with correctly **partial** scientific availability:
149 unknown intersections retain null T and null scenario probabilities.
Evidence and bundle predictor records agree, and no incomplete marker remains
in the successful bundle. The July 1 assessment limitation is explicit.
The earlier `generated/wallow` attempt is not the final evidence path.

Disposition: **pass** for the added local artifact/provenance scope. Source
identity and unavailable scientific results are preserved; no new medium/high
finding or runtime boundary expansion.

## Rebuilt final-polygon assessment addendum

Reviewed the subsequent `--assessment final-june23` branch in
`reproduce_wallow.py` and
`artifacts/generated/wallow-rebuilt-final/evidence.json` after the owner's
project rebuild. The branch requires the configured `_disturbed_fn` to name
the final polygon TIFF. It verifies the uploaded TIFF against the fixture's
polygon manifest, checks that manifest's archived shapefile-component hashes,
and verifies the exact uploaded-to-prepared SBS grid, mask, and class mapping.
It selects June 23 dNBR/metadata explicitly and rechecks original source and
provenance files before publishing local evidence. ZIP members are read as
bytes; embedded member names do not become extraction paths.

Independent read-only container validation passed for all 24 original project
and provenance file hashes, 10 bundle source hashes, 5 prepared-file hashes,
4 WBT output hashes, and the unchanged executable identity. The uploaded TIFF
matches the fixture output hash; all four archived polygon components and the
grid-reference hash match the polygon manifest. Actual source/prepared raster
reads confirm identical masks and the documented severity-code offset.
Evidence, bundle, and normalization records agree and identify June 23.

The final local evidence has complete processing and complete T/F/S support:
12,973 valid domain cells for each predictor, zero unknown intersections, and
three non-null explicit-scenario results. Output and bundle directories remain
mode 0700. The prior July 1 partial result remains historical evidence, not the
current assessment.

A direct negative invocation with `--assessment july1` against the rebuilt
project failed at the configured-source check, before model execution, bundle
creation, or evidence publication. All original project/provenance file hashes
remained unchanged. This verifies that the explicit assessment switch does not
silently attach the older imagery to the rebuilt SBS.

Disposition: **pass** for the rebuilt local evidence and its provenance checks;
no new medium/high findings. No runtime admission or production publication
boundary changed. Source readiness remains an observed local checkpoint rather
than automatic controller freshness enforcement. Artifact lint, spelling
preview, and `git diff --check` passed after this addendum.

## Residual risk and sign-off

Caller-controlled provenance is an identity assertion, not upstream freshness,
scientific validity, or authorization for production deployment. Trusted native
decoders and the pinned executable execute with the local caller's privileges.
Cell/file limits and subprocess timeout bound common costs; this interface is
not an isolation sandbox or a service concurrency quota.

Transient source changes that revert before the final hash check, hostile
directory owners, output changes after return, and crash durability across
power loss are outside the accepted local contract. Failed/partial bundles must
not be treated as active run results. Future public/worker integration requires
its own authorization, resource, mount/identity, and publication review.

Security reviewer: independent `m1_security` agent, signed off 2026-09-09.
Package owner acknowledgment: no risk acceptance requested or recorded.
