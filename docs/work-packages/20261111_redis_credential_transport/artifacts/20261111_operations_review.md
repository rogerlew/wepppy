# Independent operations review

**Reviewer:** `ops_security_control_agent` (`/root/contract_ops`)
**Date:** 2026-11-11 UTC
**Candidate:** `db7ef7cb7e1d05400b6acca333526dfe80c7b417`
**Status:** PASS for scoped operations acceptance at the candidate revision.
All five implementation findings are closed. This approves the package's local
operations gate and F5 dependency checkpoint; it does not authorize production
deployment or claim uninterrupted shared-development service.

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
Docker reported healthy. Independent follow-up via `wctl exec -T weppcloud`
confirmed native AUTH/PING, 11 registered worker keys with positive TTLs, and
HTTP 200/OK from both existing status/preflight health endpoints. Only reads
were issued; no job was enqueued, deleted or flushed. These checks establish
current availability, not pre/post job continuity.

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

1. **Medium, closed — dev/HPC healthchecks could accept failed AUTH.** Both invoked
   the CLI wrapper with `ping` but omitted the required PONG output check. Redis
   CLI command errors can have a successful process exit. Match prod/canary
   output checking and exercise wrong credentials through the actual probe.
   Re-review confirms both definitions now require PONG. The private
   `restart-negative.txt` receipt records wrong-health-credential rejection.

2. **Medium, closed — canary/aux snapshot behavior changed.** Those paths now set
   `REDIS_SAVE_SCHEDULE=""` through the shared entrypoint instead of using
   `--save ""`. The entrypoint's `:-` expansion substitutes the default when
   empty, enabling snapshots. Preserve explicit empty with the appropriate shell
   expansion and read back `CONFIG GET save` in the acceptance instance.
   Re-review confirms the entrypoint uses the unset-only `-` expansion. The
   private pinned-Alpine receipt confirms authenticated PONG and empty `save`.

3. **Medium, closed — an operator consumer lost AUTH.**
   `tools/perf/redis_nodb_cache_stress/run_harness.py` resolver mode calls
   `redis_url(DB13)` and derives pool kwargs only from the result. The endpoint
   helper is now credential-free, so this consumer loses its password. Migrate
   resolver mode to canonical native pool kwargs and disposition direct URL
   CLI input, raw-input errors and the credential-bearing README example.
   Re-review confirms resolver mode now uses `redis_connection_kwargs(...,
   for_pool=True)` and explicit parser messages no longer interpolate raw URLs.
   Explicit URL inputs now also pass through canonical native kwargs; operators
   are directed to the file input, and displayed/retained endpoints have userinfo
   removed. The private operator receipt confirms real DB13 AUTH. User-supplied
   legacy URL input remains a transition input, not a recommended argv pattern.

4. **Medium, closed — file framing validation differed across consumers.** A
   local synthetic test under `LC_ALL=C` found `redis-password.sh` accepts a
   leading U+00A0, whereas Python/Go reject it as surrounding whitespace. Normal
   LF framing passed; empty, NUL, malformed UTF-8 and embedded CR failed. This
   can yield a healthy server/probe while applications fail. Align the accepted
   byte/content rule and add direct parity coverage; never rewrite a real secret
   automatically. Re-review of the codepoint validator confirms leading/trailing
   U+00A0, malformed UTF-8, NUL, CR, embedded LF and empty content reject; ordinary
   and repeated terminal LF and nonspace Unicode pass. Go's `strings.TrimSpace`
   differs from Python for U+001C through U+001F; both Go configs now use a trim
   predicate that includes those four codepoints. Focused shell/native parity
   tests cover those bytes, Unicode whitespace, malformed UTF-8 and valid
   nonspace Unicode.

5. **Medium, closed — canonical deployment helpers
   retained older credential rules.** `scripts/redis_flush_rq_db.sh` exported
   `REDISCLI_AUTH` to its parent shell, prefers `REDIS_PASSWORD` over the mounted
   file, and continues without auth if the file is absent. This is an existing
   behavior rather than a new regression, but it conflicts with the new universal
   file-authority/CLI-child-only rules. `scripts/deploy-production.sh` also has a
   worker-registration check that uses `from_url` with a separately read file
   password rather than the canonical resolver. Inventory and narrowly migrate
   these paths or explicitly document the supported compatibility boundary;
   never execute the destructive flush while validating credential transport.
   Current source gives configured files authority and confines auth environment
   to the CLI/timeout child. The registration probe uses canonical native kwargs.
   The private operator receipt shows only `--dry-run --require-redis`; it did
   not execute FLUSHDB. Explicit password-free local fixture behavior is retained
   and documented rather than silently removed.

## Acceptance and recovery evidence

Read-only review of `/tmp/wepppy-redis-transport-acceptance/compose.json` confirms
unique project, internal project-scoped network, no fixed container names or
published ports, isolated Redis data, synthetic Redis/signing files, and preserved
users/mount structure. The containing directory is mode 0700. Application/worker
mounts deliberately preserve canonical repository/run-data structure; the tested
job is only `operator.add(20, 22)` on the isolated Redis queue.

Reviewed private receipts and the public scoped validation record show real AUTH,
six worker registrations, result 42, sessions/expiry, Go and dashboard health,
negative auth/files, private ACL permissions, candidate restart, baseline
rollback/candidate restore over the same disposable data, and retained sentinel.
Five service argv/log scans and all seven rendered Compose variants passed.
The pinned Alpine fixture preserved empty snapshot settings.

## Final verdict and recovery limits

Independently read the retained final receipts for candidate
`db7ef7cb7e1d05400b6acca333526dfe80c7b417`:

- `20261111_final-candidate.json` binds exact running image IDs and confirms
  final rebuilt Go health, all seven logical DBs, async PubSub, session expiry,
  dashboard HTTP, six workers and fresh job
  `2c42074f-f19b-49c4-b26a-73f24fbb7267` returning 42. All five service
  argv/config/log scans pass, and Redis retains umask 0022.
- `20261111_final-negative-services.json` confirms wrong/missing credentials
  terminate both rebuilt Go services with exit 1, wrong credentials terminate
  production RQ readiness with exit 1, and an unwritable private ACL destination
  fails Redis startup with exit 1.
- `20261111_final-dashboard-negatives.json` confirms wrong AUTH and empty
  credential input fail in the actual dashboard image, without canary output.
- `20261111_final-redis-config.json` confirms AOF enabled, everysec fsync, the
  original RDB schedule and AOF preamble, and equivalent keyspace flags `hK`.

These receipts close the final operations approval condition. Recovery evidence
includes restarting affected consumers after Redis rollback/candidate restore:
an intermediate query saw zero registrations, while final consumer startup
restored six workers and completed the fresh job. This supports the explicit
orchestrated recovery path; it does not establish automatic worker recovery
through a Redis outage. Keep that operational requirement visible for rollout.

**Verdict: PASS for the named local M4 operations gate and F5 checkpoint.** No
production deployment was performed or authorized by this review. TLS/Unix
transport has parser/constructor coverage; real AUTH acceptance covers canonical
TCP/default-user topology. Cleanup must remain limited to acceptance-owned
resources. The accidental shared development recreation, current availability
checks and unavailable pre-event workload baseline remain material limits in
the final handoff. No zero-interruption or unchanged-job claim is approved.
