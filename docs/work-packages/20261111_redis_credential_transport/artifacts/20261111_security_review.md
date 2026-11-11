# Security review - Redis credential transport hardening

**Status**: PASS for implementation and scoped environment acceptance
**Reviewer**: independent `security_reviewer` agent `/root/contract_security`
**Date opened**: 2026-11-11 UTC
**Security impact**: High
**Reviewed candidate**: `db7ef7cb7` against contract checkpoint `ca1034a2b`

## Required Security Checks

- [x] No generated password appears in URL userinfo, process argv, rendered Compose,
      config/repr strings, retained logs, errors or validation artifacts.
- [x] Secret files remain the authoritative deployed input with existing
      mounts and permissions.
- [x] No raw secret is copied to a long-lived environment variable.
- [x] Legacy URL credentials are separated once, never re-emitted and follow an
      explicit conflict/precedence contract.
- [x] Missing, empty, unreadable and wrong credentials fail closed.
- [x] Redis server ACL/config generation is atomic, permissioned and does not
      weaken default-user authentication or add identities/commands.
- [x] RQ config does not leak through module repr, CLI help, errors or child argv.
- [x] Owned healthchecks and operator invocations avoid `-a`, secret URLs and output.
- [x] Real AUTH tests use synthetic canaries and publish no credential.
- [x] Isolated rollback retains data and explicit consumer restart restores
      availability; shared-development continuity limits are recorded below.

## Findings and Verdict

**Implementation security gate: PASS. Final scoped security gate: PASS.**
M0 passed in `20261111_m0_security_review.md`. All six implementation findings
are closed for candidate `db7ef7cb7e1d05400b6acca333526dfe80c7b417`. Final
candidate-bound service probes and runtime scans were reviewed. No unresolved
medium/high security finding remains in the assessed scope. This satisfies the
security prerequisite for F5; package closure still requires the other independent
gates. This review does not approve a production deployment.

| Finding | Severity and concrete failure path | Disposition |
| --- | --- | --- |
| S1: false-positive Redis health | Medium. Dev/HPC probes initially relied on redis-cli exit status, which can remain zero after AUTH/command failure. Wrong credentials could mark Redis healthy. | CLOSED. All four changed Compose stacks require PONG. Private `restart-negative.txt` and scoped validation receipt establish wrong-password rejection through the actual probe. |
| S2: endpoint query disclosure | Medium. Python URL helpers initially bypassed the constructor allowlist and re-emitted `ssl_password=canary` or `PASSWORD=canary`. | CLOSED. Shared ingestion validates names before endpoint output; retained `test_endpoint_helpers_reject_credential_query_options` and direct reviewer probes confirm clean rejection. |
| S3: credential byte disagreement | Medium. Shell `[[:space:]]` accepted edge NBSP/em-space while native Python/Go rejected them, allowing server startup with unusable client credentials. Python also treats U+001C–U+001F as whitespace, unlike Go's default trim. | CLOSED. Shared explicit whitespace set is applied in shell/Go; retained shell/Python parity and Go config tests pass. Independent candidate probe passes 31 cases each in Debian and pinned Alpine Redis images. |
| S4: formatted string disclosure | Low. Both `_Password` subclasses inherited `str.__format__`, so a width format exposed the raw password. | CLOSED. Both classes implement redacted `__format__`; direct probe and retained format-specifier regression pass. |
| S5: canary persistence regression | Medium. Newly migrated canary/aux Redis sets an empty `REDIS_SAVE_SCHEDULE`, but entrypoint `:-` substitution replaces empty with default snapshots. Former startup explicitly disabled snapshots. | CLOSED. Unset-only substitution preserves explicit empty. Inspected private `alpine.txt` and scoped receipt confirm pinned Alpine real AUTH and empty `CONFIG GET save`. |
| S6: remaining shared consumers | Medium closure gap. `tools/perf/redis_nodb_cache_stress/run_harness.py` used `redis_url()` as an authenticated input, and `docker/prod-worker-deploy-guide.md` still documented password argv. | CLOSED within recorded inventory. Performance resolver/legacy inputs now construct native kwargs and normalize display; real DB13 AUTH passes. Operator/spec docs, host flush credential transport and deployment probe migrated. Dormant standalone dashboard and explicit external legacy input limits are dispositioned in the failure matrix. |

No unresolved medium/high source finding remains in the assessed scope. Explicit
legacy input can still arrive in an external environment or user-supplied CLI
argument; owned launchers/examples no longer generate password arguments. The
performance harness documents that explicit CLI endpoint arguments must be
credential-free. This is not a claim to erase secrets supplied by outside callers.

## Review evidence

Reviewed Python settings and RQ connection adapter, session construction,
dashboard sibling API/config module, Go endpoint parsing/provider/config and
streamauth cloning, shell password/ACL/CLI helpers, changed Compose stacks,
worker startup, wctl RQ helper and source inventory.

Direct read-only/local probes used synthetic values only. Before corrections,
they reproduced width-format disclosure and shell/native whitespace disagreement.
After corrections, Python endpoint helpers reject the two credential-like query
names without printing inputs, and password width formatting contains no canary.
The shell helper accepts ordinary ASCII and valid accented/emoji UTF-8; rejects
NUL, overlong encoding, surrogate encoding, code points above U+10FFFF, truncated
sequences, isolated continuation bytes, ASCII edge whitespace, NBSP, em-space,
U+001C, CRLF, embedded LF and LF-only files. Only case names/results were printed.
These probes did not read or modify deployed credentials. On candidate
`db7ef7cb7`, the reviewer additionally executed 31 synthetic framing cases in
disposable `--rm --network none` containers using `redis:latest` (Debian) and
the pinned `redis:8.2.1-alpine` digest. Both passed every case, including all four
U+001C–U+001F separators and the non-ASCII edge whitespace cases.

ACL creation uses a fresh `mktemp -d` private directory, restrictive creation
umask, mode 0600 and atomic rename; password/hash variables are unset before
server exec and the persistence umask is restored. The CLI helper disables trace
and automatic export before reading credentials, and assigns REDISCLI_AUTH only
to the exec'ed CLI child. This matches the bounded M0 bridge decision. The
scoped receipt records mode 0600/parent 0700, canary-free argv/config/log scans,
wrong/missing/empty-file failures and restart/rollback marker retention. The
reviewer inspected the private receipt files in memory, checked that they lacked
the synthetic canary before displaying summaries, and found their reported
results consistent with the package receipt. Raw password and hash were not
printed or committed.

Inspected `client.log` proves native AUTH on DBs 0/2/9/11/13/14/15, async PubSub,
session round trip/expiry, six RQ workers and job result 42, Go health and
dashboard HTTP. Operator receipts prove DB13 harness AUTH and a DB9 flush-helper
dry-run without FLUSHDB. The seven Compose render receipts and initial runtime
image/user/argv/log receipt are present.

Final `20261111_final-candidate.json` binds the exact commit and rebuilt Go image
IDs to a fresh successful client probe, six registered workers, job
`2c42074f-f19b-49c4-b26a-73f24fbb7267` returning 42, and clean argv/config/log
scans for all five isolated services. Redis umask remains 0022. The final
negative-service receipt records exit 1 for both Go services with wrong/missing
files, RQ production readiness with wrong credentials, and private ACL creation
on a read-only filesystem. Dashboard wrong-password and empty-file cases also
exit 1 with clean canary scans. Final Redis config readback preserves production
persistence/keyspace settings; pinned Alpine separately preserves empty save.
After rollback/restore, affected consumers were explicitly restarted. No claim
of automatic worker recovery after Redis loss is made.

The parent reported that `wctl run-status-tests` unexpectedly recreated shared
development Redis while resolving Compose dependencies. It reports the existing
password still authenticates and Redis is healthy, with no rotation or data
deletion. This review did not independently establish workload continuity.
The operations receipt must retain the incident, recovery checks and subsequent
`--no-deps` isolation before environment acceptance is claimed.

## Scope limits

Focused evidence closes this security gate for the reviewed candidate. The
independent operations gate owns the shared-development restart disposition and
cleanup decision. No full-suite success is requested or claimed. Production
rollout, remote host parity, automatic recovery after Redis loss and
incident-free shared-development execution are not claimed. Real AUTH acceptance
uses the current default-user TCP topology; TLS/Unix option preservation has
parser/constructor coverage, not a remote TLS deployment claim.
