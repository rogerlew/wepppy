# Schema-2 PASS calendar selection fix

**Status**: Closed 2026-10-21; implemented and validated locally

Roger authorized correction of the binary PASS date-selection defect. See
[the completed plan](prompts/completed/hbp_calendar_execplan.md) and maintain [tracker](tracker.md).
The previous observation-only investigation remains closed. This package fixes
reader selection without changing the file format, calendar policy or equations.
The ASCII `wepp_261010` century issue is separate. No release/deployment is included.

Acceptance requires multiyear date-keyed readback, unchanged hillslope payloads,
observation off/on parity, schema-1 compatibility, native tests and dual review.
Security impact: none. Parameterization changes: none.

[Validation](artifacts/validation.md) and [independent review](artifacts/correctness_review.md)
confirm exact date selection over two 44-year controlled cases and a 28-hillslope,
43-year real project. All hillslope payloads remain unchanged and candidate
observations off/on are exact. Broad native suites retain documented preexisting
limitations; no release, deployment or full-domain conservation claim.

Background: [closed routing investigation](../20261021_watershed_channel_routing_closure/package.md).
