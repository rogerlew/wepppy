# Security Review — CBEXEC-01

## Findings

All four implementation findings are resolved. The dedicated security and artifact-observability gates pass for the bounded Forest scope. Broad regression completion remains a separate package gate.

| ID | Severity | Surface and consequence | Evidence and required correction | Status |
| --- | --- | --- | --- | --- |
| CBEXEC-SEC-01 | Medium | The second upload-policy guard rejected omitted/unchanged saved executables without the new declarations, breaking supported legacy submissions and preparation. | `single_input_policy.require_wepp_input_policy` now requires certification for explicit changes while retaining feature exclusions. `test_saved_legacy_upload_choice_survives_actual_parser` exercises real parser, locks, NoDb persistence and detached reload; unsupported changes leave saved bytes unchanged. | Resolved |
| CBEXEC-SEC-02 | Medium | Matching flags and per-file hashes could admit a watershed/hillslope pair from different releases or source commits. | `read_binary_capabilities` now binds resolved names, roles, release tag and source repository/branch/commit. Direct reviewer-created temporary files reproduced acceptance before the fix and explicit rejection after the fix; actual installed 260803/261010 pairs remain eligible. Parameterized copied/mixed sidecar tests cover the correction. | Resolved |
| CBEXEC-SEC-03 | Medium | Unconditional graph resolution rejected explicit schema-v1 projects; coarse legacy geometry also needed protection when expanding binary choices. | `capability_authority` returns its documented legacy result for v1; the shared policy validates coarse backend/representation axes and rejects TOPAZ/MOFE. `test_explicit_v1_saved_config_persists_new_binary` reloads an actual v1 config and persists 261010 without changing config/manifest bytes. | Resolved |
| CBEXEC-SEC-04 | Medium | The shared runner hash cache could accept stale metadata after an executable changed in place with identical size and restored mtime. | The implementation agent reproduced the defect; `_collect_binary_identity` now includes `st_ctime_ns` in its cache key. Reviewer independently confirmed a valid temporary pair passes and the same-size/restored-mtime mutation rejects stale SHA. Final runner receipt: 59 passed. | Resolved |

No risk acceptance was requested or used to close findings.

## Metadata

- **Package:** `docs/work-packages/20261012_wepp_executable_capabilities/`.
- **Reviewer:** independent `final_security_evidence`, dedicated security reviewer.
- **Date:** 2026-10-12 local date; evidence inspected 2026-10-13 UTC.
- **Scope:** installed-ID and paired-sidecar helpers; project policy; Builder graph/registry/resolver/controller; parser/RQ admission and schema; run-page rendering; native generator refresh; retained Forest evidence.
- **Context:** accepted checkpoint `b4c950ced266765bb75f5f058bbdda8b6055278b`; implementation `3c114719b565ce4ee153c5b06d7690d11129ff6d`. [Source identity](security-source-identity.json) binds all 22 changed runtime files; each independently matches the candidate commit and working tree. Native default-branch commit: `917265bb5de62d1e20f2f5aada434a622f916398`.
- **Related correctness/QA review:** [implementation review](2026-10-12_implementation_correctness_review.md), approved for feature correctness and observability with broad regression completion pending. See also [validation summary](validation.md).
- Review changed only security artifacts. No runtime, accounts, permissions, native binaries or project data were changed by this reviewer; isolated temporary files were used for the sidecar rejection check.

## Security Triage Decision

- **Impact:** high; dedicated review required because an externally submitted choice determines a native executable.
- **Trust assumptions:** installed binaries and release sidecars remain operator-owned deployment files; callers cannot upload sidecars or supply an executable path. Existing run authorization, session/JWT/CSRF and NoDb ownership boundaries remain authoritative. Hashes bind bytes to declarations; they are not publisher signatures.
- **Preserved valid states:** missing optional sidecars/flags, false capabilities, matching positive declarations, old graphs, explicit v1 configs, omitted/unchanged saved legacy values and zero available MOFE tuples. Malformed declarations, mixed identities, unsupported changed IDs and hostile paths are rejected.
- Uploaded-input flexibility is the recorded scope assumption; its separate certified flag does not relax native formats, OFE limits, buffers or excluded features.

## Verdict

- **Gate status:** pass for dedicated security and artifact observability within the bounded Forest scope.
- **Unresolved findings:** High 0; Medium 0; Low 0.
- **Release recommendation:** ship with conditions: retain and assess the required broad Python result before package closeout. Security corrections, correctness/QA feature approval and the bounded Forest persistence/native hillslope/browser/archive chain are validated; no additional security correction is requested.
- This assessment does not approve production deployment, full-watershed execution or general numerical stability. Runtime changes after the reviewed candidate require re-review.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

The linked correctness matrix covers valid absence, populated and legacy states. Actual-file sidecar tests and actual parser/persistence tests protect the changed boundaries. Zero MOFE support retains ordinary creation; invalid TOPAZ/MOFE tuples remain rejected. Current legacy values are displayed separately from eligible choice enums. Security review does not replace correctness/UX approval.

### 1) Auth, Session, and Authorization

No auth, token issuance, role or CSRF implementation changes. Existing run access checks precede RQ payload application; run-page authorization precedes context construction. Browser evidence uses the ordinary authenticated session path. This is preservation by source inspection, not a new comprehensive authorization penetration test.

### 2) Secrets and Credential Handling

No new secret dependency or credential publication. The smoke test reads the existing ignored dev-agent secret file and retained receipts omit credentials. No saved browser authentication state is required by these receipts.

### 3) Input Validation and Output Safety

Explicit governed changes must be exact installed-provider IDs before path resolution or NoDb mutation. Strict booleans, paired declarations, role/name/source identity and actual hashes gate capability admission. Parser tests reject path-like IDs, unknown IDs, scalar blank and unsupported releases without changing saved bytes. The real browser submits `/tmp/not-a-release` and receives `400 unsupported_capability`; reload retains 261010. Templates retain ordinary escaped rendering.

### 4) File System and Run-Tree Boundaries

No new user-supplied path, upload transport, download route, archive exclusion or output directory. Prepared inputs and outputs retain `wepp/runs` and `wepp/output`. The disposable run's files were independently read back; its output is owned by UID/GID 1000:993 with mode 0644. Production identity parity and deployment remain separate gates.

### 5) Queue, Worker, and Subprocess Surfaces

No queue wiring or subprocess syntax changed. Admission occurs before enqueue. The retained bounded default-worker job calls the real hillslope runner with the reloaded selection; its trace binds `wepp_261010_hill` to the expected SHA-256. This does not demonstrate the full watershed orchestration path. A new RQ graph check is not required for unchanged queue wiring.

### 6) Agentic Tooling and MCP Surfaces

No product tooling permission or MCP changes. The native work occurs on the operator-authorized existing default-branch worktree, preserving unrelated main-checkout edits. No production operation is included.

### 7) Network and External Integrations

No new destination, remote dependency, fetch or proxy surface. Installed-file discovery remains local. Schema freshness binds current compatible role bytes and declarations without treating stored creation-time identity as a release allowlist.

### 8) CI/CD and Supply Chain

The native refresh compares immutable identity before editing capability fields, including source repository. The reviewer independently compared all four remints with checkpoint metadata: only the two capability declarations changed; all original build, source, validation and PASS fields remain equal. Native and vendored sidecars are byte-identical; executable hashes match in both repositories. No binary rebuild, third-party dependency or CI permission change occurred.

### 9) Data Integrity, Locking, and Concurrency

Existing locks and detached reload remain in use. Real old-project and v1 tests show 261010 can be saved while config and manifest bytes remain unchanged. Invalid-ID tests check saved NoDb bytes, not only exceptions. Sidecars are read afresh; direct metadata-change and registry-revision tests cover freshness. There is no new cross-file transaction or claim that independent deployment replacement is atomic.

### 10) Logging, Monitoring, and Incident Readiness

Failures are explicit; no new broad catch or silent numerical fallback was introduced. Existing runner identity traces provide executable path/hash/status. Paired policy/sidecar rollback is documented in the active plan. Changing releases still requires regenerating matching hillslope and watershed/PASS artifacts.

## Validation Evidence

- [Browser receipt](browser-validation.json): real Builder 261010 MOFE creation, upload-capability validation, live options/schema/full geometry tuples, hostile API rejection and reload. The upload checkbox was validated and then cleared before creation; this is not a browser upload-project execution claim.
- [Selected execution](selected-execution-validation.json): real grouped-payload persistence 260803 to 261010, unchanged config/manifest, two-OFE preparation and fresh native output on the default RQ worker. Reviewer independently matched all four retained config/input/output hashes and checked output text for nonfinite markers.
- [Authenticated artifact readback](browser-artifact-readback.json): normal prepared-soil and output downloads return 200 and matching SHA-256; runner-identity download succeeds. The cache-key correction followed the native/browser receipts and has separate direct file-boundary and runner regression evidence; executable bytes are unchanged.
- [Canonical archive/restore](archive-restore-validation.json): authenticated archive and restore jobs preserve selected 261010 and matching downloaded config/input/output bytes. Reviewer independently verified the ZIP hash and byte equality of 11 archived/restored members, including original sources, `wepp.nodb`, prepared inputs and runner stderr.
- [Native input matrix](native-input-validation.json): 30 cases across two releases, five admitted soil formats and 1/2/32 OFEs, with original hashes, semantic prepared-soil assertions and real native output checks. The retained script defines the bounded fixture coverage.
- [Remint receipt](sidecar-remint.json): independently checked against both repositories and original metadata.
- Independent correctness rerun: 30 policy/sidecar tests passed. Final targeted receipt `/tmp/cbexec-final-targeted.log`: 209 passed, including actual explicit-v1 persistence and metadata-only registry freshness. The earlier `/tmp/cbexec-api3.log` had 344 passes and one freshness-fixture failure; the later targeted run closes that failure and is not misreported as an earlier full pass.
- Native final generator: 9 passed. Final runner regression `/tmp/cbexec-runner-final.log`: 59 passed. Final policy/schema receipt `/tmp/cbexec-final-policy-schema.log`: 149 passed. Full Jest: 972 passed across 118 suites; focused Builder DOM tests: 23 passed. Stubtest and stub completeness passed. Broad-exception changed-file gate passed.
- Repository npm lint retains the unchanged `climate.test.js:300` conditional-expect failure; it is not a passing gate. Full Python remains in progress, with no completion claim here.

## Residual Risk

Capability declarations establish supported interfaces, not scientific stability. Existing ordinary non-flattened selection behavior is intentionally retained. A later deployment may alter installed availability; malformed packaging must fail visibly. No residual medium/high finding is accepted. Production rollout needs its own authorization and applicable runtime evidence.

## Sign-off

- **Security reviewer:** `final_security_evidence`; dedicated security/observability approval for WEPPpy `3c114719b` and native `917265bb5`, 2026-10-13 UTC. Unresolved high/medium/low findings: 0/0/0.
- **Package owner:** root orchestrator; requested this bounded disposition and retains responsibility for the outstanding broad-validation result before package closeout. No risk acceptance substitutes for that gate.

## Artifact Observability Gate

Comparable module: existing WEPP preparation/execution. Inventory: original soil/management inputs, `config.cfg`, `config-manifest.json`, `wepp.nodb`, prepared `wepp/runs` files, runner diagnostics and `wepp/output` results. Sidecars are deployment provenance in the native and WEPPpy repositories; no new hidden per-project store is introduced.

Actual writer/readback, source preservation, normal authenticated artifact downloads and canonical archive/restore parity are retained. Independent ZIP/restored-file comparison covers `config.cfg`, `config-manifest.json`, `wepp.nodb`, original management/soil/slope, prepared soil/management/run, loss output and runner stderr. All 11 members are present and byte-identical; the archive SHA matches its downloaded receipt. The [artifact observability standard](../../../standards/artifact-observability-standard.md) gate passes for this inventory; no exception is used.
