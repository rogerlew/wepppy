# Live systemd and consumer validation

Environment: forest orchestrator; production wepp1 issuer and wepp2 Culvert app. All timestamps below UTC on 2026-10-26. Operator authorized installation and live execution. No model batch submitted.

## Preconditions and deployment

- wepp1 hostname/pwd verified; `loginctl show-user roger` returned Linger=yes; user systemd running. Existing operator Docker authority reused; no sudo grants added.
- wepp2 hostname/pwd verified; worker uid 0 and existing `/workdir/culvert_app_instance_dir:/app/instance` bind mount confirmed. Queue and StartedJobRegistry both zero before client deployment.
- Contract ancestor `4cd8e9cb1`; two independent contract reviews passed. Implementation correctness COR-01 fixed and focused tests passed before deployment. Security review had no medium/high findings; low raw-size check fixed.
- Dedicated Ed25519 public-key fingerprint: `SHA256:DqHXOxnS4vyGbU103D9q3ZnvFEqxdU7ipJhr/LCjIWE`. Key exists only on wepp1 under 0700 config directory; private key/known_hosts mode 0600.
- Receiver authorized_keys entry uses `restrict`, source `100.127.248.45`, and exact forced command `/usr/bin/python3 /home/roger/.local/libexec/weppcloud-culvert-token-rotation.py receive`. No general SSH command/forwarding granted.
- Pinned host key obtained through existing authenticated operator SSH to wepp2; fingerprint `SHA256:v8nSrXK1m3HFWb2HDsnU2/J2LqJgFT1eru9GYHG4lgM`.
- Installed script SHA256 on both hosts: `66ab5675572448c6cd7c69f8193fa70bb9463b6ffcc5c04936f86e6d36c99a53`.
- Client source/env rollback snapshot on wepp2: `/home/roger/.local/state/culvert-jwt-client-backup/20261026T164324Z`. Secret snapshot files mode 0600. Helper/source were surgically installed; README appended. One initial idle Compose restart loaded WEPPCLOUD_TOKEN_FILE.

## Failure evidence and repair

16:42:06: initial real systemd run failed with sanitized subprocess exit 255 and durable `status=failed`. SSH server log identified bare `wepp2` resolving on wepp1 to `192.168.100.217`; source was `192.168.100.237`, correctly rejected by Tailscale-only key restriction. Fixed transport to `HostName=wepp2.tail305ec9.ts.net` with `HostKeyAlias=wepp2`, preserving pinned key/source restriction. No authorization relaxation.

16:42:49: real service provisioning succeeded, Result=success, ExecMainStatus=0. Initial installed fingerprint `ecb851c435a3a88e71efa32f8af3f0b7e74e29a0b12b0a3f2e814f4fd15d21a4`, jti `57c2073977c54dfd97813f8e50db4b10`.

## Service-triggered rotation and same-process read

A temporary runtime service drop-in supplied `renew --force`; `systemctl --user start weppcloud-culvert-token-renew.service` exercised issuance, SSH delivery, receiver HTTPS validation and atomic installation. Drop-in removed and daemon reloaded afterward.

Worker-container Python PID 49 imported actual app and `tasks.weppcloud_token.load_weppcloud_token`, then stayed alive across replacement:

| Observation | Before | After |
| --- | --- | --- |
| SHA256 | `ecb851c435a3a88e71efa32f8af3f0b7e74e29a0b12b0a3f2e814f4fd15d21a4` | `0ae4c339c49ff3bf1c517b7bc1718cfb9f117f00e733f637274b88812078bd41` |
| jti | `57c2073977c54dfd97813f8e50db4b10` | `8148d2256c47480cb11f4522d6870137` |
| exp | 1800808967 | 1800809041 |

Fresh worker-loaded token produced HTTP 400 `validation_error`, `missing_file`, `payload.zip`, proving authentication passed without enqueuing work. Response error_id `fc4346d0979a45ba8a3044cdd485a8cb`.

Normal service start then reported `not_due`, unchanged fingerprint, exit 0. Restricted key attempts `uname -a` and install `invalid-token` both failed; subsequent status fingerprint was unchanged.

## Timer-triggered rotation

Temporarily changed timer using runtime-only drop-in: cleared OnCalendar, OnActiveSec=3s, RandomizedDelaySec=0, AccuracySec=1s, Persistent=false. Temporary service drop-in enabled force. Restarted the timer, not the service.

Timer LastTriggerUSec: **2026-10-26 16:45:39 UTC**. Service completed at 16:45:42 with Result=success, ExecMainStatus=0.

Same-process worker probe PID 89 observed:

- Before: `0ae4c339c49ff3bf1c517b7bc1718cfb9f117f00e733f637274b88812078bd41`.
- After: `8aeb895e2b0fcbaa713857f1be391c1a58d9b776e803adb7c7f8fc1b01907190`.
- New jti: `f596899cc3c647ceb440e074ee99e5c8`; iat 1793033141; exp 1800809141 (2027-01-24 16:45:41 UTC).
- Fresh token accepted by API: HTTP 400 `missing_file`.

Both runtime overrides removed, daemon reloaded, normal daily timer restarted. Enabled timer's next trigger is 2026-10-27 around 08:00 UTC (up to 15-minute jitter). No force remains in installed units.

## Runtime and security checks

Token directory mode 0700, token and previous files mode 0600, owned by roger. App/worker run under unchanged identities. Container StartedAt remained unchanged across both rotations:

- worker: `2026-10-26T16:43:26.752630458Z`.
- web: `2026-10-26T16:43:26.782742733Z`.

A structurally valid forged signature was rejected by the live API with HTTP 401 and by restricted installation; installed fingerprint remained unchanged. `systemd-analyze --user verify` passed. Final normal timer next trigger: 2026-10-27 08:10:48 UTC. Final normal service receipt: `not_due`, unchanged fingerprint.

Public Culvert website returned HTTP 200. No bearer tokens/private keys retained in this artifact. Final script/unit/helper hash parity and review dispositions recorded in final review artifacts.

## Claims and limits

Implemented, deployed and validated through actual timer, service, restricted SSH, HTTPS verification, generated credential file, existing mount, and same-process app loader. Unit tests additionally exercise malformed state, atomic write failure retention and expired-token scheduling. No full hydrological/model analysis rerun or repair claimed. Off-host notification remains unconfigured pending a destination; local systemd/journal/receipt monitoring is active. First ordinary daily trigger remains a follow-up observation.
