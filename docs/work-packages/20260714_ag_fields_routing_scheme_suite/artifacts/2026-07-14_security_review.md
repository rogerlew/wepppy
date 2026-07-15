# Security Review - AgFields Routing Scheme Suite

> This gate remains open only for the active generated Run All remeasurement and
> final package-owner sign-off. The implementation review below has resolved the
> medium findings discovered during live acceptance.

## Metadata

- **Package**:
  `docs/work-packages/20260714_ag_fields_routing_scheme_suite/`
- **Reviewer**: Codex implementation security review; package-owner sign-off pending
- **Date**: 2026-07-14 scaffold; implementation review updated 2026-07-15
- **Scope reviewed**: Planned authenticated AgFields scheme-selection routes,
  NoDb state/locking, RQ orchestration, worker subprocesses, fixed scheme roots,
  clear behavior, browser artifact links, AgFields management-corpus validation,
  and forest binary build/vendoring
- **Commit/branch context**: `master`; scaffold based on `9c5b585c6`
- **Related artifacts**:
  - Compatibility plan:
    `artifacts/2026-07-14_scheme_artifact_compatibility_plan.md`
  - Management capacity/corpus plan:
    `artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md`
  - Active ExecPlan:
    `prompts/active/ag_fields_routing_scheme_suite_execplan.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The implementation changes authenticated mutation input,
  RQ job/dependency state, worker-launched native/WEPP processes, run-scoped file
  writes, selected directory deletion, and browser-visible output paths.
- **Threat model assumptions**:
  - Scheme/request values and browser payloads are untrusted even after run access
    is authorized.
  - `/wc1/runs` projects can contain historical files and unexpected symlinks;
    enum validation alone does not replace resolved-path checks.
  - RQ jobs can fail, retry, disappear, or overlap with user actions, and partial
    Run All completion must leave independently trustworthy state.
  - Peridot and WEPP are local owned binaries invoked with structured argument
    vectors; no shell interpolation is required.

## Pre-Implementation Threat Register

| ID | Severity | Surface | Threat | Required control | Status |
| --- | --- | --- | --- | --- | --- |
| THR-01 | High | File clear | Caller-controlled scheme text escapes the watershed root or selects legacy/protected files | Closed enum-to-slug mapping, resolved-path containment, symlink rejection, cross-scheme deletion tests | Mitigated |
| THR-02 | High | RQ/NoDb | Concurrent scheme jobs or clear actions corrupt state or publish the wrong result | Single-flight admission, preassigned atomic job-id state, scheme-scoped terminal state, atomic publish, lock/concurrency tests | Mitigated |
| THR-03 | High | Subprocess | Scheme/resource values reach shell command composition | Structured argv only, allowlisted binaries/resources, explicit failure propagation | Validated |
| THR-04 | Medium | Authorization | New Run All or clear-all behavior bypasses existing run access or enqueue scope | Preserve JWT scopes/run ownership and add route tests for each mutation | Validated |
| THR-05 | Medium | Availability | Run All starts three memory-heavy watershed jobs concurrently | Dependency-chain serialization, explicit 16-worker ceiling propagated to every interchange pool, queue observability, measured peak-memory evidence | Mitigated; final remeasurement active |
| THR-06 | Medium | Integrity | Failed/retried jobs overwrite a prior completed scheme or misreport partial results | Attempt staging, atomic terminal manifest, source signatures, independent job ids/status | Validated |
| THR-07 | Medium | Output exposure | Browse/result links can be influenced to reveal sibling or unrelated run files | Server-provided fixed relative paths and route-level run authorization | Validated |
| THR-08 | Medium | Input integrity | Duplicate classifier logic changes hybrid branch assignment silently | Invoke/version the canonical Peridot implementation and persist resource hashes | Validated |
| THR-09 | High | Native input integrity | Invalid/non-finite management data or silent coercion reaches WEPP and creates crashes or scientifically ambiguous results | Canonical row/value/unit validation, explicit failure, corpus provenance, no undocumented clamp/fallback | Validated by complete corpora |
| THR-10 | Medium | Supply chain | A binary built from the detached dirty forest baseline is misattributed or mismatched with watershed/PASS artifacts | Initial status/hashes, isolated build, explicit dirty-base disposition, matching release family, source/binary SHA-256 | Validated |

These are design threats, not dispositioned implementation findings. The Findings
section is populated from actual code and validation evidence.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-01 | Medium | RQ/NoDb availability | The first Run All job could start while rq-engine still persisted later scheme ids under the AgFields lock. | Authenticated job `7ece99f4-6c0e-44d9-801e-6c8b693bf0ac` failed in 0.130 seconds with `NoDbAlreadyLockedError`. | Preassign and persist the complete scheme/job mapping before the first enqueue; add an ordering regression. | Resolved |
| F-02 | Medium | Worker availability | The integrator's 16-worker bound did not reach hillslope interchange pools, allowing each pool to expand to host `NCPU`. | First full Concept 1 process reached `VmHWM=60,502,848 KiB`; call-chain audit found no converter `max_workers` argument. | Forward one validated 1-16 bound through the aggregate and all six writers; reject out-of-range API/RQ values. | Resolved; generated remeasurement active |
| F-03 | Medium | Native release integrity | An in-place shared-object refresh invalidated mapped pages in the completed direct-generation process, causing exit 139 during teardown. | The terminal manifest/NoDb state completed before the refresh; wepppyo3 provenance records the incident and exact artifact hash. | Install shared objects through a same-directory temporary file and atomic rename; restart target services. | Resolved |

Risk acceptance authority: `Accepted-risk` requires a security reviewer
recommendation plus explicit package-owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `fail` (implementation and evidence are pending)
- **Unresolved findings**:
  - High: 0
  - Medium: 0 implementation findings; final generated availability evidence pending
  - Low: 0
- **Release recommendation**: hold until authenticated Run All, protected inventory,
  and peak-memory evidence complete

## Surface Checks

### 1. Auth, Session, and Authorization

- [x] Run and clear routes preserve JWT scopes and run access checks.
- [x] `all` grants no capability beyond invoking the three individually authorized
  scheme operations.
- [ ] Browser mutation paths preserve the canonical CSRF/service-token boundary.
- [ ] Unauthorized, wrong-run, and missing-scope tests cover run, clear-one, and
  clear-all requests.
- [x] Errors redact the run root and do not disclose tokens or internal auth details.

### 2. Secrets and Credential Handling

- [ ] No new secrets, plaintext credentials, query-string tokens, or logged bearer
  values are introduced.
- [ ] Existing rq-engine secret-file and JWT contracts remain unchanged.
- [ ] Native binary provenance does not embed sensitive environment values.

### 3. Input Validation and Output Safety

- [x] Scheme values are exact closed enums; slugs, separators, arrays, mixed case,
  and unknown values fail with canonical 400 errors.
- [x] `max_workers` is an integer in the explicit 1-16 operational range.
- [x] Peridot resource paths are server-derived from the authorized run, not
  supplied by the browser.
- [x] Management-corpus source/output paths are server-derived fixed run resources
  in production; the diagnostic CLI validates explicit paths and does not execute
  shell-composed arguments.
- [ ] Invalid source values fail with bounded provenance and are not silently
  clamped or emitted as raw database records in browser-visible errors.
- [ ] Manifest/error values are escaped before browser rendering.
- [x] Validation failures are explicit and never trigger a fallback scheme.

### 4. File System and Run-Tree Boundaries

- [x] Writes remain under fixed current scheme roots.
- [x] Resolved path and symlink checks cover scheme roots and all parents used by
  clear/publish operations.
- [x] Clear one/all tests prove baseline, independent AgFields, sibling scheme, and
  legacy Concept 2 trees cannot be removed.
- [x] Temporary/staging roots are bounded and cleanup/retry behavior is explicit.
- [ ] Browse paths cannot escape the authorized run or expose another scheme by
  caller-controlled text.

### 5. Queue, Worker, and Subprocess Surfaces

- [x] Enqueue sites and Run All dependency edges are intentional and present in
  the RQ dependency catalog/graph.
- [x] `allow_failure=True` permits later comparison jobs without masking the
  earlier job's failed terminal state.
- [ ] Active/deferred/started jobs prevent conflicting AgFields input mutation and
  unsafe clear operations.
- [x] Native and WEPP subprocesses use structured argv with fixed binaries and
  bounded worker/resource controls.
- [ ] Job failure, cancel, retry, missing-job, and partial Run All cases preserve
  the canonical response/error contracts.
- [x] `wctl check-rq-graph` passes after queue wiring changes.

### 6. Agentic Tooling and MCP Surfaces

- [x] No agentic or MCP execution surface is added by this package.
- [ ] Generated evaluation artifacts do not publish or copy data outside the
  authorized project without an explicit operator action.

### 7. Network and External Integrations

- [x] No new outbound network call or external dependency is introduced.
- [x] Existing internal rq-engine exposure is not widened.
- [ ] High-cost Run All requests retain single-flight/rate controls adequate for
  the existing authenticated audience.

### 8. CI/CD and Supply Chain

- [x] Peridot/wepppyo3/forest changes use owned repositories and existing
  dependencies; any new dependency passes the repository evaluation standard
  first.
- [x] Refreshed native binaries record source commit, dirty-base disposition,
  compiler/build flags, release family, and SHA-256.
- [ ] Hillslope PASS generation and watershed execution use matching binary
  families; no stale or mixed release is published.
- [x] Committed build/test evidence does not expose secrets.

### 9. Data Integrity, Locking, and Concurrency

- [x] NoDb updates use the canonical lock/dump contract and do not hold locks over
  long WEPP/native execution.
- [x] Each scheme has independent atomic status, source signature, summary, and
  error state.
- [x] Concurrent submission and clear races have focused regression coverage.
- [x] Partial failure leaves previous completed artifacts and sibling states
  diagnosable and trustworthy.
- [x] Historical singular state hydration is additive and cannot claim current
  artifacts that do not exist.

### 10. Logging, Monitoring, and Incident Readiness

- [x] Logs/status messages include run id, scheme, job id, phase, and stable reason
  code without absolute paths or secrets.
- [x] Run All exposes job ordering and partial terminal results.
- [x] No broad handler silently swallows implementation errors.
- [ ] Rollback can disable/remove the new UI selection while retaining completed
  artifacts and the legacy Concept 2 path.
- [ ] Peak memory, elapsed time, and disk usage are recorded on generated
  acceptance.

## Validation Evidence

- Automated checks completed:
  - focused AgFields/management: 84 passed;
  - route/RQ/render: 104 passed;
  - enqueue-race focused rerun: 55 passed;
  - rq-engine OpenAPI contract: 10 passed;
  - frontend lint and all 625 Jest tests passed;
  - RQ dependency graph: 141 edges, current;
  - endpoint inventory and route checklist guards passed;
  - stub completeness and changed-file broad-exception enforcement passed;
  - Peridot and wepppyo3 Rust tests passed; and
  - forest smoke, hillslope watchlist, pytest, ablation policy, watershed replay,
    ELF interpreter, and binary provenance gates passed.
- Automated checks pending:
  - final documentation lint and broad repository pytest gate.
- Manual checks completed:
  - authenticated validation rejects `max_workers=17` with canonical 400;
  - authenticated Run All returns three independent job ids; and
  - the corrected retry entered native parent execution with downstream jobs deferred.
- Manual checks pending:
  - terminal authenticated Run All execution;
  - Cross-scheme/legacy protected-tree inventory
  - Clear-one/clear-all path containment
  - Partial Run All failure/retry
  - Dev-project memory and output evidence

## Residual Risk

- **Accepted residual risks**: None. Acceptance has not been requested.
- **Follow-up packages/issues**: Recorded only after implementation review.

## Sign-off

- **Security reviewer**: Codex implementation review complete; generated evidence pending
- **Package owner**: Pending
