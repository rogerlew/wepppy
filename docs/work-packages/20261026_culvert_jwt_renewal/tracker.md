# Culvert JWT renewal tracker

## Status

Active 2026-10-26 UTC. Starting implementation revision: `e5e59e83256a19ba5fc9b5f5c8401f3848e11e73`.

## Progress

- [x] Inspect live identities, mounts, issuance and user systemd availability.
- [x] Scaffold package and draft canonical contract.
- [ ] Independent contract reviews and ancestor checkpoint.
- [ ] Implement operator scripts, units, client helper and tests.
- [ ] Review implementation, deploy bounded files and validate via systemd.
- [ ] Document evidence, monitoring, recovery and closeout.

## Decisions

2026-10-26 UTC: operator explicitly requested scaffold and execution with systemd and live JWT update validation. Preserve existing subject/audience/group/scope. Use existing lingering user systemd on wepp1; no privilege escalation. Deployment is authorized for this bounded workflow.

## Evidence

`wepp1`: `loginctl show-user roger` gives `Linger=yes`, user systemd running. `wepp2`: Culvert worker uid 0; instance mount maps `/workdir/culvert_app_instance_dir` to `/app/instance`. Signing secrets stay on issuer. Independent review pending.
