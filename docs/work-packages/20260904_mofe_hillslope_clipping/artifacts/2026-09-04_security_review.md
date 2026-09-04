# Security Review - Multiple-OFE Hillslope Clipping

## Metadata

- **Package**: `docs/work-packages/20260904_mofe_hillslope_clipping/`
- **Reviewer**: `/root/checkpoint_security_review`
- **Date**: 2026-09-04
- **Scope reviewed**: canonical run-input resolution, transformed slope-file
  publication, RQ worker failure, and Forest deployment.
- **Commit/branch context**: checkpoint draft from `6aae4616c` on `master`.

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: authorized run input selection does not change, but the
  multiple-OFE path changes from canonical directory copy to content
  transformation and publication inside the run tree.
- **Threat model assumptions**: source paths and translated IDs remain trusted
  application-generated state under the existing symlink policy; run
  authorization is unchanged; malformed contents can reach workers through
  existing run inputs. This package does not claim to harden that existing
  trusted boundary against a hostile filesystem actor.
- **Valid states controls must preserve**: directory-backed,
  disabled clipping, valid positive enabled clipping, and
  supported single-OFE files from the contract-decision state matrix.

## Findings

| ID | Severity | Disposition | Status |
| --- | --- | --- | --- |
| SEC-01 | High | Replace impossible archive-materialized success with directory-backed success and archive-only/mixed rejection. | Resolved |
| SEC-02 | High | Require complete parse, same-directory temp write, `os.replace`, cleanup, prior-output preservation, and hardlink de-aliasing tests. | Resolved |
| SEC-03 | Medium | Narrow threat model to unchanged trusted generated IDs/source symlink policy; do not claim new hostile-filesystem containment. | Resolved |
| SEC-04 | Medium | Add a configured-value accessor for WEPP prep/UI and retain effective-property suppression for every other consumer. | Resolved |
| SEC-05 | Medium | Require direct RQ aggregate/child/downstream failure evidence. | Resolved |
| SEC-06 | Medium | Require zero started jobs before bounded recreation and worker registration afterward. | Resolved |
| SEC-07 | Medium | Use canonical `wctl rq-info --detail` spelling and record the exact drain/registration evidence. | Resolved |

## Required Surface Evidence

- Direct unmocked valid directory-backed source transformation.
- Direct unmocked archive-only and mixed-root rejection.
- Malformed and invalid-limit sources cannot partially replace the destination.
- Injected temp-write and replace failures preserve a prior destination and
  clean temporary files.
- Replacing a hardlinked destination de-aliases it without mutating the source.
- Source/destination selection stays on the existing trusted generated-state
  path; no new user-controlled identifier or symlink policy is introduced.
- Queue topology, auth, secrets, subprocess composition, and external network
  behavior remain unchanged.
- Direct RQ evidence proves prep failure terminates the aggregate as failed,
  exposes the child exception, and blocks hillslope/downstream execution.
- Forest recreation is limited to `weppcloud`, `rq-engine`, `rq-worker`, and
  `rq-worker-batch`, happens only after started jobs drain, and is followed by
  worker registration checks; forest1 and production are untouched.

## Verdict

- **Gate status**: pass for pre-implementation checkpoint; implementation and
  Forest evidence remain gated
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: implement within the accepted boundary; hold
  deployment until the required evidence is complete and independently reviewed

## Residual Risk

The unchanged trusted generated-ID and source-symlink boundary remains a
residual assumption owned by existing run-input governance. This package adds
no user-controlled path component. Re-review is required after implementation.

## Sign-off

- **Security reviewer**: `/root/checkpoint_security_review`, 2026-09-04
- **Package owner**: Codex, 2026-09-04
