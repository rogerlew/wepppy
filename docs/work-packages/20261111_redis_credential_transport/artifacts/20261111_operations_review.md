# Independent operations review

**Reviewer:** `ops_security_control_agent` (`/root/contract_ops`)
**Date:** 2026-11-11 UTC
**Status:** Implementation review in progress; scoped runtime approval pending.

## Unintended shared development Redis recreation

The implementation executor reported that `wctl run-status-tests` recreated the
shared development Redis while running the prescribed Go validation command.
Inspection confirms `tools/wctl2/commands/go_services.py` invokes Compose
`run --rm status-build` without `--no-deps`; canonical Compose declares a Redis
dependency, and its configuration had changed during implementation. This was
an unintended mutation outside the planned isolated acceptance boundary.

Read-only inspection recorded the replacement container created at
`2026-11-11T20:45:58.491142286Z` and started at
`2026-11-11T20:46:00.462681296Z`. It used the same image ID recorded during M0:
`sha256:646a47c903c5c45f99081094d8c3ba51ec2a1091babf42dc5a928cef024e6fcd`.
The live `.docker-data/redis` bind and mounted password remained in place;
the new entrypoint, password reader and CLI wrapper were mounted read-only.
Docker reported healthy. The executor additionally reported successful native
AUTH from the existing web container; that claim needs its validation receipt.

Containment: subsequent builder commands must use explicit `--no-deps`. Retain
the healthy shared Redis rather than causing an additional speculative restart.
Check existing worker registrations/heartbeats and status/preflight health
read-only. No data flush, credential rotation or rollback was performed by this
reviewer. Pre-recreation data/job baselines were not captured, so this evidence
does not establish zero interruption or unchanged queued/running jobs. Record
that limitation in closeout; do not describe all execution as isolated.

The plan's concrete commands must reflect the safe builder invocation. A small
follow-up to add `--no-deps` to the Go test wrapper and its command tests would
prevent the same tooling surprise. That change requires reviewing whether any
documented wrapper caller relies on dependency startup.

## Implementation findings

1. **Medium, source corrected; runtime case pending — dev/HPC healthchecks can accept failed AUTH.** Both invoked
   the CLI wrapper with `ping` but omit the required PONG output check. Redis
   CLI command errors can have a successful process exit. Match prod/canary
   output checking and exercise wrong credentials through the actual probe.
   Re-review confirms both definitions now require PONG.

2. **Medium, source corrected; runtime readback pending — canary/aux snapshot behavior changed.** Those paths now set
   `REDIS_SAVE_SCHEDULE=""` through the shared entrypoint instead of using
   `--save ""`. The entrypoint's `:-` expansion substitutes the default when
   empty, enabling snapshots. Preserve explicit empty with the appropriate shell
   expansion and read back `CONFIG GET save` in the acceptance instance.
   Re-review confirms the entrypoint uses the unset-only `-` expansion.

3. **Medium, resolver source corrected; legacy disposition pending — an operator consumer loses AUTH.**
   `tools/perf/redis_nodb_cache_stress/run_harness.py` resolver mode calls
   `redis_url(DB13)` and derives pool kwargs only from the result. The endpoint
   helper is now credential-free, so this consumer loses its password. Migrate
   resolver mode to canonical native pool kwargs and disposition direct URL
   CLI input, raw-input errors and the credential-bearing README example.
   Re-review confirms resolver mode now uses `redis_connection_kwargs(...,
   for_pool=True)` and explicit parser messages no longer interpolate raw URLs.
   Direct `--redis-url` mode remains a legacy credential/argv path requiring
   disposition; do not imply it was migrated by the resolver-mode fix.

4. **Medium, substantially corrected; exact parity pending — file framing validation differs across consumers.** A
   local synthetic test under `LC_ALL=C` found `redis-password.sh` accepts a
   leading U+00A0, whereas Python/Go reject it as surrounding whitespace. Normal
   LF framing passed; empty, NUL, malformed UTF-8 and embedded CR failed. This
   can yield a healthy server/probe while applications fail. Align the accepted
   byte/content rule and add direct parity coverage; never rewrite a real secret
   automatically. Re-review of the codepoint validator confirms leading/trailing
   U+00A0, malformed UTF-8, NUL, CR, embedded LF and empty content reject; ordinary
   and repeated terminal LF and nonspace Unicode pass. Go's `strings.TrimSpace`
   differs from Python for U+001C through U+001F; resolve those four framing cases
   before claiming identical validation.

5. **Medium, inventory disposition pending — canonical deployment helpers
   retain older credential rules.** `scripts/redis_flush_rq_db.sh` exports
   `REDISCLI_AUTH` to its parent shell, prefers `REDIS_PASSWORD` over the mounted
   file, and continues without auth if the file is absent. This is an existing
   behavior rather than a new regression, but it conflicts with the new universal
   file-authority/CLI-child-only rules. `scripts/deploy-production.sh` also has a
   worker-registration check that uses `from_url` with a separately read file
   password rather than the canonical resolver. Inventory and narrowly migrate
   these paths or explicitly document the supported compatibility boundary;
   never execute the destructive flush while validating credential transport.

## Pending acceptance and recovery evidence

Review the final isolated Compose render before execution: unique container and
network names, no inherited fixed subnet/ports, disposable data, synthetic
secret paths, same relevant users/groups and mount permissions. Record exact
source and image identities. Require actual RQ registration/dequeue, session
set/get/expiry, status/preflight and streamauth AUTH, dashboard access, negative
secret cases, argv/log/config scans, and restart/rollback over the same disposable
data with sentinel retention. Require canonical persistence and notification
settings to match, and record cleanup limited to the acceptance-owned resources.

No M4 or F5-unblock approval is granted by this interim artifact. No production
deployment was performed or authorized by this review.
