# Culvert JWT renewal tracker

## Status

Closed 2026-10-26 UTC; deployed and validated. Starting implementation revision: `e5e59e83256a19ba5fc9b5f5c8401f3848e11e73`.

## Progress

- [x] Inspect live identities, mounts, issuance and user systemd availability.
- [x] Scaffold package and draft canonical contract.
- [x] Independent contract reviews and ancestor checkpoint `4cd8e9cb1`.
- [x] Implement operator scripts, units, client helper and tests (`2b334ded7`; companion `a2bd7bf62`).
- [x] Independent reviews PASS; bounded deployment and service/timer validation complete.
- [x] Document evidence, monitoring, recovery and closeout.

## Decisions

2026-10-26 UTC: operator explicitly requested scaffold and execution with systemd and live JWT update validation. Preserve existing subject/audience/group/scope. Use existing lingering user systemd on wepp1; no privilege escalation. Deployment is authorized for this bounded workflow.

## Evidence

`wepp1`: `loginctl show-user roger` gives `Linger=yes`, user systemd running. `wepp2`: Culvert worker uid 0; instance mount maps `/workdir/culvert_app_instance_dir` to `/app/instance`. Signing secrets stay on issuer. Independent review pending.

Contract ancestor: `4cd8e9cb1` (two independent reviews PASS before implementation).

## Live progress — 2026-10-26 16:46 UTC

20 focused tests pass. Installed on both hosts. First systemd attempt exposed short-hostname LAN resolution; changed to explicit Tailscale FQDN without relaxing key restriction. Service-triggered and timer-triggered rotations both changed JWT read by the same live worker process; fresh token authenticated. Negative forced-key commands and malformed installation preserved token. Timer enabled, runtime force/test overrides removed. Full-suite run remains active; first run was invalidated by editing a collected test fixture while running, rerun uses final fixture. See artifacts/20261026_live_validation.md.

## Closeout — 2026-10-26 17:41 UTC

Source checkpoint `4cd8e9cb1`, implementation `2b334ded7`, companion `a2bd7bf62`. Focused 20 pass; full gate reached 11,610 pass/155 skip before existing Playwright path failure; corrected-path tail 183 pass, seven repeated cases, giving 11,786 unique passing cases. No implementation regression remains observed. Correctness/security PASS; all findings closed. Live service and timer changed the mounted credential and the same worker process authenticated it. Daily units restored/enabled; no test force remains. See validation summary and live evidence.

Follow-ups: off-host alert destination, first ordinary trigger observation, separate dev Compose browser-path correction. No changes to unrelated query-catalog work in the shared checkout.
