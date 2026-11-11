# M0 independent operations review

**Reviewer:** `ops_security_control_agent` (`/root/contract_ops`)
**Date:** 2026-11-11 UTC
**Reviewed baseline:** `824c183770ec87fb156e7ad1bbe8f600115ed388` plus the
uncommitted transport contract. No implementation or runtime acceptance reviewed.
**Verdict:** APPROVE M0 contract after re-review of the amendments described
below. The native credential/hashed ACL design is operationally viable within
the existing stack. Implementation and runtime approval remain pending.
No deployment, service restart, credential rotation or shared-state write was
performed during this review.

## Findings

1. **Medium — valid file terminators need an explicit rule.** The contract bans
   surrounding whitespace, but `docker/README.md` creates the password with
   Python `print`, producing a trailing LF. The existing server removes trailing
   LF via command substitution; Python and Go trim whitespace. Define the
   normalized password separately from file framing, preserving ordinary
   LF-terminated secret files. Reject incompatible content without echoing or
   rewriting it. Test identical AUTH across server, Python, Go and probe for
   both no-terminator and trailing-LF files. **Closed for M0:** the amended
   contract explicitly removes trailing LF file terminators before validating
   password content. Runtime parity remains an M4 test.

2. **Medium — restrict the ACL-generation umask to its private files.** The live
   Redis process is uid/gid 0 with umask 0022; the custom Compose entrypoint
   bypasses the upstream image's identity switch. Applying umask 077 to the
   eventual server changes future persistence-file modes. Preserve the incoming
   umask after protected-file creation, and keep the current identity. The
   existing contract says to preserve identity and persistence but should state
   this permission boundary explicitly before M0. Do not introduce a privilege
   drop, data chmod/chown or new writable data mount in this work. **Closed for
   M0:** the amended contract explicitly preserves the original server umask.

3. **Medium — isolated Compose requires more than a project name.** Canonical
   dev Compose hard-codes `container_name`, `wepppy-net`, subnet
   `172.28.0.0/16`, Redis port 6379 and `.docker-data/redis`. The smoke overlay
   must explicitly override/reset those fields, use private synthetic secret
   inputs and disposable data, and avoid the live default network. Render and
   mechanically inspect the selected service definitions before starting them.
   A generic `-p` is insufficient. Add these constraints to acceptance planning
   before running M4; retain the exact overlay and bounded service command.
   **Closed for M0:** the amended acceptance contract names fixed container,
   network, port and live-data overrides. Inspect the actual M4 render before
   execution.

4. **Medium — RQ config selection and kwargs require adapter evidence.** The
   installed `rq.cli.helpers.CliConfig.connection` chooses `self.url` before
   config; Click populates it from `RQ_REDIS_URL`. Worker-only and wepp3 Compose
   set that variable. Merely adding `-c` would bypass the adapter. Also,
   `get_redis_from_config` forwards password and selected TLS fields, but omits
   username and socket options. The launcher must normalize legacy input and
   prevent the CLI env override, and either use an owned connection class or
   explicit launcher that preserves all accepted options. Contract already
   requires this behavior; verify it with external-worker env fixtures in M3.
   **Closed for M0:** the amended contract specifies an owned connection adapter
   and explicit empty `--url` to suppress Click's environment-derived URL while
   the adapter reads the original endpoint input.

5. **Low — dashboard already has a separate-password path.** The sibling
   `rq_dashboard.app.create_app` supports `RQ_DASHBOARD_CONFIG`;
   `web.setup_rq_connection` supplies `RQ_DASHBOARD_REDIS_PASSWORD` via
   `client_options` while retaining a displayable endpoint. A small owned
   file-backed config module may be enough; check all page/instance-switch
   paths and safe config formatting. Do not introduce a sibling-repository
   deployment dependency without identifying its exact deliverable/revision.

## Observed environment and safe implementation constraints

Read-only `docker inspect` and `docker exec` established that the running Redis
image is `sha256:646a47c903c5c45f99081094d8c3ba51ec2a1091babf42dc5a928cef024e6fcd`,
configured with the owned entrypoint, a writable `/data`, and read-only mounted
secret/script. `sha256sum`, `mktemp`, `stat`, `redis-cli` and `redis-server` are
available. Pin the acceptance receipt to the actual image ID; production Compose
currently references mutable `redis:latest`. This review does not authorize an
image update. Verify required tools independently in the pinned Alpine image
used by canary/auxiliary checks.

The live image also has `iconv`, `od`, `tr`, `cmp`, `awk` and `perl`. UTF-8
validation can discard `iconv` output; NUL validation can compare the original
file to its NUL-filtered stream without printing either. The Alpine canary image
is not locally cached; this review does not establish its tool availability.

Status/preflight canonical development services explicitly run as the configured
UID/GID so mode-0600 secrets are readable. The test overlay must preserve those
identities and file-read permissions; testing everything as root is insufficient.
Runtime ACL input should live outside `/data`, use a private directory and
atomic replacement, and never expose a password hash in receipts or logs.

The temporary `REDISCLI_AUTH` bridge is acceptable for a bounded CLI child if it
is never exported to the launcher or long-lived service, shell tracing is
disabled before reading, and stdout/stderr contain no credential. Missing/empty
file failures and PONG checking remain mandatory. Runtime implementation still
requires independent security review.

## M4 evidence required for operations approval

Retain nonsecret candidate revision/image/identity/mount mappings and selected
rendered Compose topology; never archive raw environment dumps or ACL files.
Verify isolated network/data/ports before startup. Run positive and wrong/missing
credential cases for every changed process boundary and inspect actual argv.
Test restart with a sentinel key persisted in disposable data, then restore the
known-good entrypoint/config against the same disposable data and verify AUTH,
sentinel retention and relevant DBs. Preserve original appendonly, appendfsync,
save, AOF preamble and keyspace-notification settings.

Cleanup must target only names recorded for this acceptance run. Never invoke
shared `down`, prune, flush, volume deletion or the production deploy script for
this local canary. The canonical deployment entry point remains
`scripts/deploy-production.sh`; deployment and production rollback are outside
this review. No green runtime or F5-unblock verdict is implied by M0 approval.
