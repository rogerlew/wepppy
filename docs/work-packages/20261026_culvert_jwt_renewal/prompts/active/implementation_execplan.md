# Automate Culvert JWT renewal with systemd

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture

Culvert submissions must not stop every 90 days because a human forgot credential rotation. A daily systemd timer on wepp1 checks the token installed on wepp2, renews before expiry, and records verification. The worker reads a dedicated token file for each submission without restarts.

## Progress

- [x] (2026-10-26 UTC) Inspected production and scaffolded package/contract.
- [ ] Reviewed and committed contract checkpoint.
- [ ] Implemented and tested scripts, units and client file loading.
- [ ] Independent implementation/security reviews passed.
- [ ] Deployed and exercised systemd; verified changed JWT in real worker.
- [ ] Documented operations and final evidence.

## Surprises & Discoveries

Both hosts lack general passwordless sudo; wepp1 already has lingering user systemd. Use this existing operational identity instead of adding privileges. Culvert worker runs as root and reads the existing instance mount, so a host-user-owned 0600 credential file is readable without mount or identity changes.

## Decision Log

2026-10-26 UTC, Roger/Codex: implement scheduled issuer-side rotation, daily check, 90-day lifetime and 30-day renewal window. Preserve submit-only service registration. Keep existing env-only clients working when no token file is configured; configured unreadable/empty files fail explicitly. Source and deploy changes remain bounded to this integration.

## Context and Orientation

WEPPpy owns wctl issuance and integration documentation. Live client checkout is `/workdir/Culvert_web_app` on wepp2; local companion checkout is at the same path on forest. `culvert_app/tasks/wepp_cloud_integration_task.py` currently reads WEPPCLOUD_TOKEN from environment. `scripts/culvert_token_rotation.py` will own issuer and forced-command receiver logic. Units live in `scripts/systemd/`. Client helper lives in integration dev-package scripts and is copied into client tasks with direct import.

## Plan of Work

Milestone 1: amend canonical renewal and service registration contracts, capture operator authorization, obtain two independent read-only reviews and commit a standalone checkpoint. Milestone 2: implement stdlib operator, daily user units, file-loading client helper, regression tests, and runbook. Milestone 3: obtain independent reviews, install a restricted delivery key and receiver, bootstrap file from current valid token, deploy client source/config with idle-queue verification, then run forced renewal via systemd. Milestone 4: validate normal no-op, rejection paths, timer scheduling, worker authentication and redacted receipts; finalize docs and reviews.

## Concrete Steps

From `/workdir/wepppy`, run `wctl run-pytest tests/culverts/test_token_rotation.py`, then `wctl run-pytest tests --maxfail=1`. Lint changed docs with `wctl doc-lint --path <file>`. Deploy only bounded reviewed files over SSH. On wepp1 use `systemctl --user daemon-reload`, `enable --now weppcloud-culvert-token-renew.timer`, and `start weppcloud-culvert-token-renew.service`. An operator-only temporary drop-in forces the acceptance rotation and is removed afterward. Record exact commands and hashes in artifacts.

## Validation and Acceptance

Direct filesystem tests cover absent/current/empty/malformed tokens, atomic replacement and failed verification retention. Test subprocess/SSH boundaries without secrets in errors. Live acceptance follows mint -> receiver verification -> file replacement -> actual application helper read -> HTTP 400 missing_file (authenticated request). Compare fingerprints, jti, expiry and permissions without retaining tokens. Confirm no-op and malformed candidate leave fingerprint unchanged, unauthorized forced command fails, enabled timer has next trigger, and consumers require no restart during rotation.

## Idempotence and Recovery

Default renewal skips healthy credentials with over 30 days remaining. Force is explicit for acceptance/manual repair. Receiver supports only status/install. Keep previous valid file and restore it via the same verification/install path; disable timer to halt renewal. Failures preserve installed credential and emit sanitized errors. SSH timeout or ambiguous response requires readback before another rotation.

## Artifacts and Notes

Retain redacted live evidence, independent contract reviews, correctness and security artifacts under artifacts/. No secret material belongs in work-package artifacts.

## Interfaces and Dependencies

Python stdlib, existing wctl/Docker issuer, SSH, user systemd, and HTTPS validation endpoint. No new external dependencies. Receiver fixed file `/workdir/culvert_app_instance_dir/.weppcloud-auth/token`; consumer configured path `/app/instance/.weppcloud-auth/token`. Operator scripts installed beneath existing user's `.local/libexec`; restricted key under `.config/weppcloud-culvert-renewal`.

## Outcomes & Retrospective

Pending implementation and real-systemd validation.

Initial revision: 2026-10-26 UTC; bounded execution authorized by user.
