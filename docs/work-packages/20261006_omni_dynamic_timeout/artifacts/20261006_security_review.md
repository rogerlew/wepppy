# Security Review - Omni dynamic timeout

## Metadata

- **Package**: `docs/work-packages/20261006_omni_dynamic_timeout/`
- **Reviewer**: `/root/wrt02_contract_security`, independent operations and
  security review
- **Date**: 2026-10-06
- **Scope reviewed**: Omni scenario/contrast RQ admission, resource duration,
  metadata, graph topology, and disposable Redis validation
- **Commit context**: checkpoint `3c8c9c622ce722180c837e641b6d3bfbe9d67df3`;
  implementation candidate `adff42d6d9e38f561d41cc681e89f3386ef888c0`
- **Related artifacts**: `20261006_correctness_review.md`, `live_rq.json`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: the change permits existing batch leaves to occupy a
  worker for a longer finite interval; authorization, queue, fan-out, paths,
  subprocess arguments, dependency edges, and retry behavior remain unchanged.
- **Threat-model assumptions**: existing project authorization and tracked-job
  conflicts remain authoritative; WRT-01 range validation remains the per-leaf
  bound; no new external input, secret, service, or dependency is introduced.
- **Valid states controls preserve**: absent/empty/fully skipped work, populated
  continuous work, single storms, existing queued work, and malformed required
  workload as enumerated by WRT-02 and the correctness review.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Queue/worker admission | No unresolved issue found | Admission occurs before child identity, parent metadata/save, Redis access, contrast rerun, and enqueue; malformed-workload regressions pass | None | Resolved |
| SEC-02 | Medium | Resource containment | No unresolved issue found | Finite WRT-01 alarm range and metadata are reused; fan-out, batching, dependencies, conflicts, and authorization are unchanged | None | Resolved |
| SEC-03 | Medium | Validation Redis | No unresolved issue found | UUID-scoped queue, nine disposable jobs, `finally` cleanup, and `cleanup_verified: true` in `live_rq.json` | None | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: proceed with local package closure after the
  remaining correctness and full-suite gates; deployment remains separately
  authorized.

## Surface Checks

- Existing authentication, project authorization, CSRF, path, NoDb lock,
  subprocess argument, error-contract, retry, and cancellation surfaces are
  unchanged.
- No secrets or credentials are added. Retained metadata contains only accepted
  WRT-01 workload and WEPP binary identity fields.
- Queue wiring is intentional and documented; `wctl check-rq-graph` passes and
  regenerated graph changes are source-line-only.
- Invalid required workload is rejected before executable side effects. Empty
  and fully skipped paths do not read unused workload.
- No external integration, dependency, CI/CD, MCP, or network surface changes.

## Validation Evidence

- Focused WRT/Omni regression suite: `97 passed`.
- Stub completeness and `stubtest wepppy.rq.omni_rq`: pass.
- Changed broad-exception enforcement: pass, net delta `+0`.
- Real Redis readback at candidate `adff42d6d9e38f561d41cc681e89f3386ef888c0`:
  dynamic leaf metadata/timeouts, fixed non-leaf timeouts, dependency edges,
  `job_info` visibility, and cleanup pass.
- Manual review found no widened auth, path, secret, queue, dependency, or
  concurrency surface.

## Residual Risk

- Existing Omni fan-out can occupy batch workers for longer; it remains finite,
  observable, and bounded by existing selection, batching, and WRT-01 controls.
- WRT-01 was fitted to watershed runtime, so whole-leaf Omni overhead may exceed
  the allowance. Any coefficient change needs separate evidence and approval.
- Existing subprocess cleanup behavior after an RQ timeout is not repaired.
- Deployment and production retry require queue drain, exact revision/container
  verification, rollback readiness, and post-retry queue/worker review.

## Sign-off

- **Security reviewer**: `/root/wrt02_contract_security`, 2026-10-06
- **Package owner**: Codex, 2026-10-06

## Artifact Observability Gate

The changed artifact is ephemeral RQ serialization, not a new project-run
scientific artifact. It is visible through existing `job_info`/job dashboard
authorization and retained as sanitized disposable-queue evidence in
`live_rq.json`. Archive/restore and browser scientific-output evidence are not
applicable because no run-tree input, intermediate, or output contract changes.
