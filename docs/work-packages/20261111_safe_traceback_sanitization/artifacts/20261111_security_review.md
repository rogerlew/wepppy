# Security review - Safe traceback sanitization

**Status**: Pending implementation and independent security review
**Reviewer**: Unassigned
**Date opened**: 2026-11-11 UTC
**Security impact**: High

## Required Security Checks

- [ ] Locals and environment mappings are never captured.
- [ ] Only explicit canonical secret sources are read; no globbing or arbitrary
      `*_FILE` traversal exists.
- [ ] Source ownership is selected per process. Environment presence alone does
      not authorize a read, and downstream-only/stale Kubernetes paths do not
      trigger a fail-closed diagnostic.
- [ ] F5 does not decrypt SOPS, query Kubernetes Secret objects, read
      `flux-system/sops-age` or add workload RBAC.
- [ ] No process registry/cache/module collection retains secret values after a
      render call; no serialization/repr/debug accessor exposes snapshots.
- [ ] Raw, percent-encoded and JSON-escaped canaries are absent from API, logging,
      run-file, RQ Redis and publication sinks.
- [ ] URI credentials, Authorization/cookies, bearer/JWT, PEM and sensitive
      assignments receive structural redaction.
- [ ] Every constituent of the comma-delimited authorization JWT key ring, the
      WEPPcloudR bearer token/private key and the owning control plane's current
      service-account token are included in synthetic source coverage.
- [ ] Message, notes, causes, contexts and ExceptionGroups are all sanitized.
- [ ] Formatter integration covers third-party `exc_info` and cannot be bypassed
      by an alternate production handler.
- [ ] Kubernetes-captured stdout/stderr, uncaught interpreter output and the
      WEPPcloudR control-plane reconciliation logger are dispositioned with
      direct final-output evidence.
- [ ] Sanitization occurs before RQ superclass persistence and before file/status
      writes.
- [ ] Source-read/sanitizer failure discards raw diagnostics and emits only the
      fixed safe message/error ID.
- [ ] Existing authorization is neither weakened nor treated as sanitization.
- [ ] Tests use synthetic secrets only and do not print failed canaries.
- [ ] Production-equivalent mounted-file tests preserve existing non-root
      identity, paths and `0444` modes without reading real cluster secrets.
- [ ] Full pytest/npm receipts and direct sink checks bind to the reviewed commit.

## Findings and Verdict

Populate severity, surface, attack path, evidence, action and disposition.
**Gate status: FAIL/PENDING**; F5 remains open and no implementation exists.
