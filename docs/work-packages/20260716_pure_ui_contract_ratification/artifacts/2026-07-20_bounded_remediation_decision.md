# GOV-00A Bounded Cross-Owner Remediation Decision

**Milestone**: GOV-00A-M1A
**Status**: Accepted; dual review complete
**Decision time**: 2026-07-20 21:23 UTC
**Starting revision**: `a0c21b8727ca6b10c9dc1946087473d793a3554b`

## Decision

GOV-00A adds a narrow pre-GOV-01 path for a concrete production defect that
spans registered future owners whose normal dependency order is not complete.
The path requires a stable remediation id, exact borrowed boundaries and
exclusions, the highest borrowed-owner security triage, operator approval,
contract and authoritative-metadata amendments, two independent reviews, a
standalone ancestor commit, focused implementation evidence, and later
inheritance by each borrowed owner's audit.

GOV-00A-M1A is independently closable when this decision, the standard and
register amendments, two reviews, and their disposition are committed as one
standalone ancestor. Its closure authorizes only REM-01 and leaves all other
GOV-00A deliverables open.

The path does not execute, verify, or advance a borrowed owner. It cannot waive
dependencies for unrelated work and cannot silently add queue, data-schema,
parameterization, upload, file, or model-execution changes.

## First Registration

REM-01 registers
`docs/work-packages/20260720_omni_mod_state_sync/` and borrows the smallest
relevant portions of DOM-02, DOM-25A, and DOM-25B. Its exact boundary is feature
menu availability, checkbox/reason rendering, persisted mod enable/disable
guards, run-page/preflight active visibility, shared Omni controller remount,
focused regression tests, and the generated controller bundle.

## Rationale

Requiring the full multi-year dependency spine before correcting a finite
production state mismatch would leave an operator-confirmed defect in place.
Allowing an unregistered ad hoc package would undermine contract-first
governance. The bounded path preserves authority and review ordering while
making no claim that the future domain audits are complete.

## Operator Authorization

On 2026-07-20 the operator explicitly directed Codex to expand scope through
GOV-00A, ratify the mechanism, and complete REM-01. The same direction defines
the unauthorized Omni Contrasts menu text as `Not Authorized`.

## Security and Compatibility

REM-01 inherits `high` security impact because it touches role-gated dynamic
loading and persisted Project mod mutation. Existing Dev/Root enable and
dynamic-load authorization remains unchanged. The menu becomes discoverable to
all users, but disabled visibility grants no route or state authority.

The mechanism is additive to the register. Existing package ids, dependency
edges, evidence grades, and execution states remain unchanged.

## Required Review Evidence

Two independent reviewers must confirm scope containment, finite authority,
security inheritance, compatibility, negative authorization evidence, and the
standalone ancestor requirement. Their raw findings and primary disposition
must be committed with this decision before REM-01 implementation begins.

## Review Outcome

Both independent reviewers approved the corrected standalone ancestor after
disposition. No high- or medium-severity findings remain. Approval is limited
to GOV-00A-M1A and REM-01; all other GOV-00A deliverables remain open.
