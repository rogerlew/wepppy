# Security review - Redis credential transport hardening

**Status**: Implementation review in progress; runtime acceptance pending
**Reviewer**: independent `security_reviewer` agent `/root/contract_security`
**Date opened**: 2026-11-11 UTC
**Security impact**: High

## Required Security Checks

- [ ] No password appears in URL userinfo, process argv, rendered Compose,
      config/repr strings, retained logs, errors or validation artifacts.
- [ ] Secret files remain the authoritative deployed input with least-privilege
      mounts and permissions.
- [ ] No raw secret is copied to a long-lived environment variable.
- [ ] Legacy URL credentials are separated once, never re-emitted and follow an
      explicit conflict/precedence contract.
- [ ] Missing, empty, unreadable and wrong credentials fail closed.
- [ ] Redis server ACL/config generation is atomic, permissioned and does not
      weaken default-user authentication or add identities/commands.
- [ ] RQ config does not leak through module repr, CLI help, errors or child argv.
- [ ] Healthchecks and operator tools do not leak through `-a`, URLs or output.
- [ ] Real AUTH tests use only synthetic canaries and retain no credential.
- [ ] Rollback and environment validation preserve availability and data.

## Findings and Verdict

**Gate status: PENDING.** M0 passed in `20261111_m0_security_review.md`.
This review compares the working implementation with checkpoint `ca1034a2b`.
No production deployment or F5 unblock is approved. The implementation is still
being refined; closure requires retained regressions and scoped runtime receipts.

| Finding | Severity and concrete failure path | Disposition |
| --- | --- | --- |
| S1: false-positive Redis health | Medium. Dev/HPC probes initially relied on redis-cli exit status, which can remain zero after AUTH/command failure. Wrong credentials could mark Redis healthy. | Source corrected to require `grep -qx PONG` in all four changed Compose stacks. Executable wrong-password probe evidence pending. |
| S2: endpoint query disclosure | Medium. Python URL helpers initially bypassed the constructor allowlist and re-emitted `ssl_password=canary` or `PASSWORD=canary`. | Shared ingestion now validates option names before endpoint output. Direct reviewer probes confirm clean rejection for both fields and an unknown option; retained regressions pending. |
| S3: credential byte disagreement | Medium. Shell `[[:space:]]` accepted edge NBSP/em-space while native Python/Go rejected them, allowing server startup with unusable client credentials. Python also treats U+001C–U+001F as whitespace, unlike Go's default trim. | Shell now decodes UTF-8 code points and rejects the shared edge-whitespace set; Go applies the matching extra separators. Reviewer probes pass locally; both deployed image families and retained cross-language tests pending. |
| S4: formatted string disclosure | Low. Both `_Password` subclasses inherited `str.__format__`, so a width format exposed the raw password. | Both classes now implement redacted `__format__`; direct Python width-format probe passes. |
| S5: canary persistence regression | Medium. Newly migrated canary/aux Redis sets an empty `REDIS_SAVE_SCHEDULE`, but entrypoint `:-` substitution replaces empty with default snapshots. Former startup explicitly disabled snapshots. | Reported; fix must preserve explicit empty and prove `CONFIG GET save` is empty in migrated fixtures. |
| S6: remaining shared consumers | Medium closure gap. `tools/perf/redis_nodb_cache_stress/run_harness.py` used `redis_url()` as an authenticated input, and `docker/prod-worker-deploy-guide.md` still documented password argv. | Reported for failure-class repair; operator/spec documentation and direct harness regression pending. |

S1–S4 have source-level corrections confirmed during review. They are not a
substitute for the executable evidence named in the disposition. S5/S6 remain
open until their final changes are reviewed.

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
These probes did not read or modify deployed credentials.

ACL creation uses a fresh `mktemp -d` private directory, restrictive creation
umask, mode 0600 and atomic rename; password/hash variables are unset before
server exec and the persistence umask is restored. The CLI helper disables trace
and automatic export before reading credentials, and assigns REDISCLI_AUTH only
to the exec'ed CLI child. This matches the bounded M0 bridge decision. Actual
mode/argv/environment and unusable-file runtime evidence remain required.

The parent reported that `wctl run-status-tests` unexpectedly recreated shared
development Redis while resolving Compose dependencies. It reports the existing
password still authenticates and Redis is healthy, with no rotation or data
deletion. This review did not independently establish workload continuity.
The operations receipt must retain the incident, recovery checks and subsequent
`--no-deps` isolation before environment acceptance is claimed.

## Remaining acceptance gate

Require focused retained regressions for the findings, real AUTH through every
changed service boundary (including dashboard and RQ worker children), correct
DB and expiry behavior, negative credential cases, canary-free argv/log/config
scans, every rendered Compose variant, protected ACL readback, server restart and
rollback, and operations review of the shared-development restart. No full-suite
success is requested or claimed. Final gate remains pending until the exact
candidate and receipts are reviewed.
