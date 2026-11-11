# Redis credential transport contract decision

**Status**: Ratified for M0 implementation checkpoint
**Date**: 2026-11-11 UTC
**Starting revision**: `f0df22e5f8d2ae6255c6aa0e718394ad69a41b51`

## Decision Required

Define how every WEPPcloud Redis consumer receives the existing mounted password
without embedding it in a connection URL or process argument. Preserve current
password, default user, topology, logical DBs, TLS options and secret lifecycle.

## Ratified Contract

The canonical [transport contract](../../../schemas/redis-credential-transport-contract.md)
supersedes the draft bullets below where more specific. Independent M0
correctness, security and operations reviews passed in the adjacent `m0_*_review`
artifacts. In particular: conflicting passwords fail; LF framing is accepted;
RQ uses an owned connection adapter plus explicit empty --url; streamauth retains
its own timeout overrides; ACL creation restores the persistence umask.

## Original Proposal (resolved by canonical contract)

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

- [x] Python/RQ reviewer accepts constructor/config interfaces.
- [x] Go reviewer accepts `redis.Options` sharing/cloning.
- [x] Redis/operator reviewer accepts ACL/config generation and healthcheck path.
- [x] Legacy/conflict matrix is ratified.
- [x] Correctness and security reviewers approve a standalone ancestor
      checkpoint before implementation.

Implementation may proceed after the standalone M0 commit. No runtime acceptance
or F5 unblock is implied.
