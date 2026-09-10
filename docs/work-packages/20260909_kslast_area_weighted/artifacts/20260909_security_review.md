# Security review: project-grid area-weighted kslast

## Findings

| ID | Severity | Surface | Description and exploit path | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Run-tree writes | The initial writer followed an existing `soils` directory symlink outside its run. A substituted run-tree entry could redirect or overwrite the two fixed artifact names in another writable directory. | Independent real-raster/container reproduction created both artifacts outside a temporary run; initial `prepare_kslast_map` used `is_dir()` without containment. | Resolve the existing root, require containment within the resolved run, preserve legitimate in-run aliases, and verify both states. | Resolved: the revised collaborator checks containment and uses the resolved directory; independent unmocked recheck passed. |

No unresolved medium/high security finding remains. Final native-installation,
restart, full-run, and artifact-secret checks passed the security review.

## Metadata

- Package: `docs/work-packages/20260909_kslast_area_weighted/`.
- Reviewer: independent `security_review` agent.
- Date: 2026-09-09 UTC.
- Final code context: WEPPpy `master` at `9e1c48f4d`; wepppyo3 source `125edc1565a37f629889278e3560b1a0af4b44d2`, release `d6641ab`. Initial contract ancestors were WEPPpy `febd8f2d3` and wepppyo3 `072aed8`.
- Scope: `kslast_map.py`, ordinary/MOFE caller changes, `raster_stacker`, native `raster_characteristics/src/area_mean.rs`, wrapper/export, tests, integration runner, baseline and installation evidence.
- Authority: [kslast contract](../../../schemas/kslast-map-contract.md), especially Generic native boundary, WEPP preparation and provenance, and Directory-only runtime boundary.
- Related correctness review: [independent review](20260909_correctness_review.md).
- Owner quality/QA disposition: [validation](validation.md#owner-qa-disposition); reviewed after the broad suite completed successfully.
- Final runtime evidence: [release manifest](release_manifest.json), [restart identities](restart.json), [completed job tree](integration-jobs.json), and [full-run verification](integration-verification.json).

## Security Triage Decision

- Security impact level: **high**, using the repository's default triage for file/path handling and native installation boundaries; this is not a finding severity.
- Dedicated security review required: **yes**, also explicitly required by the execution package.
- The changed surface is a new run-scoped artifact writer and native raster reader reached through existing authorized prep. Auth, routes, uploads, queue edges, shell commands, and network permissions are unchanged.
- Threat assumptions: the source map is an operator-configured external path, not a newly introduced arbitrary public upload/URL; run identity is established by existing orchestration; arbitrary concurrent filesystem replacement by an actor with service-account access is outside the containment guarantee.
- Valid states: no map; complete/partial/all-missing coverage with the contracted default policy; empty generic key sets; populated ordinary and MOFE preparation; mixed directory/archive roots with the directory authoritative; permitted in-run directory aliases. Archive-only roots are explicitly retired by current authority.

## Verdict

- Security gate status: **pass** for the final reviewed code and runtime evidence.
- Unresolved security code findings: High **0**, Medium **0**, Low **0**.
- Release recommendation: **ship**. Correctness findings are closed; owner QA and the broad suite pass; native identities and the full workflow are verified. Normal scoped commit/push and remote-tip checks remain the package owner's publication work.
- No risk acceptance was requested or recorded.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

The correctness artifact enumerates optional absence, empty/populated data,
coverage, legacy roots, and malformed inputs. Security recheck directly proved
that containment rejects an escaping alias while preserving a legitimate
in-run alias. No-map returns before output-path/default checks. Missing-area,
invalid-default, grid, and archive errors are authorized by the current
contract. Numerical correctness and ordinary/MOFE propagation remain the
independent correctness gate's responsibility.

### 1) Auth, Session, and Authorization

No route, JWT, CSRF, session, or authorization implementation changes were
introduced in this package. The bounded integration runner enqueues only the
explicitly authorized local `seductive-sabra` run through the existing
`run_wepp_rq` orchestrator; it does not create a public enqueue endpoint.

### 2) Secrets and Credential Handling

No new credentials, secret defaults, secret mounts, or token minting occur.
The integration runner obtains the existing Redis configuration without
printing it. Reviewed evidence contains paths and hashes, not secrets. The
final job tree contains no exception text: all 15 `exception` fields are null.
All 17 current artifact files were inspected with credential-signature checks;
no private-key, token, JWT, credential-URL, or credential-value matches appeared.

### 3) Input Validation and Output Safety

The new Rust path checks finite defaults, bands, matching dimensions,
projected/equivalent CRS, every affine coefficient, nonsingular finite
transforms, raster/mask lengths, and integral signed-32-bit keys. GDAL failures
become Python exceptions; this path introduces no unwrap/panic-based input
handling. Missing-coverage errors enumerate at most ten affected keys.
WEPPpy owns conductivity positivity and rejects unusable configured inputs
instead of silently applying a scalar. The source remains an intentionally
external trusted path. No shell interpolation, deserialization, HTML output,
or new network fetch is introduced.

### 4) File System and Run-Tree Boundaries

SEC-01 is closed. The resolved soils directory must remain within the resolved
run; staging uses a private `TemporaryDirectory` in that directory and fixed
artifact basenames. `os.replace` publishes completed files. The context manager
cleans normal failure residue. Archive-only roots fail, mixed legacy archives
remain untouched, and permitted in-run aliases work. Fresh web, rq-engine,
default-worker, and batch-worker environments imported the intended native
library as UID 1000/GID 993. The real queued workflow successfully wrote and
consumed its artifacts under existing Compose permissions and orchestration.

### 5) Queue, Worker, and Subprocess Surfaces

Production queue wiring is unchanged. Both prep callers obtain validated means
before worker submission. No additional shell/subprocess boundary is introduced.
The integration script checks local queue idleness, prevents accidental repeated
submission through its evidence marker, polls descendant job metadata, and
retains failures. These are operator assertions, not public authorization
controls. Final evidence records all 15 jobs finished, including hillslope and
watershed model execution, interchange, reports, and completion finalization.

### 6) Agentic Tooling and MCP Surfaces

The review uses the package-authorized dedicated reviewer and isolated temporary
fixtures. No tools, MCP credentials, new roles, permissions, or external
communications were introduced. The reviewer made no production-code edits,
production-host changes, or commits.

### 7) Network and External Integrations

No new outbound integration or network exposure is introduced. GDAL's existing
driver capabilities remain an inherited trust boundary for operator-selected
rasters; this review does not certify GDAL against arbitrary adversarial driver
payloads or remote virtual-filesystem paths.

### 8) CI/CD and Supply Chain

No new dependency, workflow permission, or runner scope was added. The package
requires the existing py312 release path and same-directory atomic native
library replacement, with matching wrapper, source/build hash, ABI and runtime
import-path evidence. The final manifest matches all four reviewed source,
wrapper and library file hashes. The native source hash also matches its Git
source commit. The release file is mode 0755. All four fresh runtime services
report library SHA256
`587bb3371c282296291f233d6674d4bcad65f950d966f7cd71c0162cdb279b54`;
different container IDs and new StartedAt values establish the restart.

### 9) Data Integrity, Locking, and Concurrency

The collaborator does not persist NoDb state. It holds the existing soils
maintenance lock during preparation/publication. Independent real Redis
contention raised `NODIR_LOCKED`, preserved the prior artifact bytes, and left
no staging residue. Source/grid hashes are checked before and after computation.
Map and summary replacements are individually atomic, not a two-file
transaction; the summary includes the map hash as its completion identity.
A crash between replacements must remain an error/mismatched pair rather than
successful current evidence. Failure-injection coverage and the reader hash
requirement are tracked by the correctness review. Source sidecar identity and
lock TTL expiry during exceptionally long work remain coverage limits.

### 10) Logging, Monitoring, and Incident Readiness

Logs report coverage/default counts without credentials. New validation errors
are explicit and are not swallowed. The [external baseline](baseline.md)
documents a complete run snapshot, matching prior native library/wrapper, and
scoped recovery without global Redis flushing. Full rollback was not exercised
by this reviewer. Final job/manifest inspection and credential-signature checks
passed; raw backups, transcripts, and full Compose snapshots remain outside Git.

## Validation Evidence

- Initial independent `wctl run-python -` probe, real GeoTIFFs/GDAL/native and live Redis: a temporary run's `soils` symlink to a sibling directory produced outside `kslast.tif` and `kslast_summary.json`. This confirmed SEC-01 without modifying a live project.
- Post-fix independent `wctl run-python -` probe: the same escape raised `ValueError("kslast soils directory escapes the run root")`; the outside directory stayed empty.
- Same post-fix probe: a `soils` alias to an existing directory inside the run produced mean **0.2** and the two artifacts.
- Same post-fix probe: holding the real soils maintenance lock caused prep to raise `NODIR_LOCKED`; existing artifact bytes remained equal and no staging directory survived.
- Reviewed direct-raster regression suites cover masks/nodata, invalid grids/defaults, malformed configured source, uncovered destination and archive/mixed roots. The correctness reviewer closed all three numerical/stacker/worker findings after independent revalidation; their tests are not claimed as independently rerun by the security reviewer.
- Final provenance inspection independently recalculated and matched all four source/wrapper/library hashes, checked the native source against commit `125edc1`, and verified mode 0755 for the deployed library. Four services have matching runtime native hashes, changed container IDs, and fresh StartedAt records.
- Final job-tree inspection: **15/15 finished**, all descendants represented, all exception fields null. Parent `90431b48-4138-4f28-89f6-90a5b3806f7e` was submitted after restart; completion finalizer ended at **2026-09-09 23:56:19 UTC**.
- Full-run verification records **505 hillslopes, 1259 OFEs, and 25 fresh finite interchange tables**, using unchanged `wepp_260430` and 46 simulation years. Every hillslope/OFE was compared against the independent cell oracle; this live fixture used no missing-area defaults or developed exemptions, which are covered by separate synthetic tests.
- Final secret inspection scanned **17 artifact files**, with **0 credential-signature findings**. Restart JSON fields were explicitly checked against the intended ID/image/name/state/time allowlist; no environment or command snapshots are included.
- Owner QA evidence records `wctl run-pytest tests --maxfail=1`: **8174 passed, 72 skipped**, 3110 warnings, 900.45 seconds. The security reviewer inspected the resulting disposition without rerunning the broad suite.
- `wctl doc-lint --path docs/work-packages/20260909_kslast_area_weighted/artifacts/20260909_security_review.md`: **1 file validated, 0 errors, 0 warnings**.

## Residual Risk

- Existing GDAL parsing and whole-raster memory costs remain. No public raster-upload or resource-quota boundary was added; hostile oversize rasters were not stress tested.
- Resolved-path checks are not a directory-file-descriptor sandbox against simultaneous privileged filesystem replacement. Service-account access already controls the run tree; the maintenance lock coordinates participating application writers.
- Individually atomic publication can leave a detectable map/summary mismatch after an interrupted second rename; hash verification and failed-job status are required before treating outputs as current.
- Secret signatures are a scoped inspection aid, not proof that every possible credential encoding was detected. Raw operational logs remain outside the publication set.

## Sign-off

- Security reviewer: independent `security_review` agent, 2026-09-09; **pass**, SEC-01 closed and final evidence accepted after correctness and owner QA review.
- Package owner: root Codex recorded the separate owner QA disposition in `validation.md`; final Git publication and package closeout remain with the owner.
