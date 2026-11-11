# Security review - Redis credential transport hardening

**Status**: Pending implementation and independent security review
**Reviewer**: Unassigned
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

Populate findings with severity, surface, attack path, evidence, action and
disposition. **Gate status: FAIL/PENDING**; no implementation exists and F5 must
remain blocked until this review passes.
