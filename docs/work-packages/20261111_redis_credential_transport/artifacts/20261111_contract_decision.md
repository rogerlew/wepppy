# Redis credential transport contract decision

**Status**: Proposed; not ratified
**Date**: 2026-11-11 UTC
**Starting revision**: `f0df22e5f8d2ae6255c6aa0e718394ad69a41b51`

## Decision Required

Define how every WEPPcloud Redis consumer receives the existing mounted password
without embedding it in a connection URL or process argument. Preserve current
password, default user, topology, logical DBs, TLS options and secret lifecycle.

## Proposed Contract

1. Endpoint configuration contains scheme/network, host, port, DB and TLS/query
   options only. Its string/repr form is nonsecret.
2. Credentials are read from the existing explicit `*_FILE` setting and passed
   to native client `username`/`password` fields or a provider. No new secret
   registry, manager or rotation behavior is introduced.
3. Mounted-file credentials take precedence. A legacy URL with userinfo may be
   accepted during transition only if its secret is separated immediately and
   the retained/re-emitted endpoint is credential-free. Conflicting credentials
   fail according to a ratified explicit rule; no silent fallback.
4. Python sync, async and session clients use constructor kwargs/pools. Go
   services use `redis.Options`. Streamauth clones options only to select DBs 11
   and 0.
5. RQ worker-pool uses installed config-based connection creation rather than
   `-u redis://:password@...`; queue names/counts/classes and DB 9 remain fixed.
6. Redis server consumes a protected runtime ACL/config file for the same
   default-user password rather than `--requirepass <password>` argv. This does
   not authorize ACL user/permission redesign.
7. Healthchecks/operator helpers do not place the password in a URL, `-a` or
   other argv. Any CLI-only ephemeral environment bridge requires explicit
   security review and must never be inherited by long-lived application
   processes or printed.
8. Missing/empty/unreadable credentials fail startup explicitly. No
   unauthenticated fallback is permitted.

## Compatibility Matrix

| Input/state | Required result |
| --- | --- |
| Credential-free endpoint + readable password file | Authenticate to selected DB |
| Credential-free endpoint + missing/empty file | Explicit startup failure |
| Legacy URL userinfo only | Pending transition decision; never re-emit userinfo |
| Legacy URL + matching file | File precedence; normalized endpoint |
| Legacy URL + conflicting file | Pending: fail closed recommended |
| Username + password file | Preserve ACL username when supported |
| No password configured in explicit local fixture | Allow only fixture contract, never deployed fallback |
| Wrong password | Authentication failure, no retry downgrade |

## Alternatives Rejected

- Continue redacting password-bearing URLs: insufficient because the secret
  string still reaches exceptions, argv and client configuration.
- Copy the mounted password into a long-lived environment variable: changes the
  exposure location rather than removing it.
- Add a Redis proxy or secrets manager: outside the evidence and complexity
  budget.
- Introduce new ACL users/permissions in the same migration: changes
  authorization and recovery scope unnecessarily.

## Required Checkpoint

- [ ] Python/RQ reviewer accepts constructor/config interfaces.
- [ ] Go reviewer accepts `redis.Options` sharing/cloning.
- [ ] Redis/operator reviewer accepts ACL/config generation and healthcheck path.
- [ ] Legacy/conflict matrix is ratified.
- [ ] Correctness and security reviewers approve a standalone ancestor
      checkpoint before implementation.

No implementation authority or completion claim is inferred from this draft.
