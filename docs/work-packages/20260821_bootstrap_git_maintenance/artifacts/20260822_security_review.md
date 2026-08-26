# Security Review – Bootstrap Git Maintenance

## Metadata

- **Package**: `docs/work-packages/20260821_bootstrap_git_maintenance/`
- **Reviewer**: Codex
- **Date**: 2026-08-22
- **Scope reviewed**: Bootstrap enable lock, Git subprocess arguments, run-tree
  boundary, CPU configuration, and failure behavior
- **Commit/branch context**: WEPPpy merge `e94ead9d`; openWEPP deployment PR 128

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: an RQ worker performs an object-store rewrite on NFS.
- **Threat model assumptions**: the run working directory is already resolved
  by `get_wd`; the enable job owns the existing run-scoped Git lock; Git and the
  repository are trusted runtime inputs, while user-controlled shell text is not.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Object pruning | Immediate pruning can race readers or recently created objects. | Use normal `git gc`; prohibit `--prune=now`. | Resolved in design |
| SEC-02 | High | Subprocess | Shell interpolation could turn configuration into command execution. | Fixed argv list, integer CPU value, `shell=False`. | Resolved in design |
| SEC-03 | Medium | Concurrency | Object maintenance must not race Bootstrap mutations. | Run before releasing the existing enable lock; verify call ordering. | Resolved: maintenance is inside `init_bootstrap`, before `bootstrap_enabled=True`, while `bootstrap_enable_rq` retains the enable lock until `finally` |
| SEC-04 | Medium | Resource exhaustion | Unbounded packing can monopolize a worker. | Cap threads with existing `WEPPPY_NCPU`; retain RQ/container limits. | Resolved: fixed integer `pack.threads=NCPU`; Kubernetes/Compose CPU limits remain authoritative |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: shipped and validated; close package
