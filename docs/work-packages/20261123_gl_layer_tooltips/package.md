# GL dashboard layer tooltips

Closed locally on 2026-11-23 UTC. Implementation commit `abf0dca00`.
Dashboard maintainers need to change a measure's hover label without tracing a 246-line dispatcher. Extract feature lookups and tooltip formatting behind the existing map layer factory. Acceptance requires exact string and precedence parity through the factory and a complexity score below the repository red band across the changed modules.

Security impact is none. The complexity budget covers browser modules and regression tests. Local integration is the delivery boundary. See the [tracker](tracker.md).
