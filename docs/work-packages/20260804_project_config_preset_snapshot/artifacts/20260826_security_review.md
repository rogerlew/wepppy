# Security Review - Project Config Preset Snapshot

## Metadata

- **Package**: `docs/work-packages/20260804_project_config_preset_snapshot/`
- **Reviewer**: Codex
- **Date**: 2026-08-26
- **Scope reviewed**: rq-engine create boundary, snapshot files, Redis idempotency, browser-generated key
- **Commit/branch context**: `feature/project-owned-config`, starting at `95a8c4394`
- **Related artifacts**: `20260826_correctness_review.md`; `20260826_preset_snapshot_evidence.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: the change writes run-scoped configuration and introduces shared Redis state at an authentication-adjacent creation boundary.
- **Threat model assumptions**: request fields are attacker controlled; shared presets are deployment-owned; Redis is internal but records must remain non-sensitive.
- **Valid states preserved**: disabled legacy creation, anonymous CAPTCHA creation, authenticated creation, acquired/replayed/conflicting reservations, and explicit hostile-input rejection.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | durable overrides | Transport/auth fields could become configuration if filtering were implicit. | explicit transport set plus hostile tests | keep per-preset allowlist and WP00A scan | Resolved |
| SEC-02 | Medium | preset path | Unbounded preset text could permit traversal. | strict preset ID and exact registry lookup | retain registry-derived filenames | Resolved |
| SEC-03 | Medium | duplicate submission | Raw client keys or actor identity could leak through Redis key names. | SHA-256 scoped Redis key; safe record test | store only fingerprint/token/result metadata | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship dormant; do not enable before WP11 mixed-reader/Forest validation

## Surface Checks

- [x] Correctness review covers valid and hostile states.
- [x] Existing JWT/session/CAPTCHA checks complete before reservation.
- [x] Tokens, CAPTCHA responses, credentials, and config contents are excluded from artifacts and Redis records.
- [x] Overrides use exact per-preset allowlists and validators.
- [x] Preset IDs resolve only through the checked-in corpus; generated filenames are not request paths.
- [x] Temporary siblings are cleaned and final files refuse overwrite.
- [x] No queue or subprocess surface changed.
- [x] Redis reservations are actor scoped when authenticated, random-key scoped when anonymous, and expire after 86,400 seconds.
- [x] Failure handlers log contextual error IDs without request secrets and preserve canonical responses.
- [x] No new dependency, network integration, deployment secret, or enabled-by-default flag was added.

## Validation Evidence

- Focused valid/hostile and concurrency tests: passed (43 tests).
- NoDb/microservice suite: passed (3,013 tests; 30 skipped).
- WP00A scan and WP02 generated-pair reopen: passed in direct tests.
- Broad-exception enforcement and stub checks: passed.

## Residual Risk

- Real Redis failover, mixed-reader deployment, and Forest create/reopen are intentionally deferred to WP11.
- Stable capability population and endpoint authority are WP05; WP04 does not broaden legacy preset capabilities.

## Sign-off

- **Security reviewer**: Codex, 2026-08-26
- **Package owner**: Codex, 2026-08-26
