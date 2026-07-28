# GOV-00A bounded web-origin guard remediation decision

**Milestone**: GOV-00A-M1D

**Remediation**: REM-04

**Dated package**:
`docs/work-packages/20260727_web_origin_guard_hardening/`

## Decision

Register the operator-authorized browser-origin and diagnostics-boundary defects
as a bounded cross-owner remediation. REM-04 borrows only the existing browser
session mutation, shared browser transport, and diagnostics report boundaries
from SURF-13, SHR-02, and SHR-04A.

The exact accepted behavior is one same-origin decision contract for the three
existing guards, deletion of only configured WEPPcloud session and remember
cookies during browser-state reset, and an allowlist-built copied diagnostics
report that excludes raw probe evidence.

## Authority

The WEPPcloud operator requested execution of this package on 2026-07-27,
requested a governance-compliant executable scaffold on 2026-07-28, and then
explicitly requested execution of that revised package. This authorizes the
finite behavior, dual-agent checkpoint and final reviews, and standalone
checkpoint commit described by the active ExecPlan.

GOV-00A-M1D becomes effective only when the REM-04 contract checkpoint, this
registration, both independent reviews, and their disposition are committed as
a standalone ancestor.

## Exclusions

REM-04 does not authorize new guarded endpoints, authentication or role policy,
OAuth behavior, Caddy configuration, deployment, queue wiring, project data
schemas, model parameterization, diagnostics card presentation, or unrelated UI
work. It does not advance any borrowed owner.

## Security and Compatibility

Security impact is `high`. Conflicting hosts and explicit public ports reject;
raw forwarded headers do not create allowed origins; CSRF remains mandatory
where already enforced. A same-origin Fetch Metadata signal bridges only the
internal HTTP versus public HTTPS scheme difference for the same authoritative
host and effective public port. Missing all origin signals rejects on every
guard.

The query-engine restoration accepts the previously failing upstream-TLS
browser upload. Non-browser clients without origin evidence must not use the
three guarded browser endpoints.
