# Security Review - AgFields Routing Scheme Suite

> This gate is intentionally open. No implementation may close the package until
> a reviewer updates the evidence and resolves every medium/high finding.

## Metadata

- **Package**:
  `docs/work-packages/20260714_ag_fields_routing_scheme_suite/`
- **Reviewer**: TBD before implementation closeout
- **Date**: 2026-07-14 (scaffold); implementation review pending
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
| THR-01 | High | File clear | Caller-controlled scheme text escapes the watershed root or selects legacy/protected files | Closed enum-to-slug mapping, resolved-path containment, symlink rejection, cross-scheme deletion tests | Open |
| THR-02 | High | RQ/NoDb | Concurrent scheme jobs or clear actions corrupt state or publish the wrong result | Single-flight admission, scheme-scoped terminal state, atomic publish, lock/concurrency tests | Open |
| THR-03 | High | Subprocess | Scheme/resource values reach shell command composition | Structured argv only, allowlisted binaries/resources, explicit failure propagation | Open |
| THR-04 | Medium | Authorization | New Run All or clear-all behavior bypasses existing run access or enqueue scope | Preserve JWT scopes/run ownership and add route tests for each mutation | Open |
| THR-05 | Medium | Availability | Run All starts three memory-heavy watershed jobs concurrently | Dependency-chain serialization, queue observability, measured peak-memory evidence | Open |
| THR-06 | Medium | Integrity | Failed/retried jobs overwrite a prior completed scheme or misreport partial results | Attempt staging, atomic terminal manifest, source signatures, independent job ids/status | Open |
| THR-07 | Medium | Output exposure | Browse/result links can be influenced to reveal sibling or unrelated run files | Server-provided fixed relative paths and route-level run authorization | Open |
| THR-08 | Medium | Input integrity | Duplicate classifier logic changes hybrid branch assignment silently | Invoke/version the canonical Peridot implementation and persist resource hashes | Open |
| THR-09 | High | Native input integrity | Invalid/non-finite management data or silent coercion reaches WEPP and creates crashes or scientifically ambiguous results | Canonical row/value/unit validation, explicit failure, corpus provenance, no undocumented clamp/fallback | Open |
| THR-10 | Medium | Supply chain | A binary built from the detached dirty forest baseline is misattributed or mismatched with watershed/PASS artifacts | Initial status/hashes, isolated build, explicit dirty-base disposition, matching release family, source/binary SHA-256 | Open |

These are design threats, not dispositioned implementation findings. The Findings
section is populated from actual code and validation evidence.

## Findings

No implementation has been reviewed yet. Findings are recorded here with evidence
as milestones land.

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| _Pending_ | - | - | Implementation review has not started | Package scaffold only | Review every changed attack surface before closeout | Open |

Risk acceptance authority: `Accepted-risk` requires a security reviewer
recommendation plus explicit package-owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `fail` (implementation and evidence are pending)
- **Unresolved findings**:
  - High: not yet assessed
  - Medium: not yet assessed
  - Low: not yet assessed
- **Release recommendation**: hold until implementation review passes

## Surface Checks

### 1. Auth, Session, and Authorization

- [ ] Run and clear routes preserve JWT scopes and run access checks.
- [ ] `all` grants no capability beyond invoking the three individually authorized
  scheme operations.
- [ ] Browser mutation paths preserve the canonical CSRF/service-token boundary.
- [ ] Unauthorized, wrong-run, and missing-scope tests cover run, clear-one, and
  clear-all requests.
- [ ] Errors do not disclose absolute run paths, tokens, or internal auth details.

### 2. Secrets and Credential Handling

- [ ] No new secrets, plaintext credentials, query-string tokens, or logged bearer
  values are introduced.
- [ ] Existing rq-engine secret-file and JWT contracts remain unchanged.
- [ ] Native binary provenance does not embed sensitive environment values.

### 3. Input Validation and Output Safety

- [ ] Scheme values are exact closed enums; slugs, separators, arrays, mixed case,
  and unknown values fail with canonical 400 errors.
- [ ] `max_workers` retains finite positive range validation.
- [ ] Peridot resource paths are server-derived from the authorized run, not
  supplied by the browser.
- [ ] Management-corpus source/output paths are server-derived fixed run resources
  in production; the diagnostic CLI validates explicit paths and does not execute
  shell-composed arguments.
- [ ] Invalid source values fail with bounded provenance and are not silently
  clamped or emitted as raw database records in browser-visible errors.
- [ ] Manifest/error values are escaped before browser rendering.
- [ ] Validation failures are explicit and never trigger a fallback scheme.

### 4. File System and Run-Tree Boundaries

- [ ] Writes remain under fixed current scheme roots.
- [ ] Resolved path and symlink checks cover scheme roots and all parents used by
  clear/publish operations.
- [ ] Clear one/all tests prove baseline, independent AgFields, sibling scheme, and
  legacy Concept 2 trees cannot be removed.
- [ ] Temporary/staging roots are bounded and cleanup/retry behavior is explicit.
- [ ] Browse paths cannot escape the authorized run or expose another scheme by
  caller-controlled text.

### 5. Queue, Worker, and Subprocess Surfaces

- [ ] Enqueue sites and Run All dependency edges are intentional and present in
  the RQ dependency catalog/graph.
- [ ] `allow_failure=True` permits later comparison jobs without masking the
  earlier job's failed terminal state.
- [ ] Active/deferred/started jobs prevent conflicting AgFields input mutation and
  unsafe clear operations.
- [ ] Native and WEPP subprocesses use structured argv with fixed binaries and
  bounded worker/resource controls.
- [ ] Job failure, cancel, retry, missing-job, and partial Run All cases preserve
  the canonical response/error contracts.
- [ ] `wctl check-rq-graph` passes after queue wiring changes.

### 6. Agentic Tooling and MCP Surfaces

- [ ] No agentic or MCP execution surface is added by this package.
- [ ] Generated evaluation artifacts do not publish or copy data outside the
  authorized project without an explicit operator action.

### 7. Network and External Integrations

- [ ] No new outbound network call or external dependency is introduced.
- [ ] Existing internal rq-engine exposure is not widened.
- [ ] High-cost Run All requests retain single-flight/rate controls adequate for
  the existing authenticated audience.

### 8. CI/CD and Supply Chain

- [ ] Peridot/wepppyo3/forest changes use owned repositories and existing
  dependencies; any new dependency passes the repository evaluation standard
  first.
- [ ] Refreshed native binaries record source commit, dirty-base disposition,
  compiler/build flags, release family, and SHA-256.
- [ ] Hillslope PASS generation and watershed execution use matching binary
  families; no stale or mixed release is published.
- [ ] Build/test logs do not expose secrets.

### 9. Data Integrity, Locking, and Concurrency

- [ ] NoDb updates use the canonical lock/dump contract and do not hold locks over
  long WEPP/native execution.
- [ ] Each scheme has independent atomic status, source signature, summary, and
  error state.
- [ ] Concurrent submission and clear races have focused regression coverage.
- [ ] Partial failure leaves previous completed artifacts and sibling states
  diagnosable and trustworthy.
- [ ] Historical singular state hydration is additive and cannot claim current
  artifacts that do not exist.

### 10. Logging, Monitoring, and Incident Readiness

- [ ] Logs/status messages include run id, scheme, job id, phase, and stable reason
  code without absolute paths or secrets.
- [ ] Run All exposes job ordering and partial terminal results.
- [ ] No broad handler silently swallows implementation errors.
- [ ] Rollback can disable/remove the new UI selection while retaining completed
  artifacts and the legacy Concept 2 path.
- [ ] Peak memory, elapsed time, and disk usage are recorded on generated
  acceptance.

## Validation Evidence

- Automated checks pending:
  - `wctl run-pytest` focused AgFields/route/RQ suites
  - `wctl check-rq-graph`
  - `wctl run-npm lint` and `wctl run-npm test`
  - Peridot and wepppyo3 Rust tests
  - forest smoke, hillslope watchlist, pytest, ablation policy, watershed replay,
    ELF interpreter, and binary provenance gates
  - `wctl doc-lint` for changed docs
  - changed-file broad-exception and stub gates
- Manual checks pending:
  - Authenticated one-scheme and Run All execution
  - Cross-scheme/legacy protected-tree inventory
  - Clear-one/clear-all path containment
  - Partial Run All failure/retry
  - Dev-project memory and output evidence

## Residual Risk

- **Accepted residual risks**: None. Acceptance has not been requested.
- **Follow-up packages/issues**: Recorded only after implementation review.

## Sign-off

- **Security reviewer**: Pending
- **Package owner**: Pending
