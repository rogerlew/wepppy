# Culvert submission JWT renewal

The Culvert app on **wepp2** submits to **wepp1 / wepp.cloud**. A daily persistent
**user systemd timer on wepp1**, running as the existing `roger` operator, renews
its registered submit-only JWT before expiration. The application reads a token
file for each task invocation; rotations do not restart containers.

Contract: [Culvert JWT renewal](../schemas/culvert-jwt-renewal-contract.md).
Decision: [ADR-0106](../adrs/ADR-0106-culvert-jwt-renewal.md).
Implementation/evidence: [work package](../work-packages/20261026_culvert_jwt_renewal/package.md).

## Identity, schedule, and ownership

The principal remains `culvert-batch-submit-90d`, audience `rq-engine`, class
`service`, group `culverts`, scope **only** `culvert:batch:submit`. Each renewal
has a fresh `jti` and a 90-day lifetime. The timer checks daily at 08:00 UTC with
up to 15 minutes jitter and catches up after downtime. It renews with at most
30 days remaining. Roger owns operation and recovery; signing secrets stay in
the WEPPcloud issuer on wepp1. This does not change browse-token lifetimes or
introduce `rq:status`, retry, or administrative privileges.

## Installed components

| Host | Path | Purpose |
| --- | --- | --- |
| wepp1 | `~/.local/libexec/weppcloud-culvert-token-rotation.py` | Issuer orchestration, from `scripts/culvert_token_rotation.py` |
| wepp1 | `~/.config/systemd/user/weppcloud-culvert-token-renew.{service,timer}` | Daily user service/timer, from `scripts/systemd/` |
| wepp1 | `~/.config/weppcloud-culvert-renewal/id_ed25519` | Dedicated delivery key, mode 0600, directory 0700 |
| wepp1 | `~/.config/weppcloud-culvert-renewal/known_hosts` | Pinned wepp2 SSH host key |
| wepp1 | `~/.local/state/weppcloud-culvert-renewal/last-attempt.json` | Sanitized receipt: status/time and installed fingerprint/claims |
| wepp2 | `~/.local/libexec/weppcloud-culvert-token-rotation.py` | Same script, fixed SSH receiver mode |
| wepp2 | `/workdir/culvert_app_instance_dir/.weppcloud-auth/token` | Current credential, mode 0600 in a 0700 directory |
| wepp2 | `/workdir/culvert_app_instance_dir/.weppcloud-auth/previous` | One prior credential for recovery, mode 0600 |
| wepp2 | `/workdir/Culvert_web_app/culvert_app/tasks/weppcloud_token.py` | Per-invocation loader copied from `dev-package/scripts/weppcloud_token.py` |

The client loader/task change is retained in Culvert_web_app commit `a2bd7bf62`;
the operator script and units are retained in WEPPpy commit `2b334ded7`.

The existing instance mount exposes the credential to the container as
`/app/instance/.weppcloud-auth/token`. Set this exact path in
`WEPPCLOUD_TOKEN_FILE` in the app's existing `.env`. The integration task calls
`load_weppcloud_token()` instead of reading `WEPPCLOUD_TOKEN` directly.
Configured missing, empty or unreadable files fail explicitly. Environment-only
clients remain compatible when `WEPPCLOUD_TOKEN_FILE` is absent. Never fall back
to the stale environment token when a configured file fails.

## Installation and trust boundary

Install the reviewed script on both hosts under the paths above and the units
on wepp1. Use the existing `roger` identity; confirm
`loginctl show-user roger -p Linger` gives `Linger=yes` and
`systemctl --user is-system-running` succeeds. No new sudo or Docker grants are
needed. Do not use full WEPPcloud deployment/restarts for this operator-only
installation.

Generate a dedicated Ed25519 key on wepp1. Pin the wepp2 host public key using
an independently authenticated operator SSH session; never disable host-key
checking. Add only its **public** key to wepp2's `~/.ssh/authorized_keys` with:

```text
restrict,from="100.127.248.45",command="/usr/bin/python3 /home/roger/.local/libexec/weppcloud-culvert-token-rotation.py receive" ssh-ed25519 <PUBLIC_KEY> culvert-jwt-renewal
```

`100.127.248.45` is the verified wepp1 Tailscale address at installation. Recheck
it during host replacement. SSH explicitly targets `wepp2.tail305ec9.ts.net`
with host-key alias `wepp2`; the bare hostname resolves to a LAN address on
wepp1 and must not be used as the transport destination. The receiver matches `SSH_ORIGINAL_COMMAND` exactly
against `status` and `install`; it never evaluates it. This key cannot run a
shell, forward ports, request a PTY, choose another destination file, or mint
tokens. Compromise of the preexisting operator account remains outside that
key restriction and retains that account's existing privileges.

Bootstrap the credential by invoking the service before enabling file
consumption. Absent receiver state is supported and causes issuance. Install the
helper and the task import/call, set `WEPPCLOUD_TOKEN_FILE`, and reload the app
and idle worker once through their existing Compose file. Confirm no queued or
started Culvert work before a restart. Subsequent rotations need no reload.

```bash
# wepp1, as roger
systemctl --user daemon-reload
systemctl --user start weppcloud-culvert-token-renew.service
systemctl --user enable --now weppcloud-culvert-token-renew.timer
```

Keep credentials and backups outside Git. The receiver authenticates an empty
HTTPS POST against the fixed public endpoint before atomic replacement; it
requires the expected HTTP 400 `missing_file` response. TLS verification stays
enabled, redirects are denied, and no model job is enqueued. Status/receipts
contain fingerprints and selected claims, never the bearer token. Installation
keeps one previous token; it is not revoked during the overlap.

## Routine monitoring

```bash
# wepp1, as roger
systemctl --user status weppcloud-culvert-token-renew.timer
systemctl --user status weppcloud-culvert-token-renew.service
systemctl --user list-timers weppcloud-culvert-token-renew.timer
journalctl --user -u weppcloud-culvert-token-renew.service --since '7 days ago'
cat ~/.local/state/weppcloud-culvert-renewal/last-attempt.json
```

A successful oneshot service normally becomes `inactive (dead)` with exit 0;
that is not a failure. `status=not_due` is healthy when expiry is more than 30
days away. `status=renewed` includes the verified new fingerprint and expiry.
Nonzero exit, `status=failed`, or no successful daily check is actionable.
A service timeout can leave the previous receipt, so monitor its age as well
as its status and systemd result.

Off-host alert delivery is **not configured** until an operator supplies a
destination. Journal and durable local status are available; they are not a
claim that anyone was notified. Inspect the first scheduled run after rollout.

## Manual renewal and end-to-end acceptance

To force issuance through the real systemd unit, create a temporary runtime
unit override on wepp1 (the normal timer always uses the expiry threshold):

```bash
mkdir -p "$XDG_RUNTIME_DIR/systemd/user/weppcloud-culvert-token-renew.service.d"
cat > "$XDG_RUNTIME_DIR/systemd/user/weppcloud-culvert-token-renew.service.d/force.conf" <<'UNIT'
[Service]
ExecStart=
ExecStart=/usr/bin/python3 %h/.local/libexec/weppcloud-culvert-token-rotation.py renew --force
UNIT
systemctl --user daemon-reload
systemctl --user start weppcloud-culvert-token-renew.service
rm "$XDG_RUNTIME_DIR/systemd/user/weppcloud-culvert-token-renew.service.d/force.conf"
systemctl --user daemon-reload
```

Always remove the override, even after failure; confirm `systemctl --user cat`
shows no forced command. Read the installed credential through the actual
worker's `tasks.weppcloud_token.load_weppcloud_token` function and compare only
SHA256/expiry/jti against the service receipt. Prove rereading in the same
process across replacement and unchanged container start times. Authenticate
an empty POST using that loaded token and require HTTP 400 `missing_file`.
A second ordinary service start must report `not_due` without replacing the
credential. For timer-path acceptance, additionally use a temporary runtime timer drop-in
that clears `OnCalendar`, sets `OnActiveSec=3s`, `RandomizedDelaySec=0`,
`AccuracySec=1s`, and `Persistent=false`; restart the timer and observe its
`LastTriggerUSec` and service result. Remove both temporary drop-ins, reload,
and restart the ordinary timer immediately afterward. Verify its next daily
trigger and the absence of `--force`.

These checks prove renewal and consumption, not a complete model
analysis. Never print the token while collecting evidence.

## Failure and recovery

- **Issuance fails:** check wepp1's deployed `wctl` preset, WEPPcloud container,
  Docker permissions and issuer config. Script deliberately suppresses child
  output because it may contain secrets.
- **SSH fails:** verify Tailscale, pinned host key, source address restriction,
  public key entry, and receiver installation. Use operator access for diagnosis;
  do not relax host verification or permit a general shell for the delivery key.
- **API rejects candidate:** check expiry, registered service identity and
  server-side authorization. Old token remains installed when validation fails.
- **Installed file is malformed:** status fails explicitly. Disable the timer,
  retain the damaged file privately for diagnosis, move it out of the fixed
  token path, then start renewal to provision valid state. Do not fall back to
  an old env token silently.
- **Failure after replace/readback:** status may be ambiguous; inspect the
  installed fingerprint before retrying. Atomic replacement prevents partial
  token reads, but does not make remote acknowledgment infallible.
- **Rollback:** disable the timer; securely pass the still-valid `previous`
  credential to the same restricted `install` action. Receiver validates it and
  stores the displaced current credential as `previous`. Never use the token
  in a command-line argument. A rollback to env-only behavior requires reverting
  the app helper call/file setting and a deliberate app reload.

All renewal operations serialize through file locks. No automatic revocation,
model retry, batch submission or full-stack restart is performed.

To retire this mechanism, disable the timer with `systemctl --user disable --now
weppcloud-culvert-token-renew.timer`, remove only the `culvert-jwt-renewal`
public-key entry from wepp2's `authorized_keys`, and remove its dedicated private
key from wepp1. Preserve the installed token until another credential source is
configured and verified. Removing it while `WEPPCLOUD_TOKEN_FILE` is set breaks
new submissions. If the delivery key is compromised, remove its authorized-key
entry first, then replace the key and inspect the installed credential before
reenabling the timer.
