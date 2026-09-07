# Security Review - Batch Climate and RAP NoDb Contention

**Disposition**: Pass; no unresolved high or medium findings.
**Independent reviewer**: `/root/security` (read-only); final re-review on 2026-09-07.
**Attack surface**: worker-owned run filesystem, NoDb locks, staged publication.
**Deployment acceptance**: excluded by operator, unmeasured.

| Finding | Severity | Resolution |
| --- | --- | --- |
| SEC-01: old publisher rollback overwrote newer output, or rolled back a committed controller | High | Check lock and artifact identity; compare exact intended NoDb payload; retain both generations when commit is unknown. |
| SEC-02: staging bypassed unmanaged Climate symlink containment | High | Restore router unlink behavior and reject unmanaged targets in direct builders; preserve managed projections. |
| SEC-03: post-replace stat failure lost publication tracking | Medium | Capture staged file identity before rename; journal without a fallible canonical stat. |

The reviewer inspected tests for token handoff, competing precommit rewrite,
postcommit version error, managed/unmanaged paths, unknown outcome retention,
and postrename stat behavior. Independent temporary-file probes confirmed the
corrected publication and unknown-outcome recovery behavior. The primary agent
ran the focused suites; their final counts are recorded in validation evidence.

No auth, secrets, subprocess arguments, queue wiring, or network-permission
widening was found. Valid absent/empty/populated/legacy states remain explicit.
Cooperative locks and multi-file crash interruption remain limitations.
No live workload or deployment operation was performed for this review.


## Metadata and triage

Package: `20260906_batch_climate_rap_contention`; base revision
`aafeecc8c3bc3ba9dbf16fec66891770742b35f4`; scope: the three new
publication/collector modules, Climate facade/router integration, and RAP_TS.
Impact is `high`; a dedicated review is required. Threat assumptions are
cooperating controller writers and worker-owned run directories. Tests and
valid-state evidence are linked in the correctness and validation artifacts.

## By-surface checks

| Surface | Disposition |
| --- | --- |
| Valid-state noninterference | Empty/populated/legacy RAP and managed Climate projection paths remain supported; malformed inputs fail explicitly. |
| Auth/session/authorization/CSRF | No entrypoint or permission changes. |
| Secrets/credentials | No new secrets, mounts, credential dependencies, or secret logging. |
| Input/output safety | Explicit snapshots; six-band allowlist; malformed years/data reject before publication. |
| Filesystem/run-tree containment | Real replacement, symlink, ownership, and rollback tests; recovery copies intentionally retained on interrupted cleanup. |
| Queue/workers/subprocesses | Existing backend calls and RQ semantics preserved; no enqueue/dependency changes, so graph regeneration is not applicable. |
| Agentic tooling/MCP | Only authorized repository/test/review work; no live replay or external publication. |
| Network/integrations | No new outbound endpoint or retry policy. |
| CI/CD/supply chain | No workflow, image, dependency, or deployment changes. |
| Data integrity/concurrency | Fresh hydration, explicit results, strict stale check, known/unknown commit handling, token takeover regression. |
| Logging/incident readiness | Year/band/progress/retry identity preserved; failures propagate and recovery locations are logged. |

## Validation and sign-off

See [validation](2026-09-07_validation.md): full suite 7535 passed, 63 skipped;
stub, exception, Vulture, and documentation gates pass. This is a source/code
gate pass, not deployment acceptance. Security reviewer `/root/security`
signed off on 2026-09-07; primary agent `/root` recorded the disposition.
No finding required risk acceptance. Known crash-interruption and deployment
evidence limits remain as documented, not waived findings.
