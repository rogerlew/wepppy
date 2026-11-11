# M0 security review: Redis credential transport

**Reviewer:** independent `security_reviewer` agent `/root/contract_security`
**Date:** 2026-11-11 UTC
**Scope:** proposed transport contract, current source and one isolated ACL
semantic probe. No implementation or deployment approval.
**Verdict:** PASS for the contract checkpoint. Implementation/runtime security
review remains PENDING; F5 remains blocked until M4/M5 acceptance.

## Findings and disposition

No unresolved medium/high contract findings remain after the following
clarifications. These dispositions approve requirements, not unimplemented code.

- **Low, resolved: file framing ambiguity.** The original contract prohibited
  surrounding whitespace without distinguishing a conventional trailing LF from
  password bytes. `docker/redis-entrypoint.sh` currently removes trailing LF
  through command substitution; `wepppy/config/secrets.py:get_secret` and both Go
  config readers trim surrounding whitespace. An ambiguous replacement could
  reject existing files or authenticate different bytes. The final contract's
  “Resolution and compatibility” section permits existing LF terminators and
  validates the remaining password without printing it. Incompatible deployed
  input blocks rollout rather than causing rotation or silent normalization.
- **Medium implementation risk, addressed in contract: RQ option loss.** Installed
  `.venv/lib/python3.12/site-packages/rq/cli/helpers.py:get_redis_from_config`
  omits username and general socket options in its ordinary config branch.
  Config-only migration could silently switch ACL identity or drop TLS-related
  settings. “Workers and dashboard” now requires an owned connection adapter,
  credential-free config module and a precedence regression for Click's
  `RQ_REDIS_URL` default. The final review must verify this behavior in actual
  worker processes, including child reconstruction.

## Security decisions accepted

Mounted files remain authoritative. Missing/empty/unreadable files cannot fall
back to legacy environment or URL credentials. Conflicting independently supplied
passwords fail with a constant diagnostic; percent decoding occurs once. Parser
errors must not carry raw URLs or exception chains. Credential-bearing parsed
URLs cannot be retained in caches. Nonsecret endpoint builders must reject
credential query settings rather than forwarding them into logs/config output.

The default-user ACL line preserves existing authorization scope: all commands,
keys and Pub/Sub channels, with password authentication. Redis documents that
`requirepass` configures the default user's password and supports SHA-256 values
in external ACL files. No new user or permission restriction is proposed.
[Redis ACL documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/).

The ACL file and its hash are secret material: a private runtime directory,
mode 0600, atomic replacement and failure on unusable storage are required.
Implementation must verify safe directory/file ownership and avoid following
attacker-controlled symlinks. Restricting the ACL creation umask must not alter
the existing persistence umask, runtime user or volume ownership.

The `REDISCLI_AUTH` bridge is approved only for the short-lived CLI child. Redis
documents this environment input as the alternative to password arguments.
It must not appear in Compose environment, a parent application's environment,
argv, shell traces or retained output. Same-UID/privileged process inspection can
still read that child's environment; this bounded exposure is not represented as
memory secrecy and introduces no new long-lived secret input.
[Redis CLI documentation](https://redis.io/docs/latest/develop/tools/cli/).

## Evidence and remaining implementation gate

Source reviewed: Python settings/secrets, RQ startup and installed RQ helper,
status2/preflight2 config and main logging, streamauth construction, Redis
entrypoint, dev/prod Compose, canary/auxiliary probes and secret documentation.
The confirmed existing URL/argv paths remain defects pending implementation.

A disposable `docker run --rm --network none` probe using the already available
`redis:latest` image reported Redis 8.6.2 and existing `sha256sum`/`mktemp` tools.
Inside that container only, a randomly generated synthetic password was hashed
via stdin into a private ACL file. Redis listened only on a temporary Unix
socket with persistence disabled. Results: authenticated PING returned PONG;
missing authentication returned NOAUTH; wrong password returned WRONGPASS and
NOAUTH. Only the PASS summary was retained. No live Redis, mounted secret,
network, data volume or running service was changed. This proves the proposed
ACL syntax semantics on that local image, not production-equivalent acceptance.

Final security review requires real AUTH for every migrated client/process,
canary-free endpoint/config/repr/error/log/argv evidence, file and directory
permission/failure tests, non-inherited CLI credentials, correct logical DBs,
streamauth's own timeout/retry overrides, RQ registration/job execution,
dashboard connectivity, every Compose variant and restart/rollback evidence.
Assert missing/wrong credentials fail; do not infer success from mocks or source
scans. Explicit Compose isolation must replace fixed names, network, ports and
live Redis bind paths before starting synthetic-credential services.
