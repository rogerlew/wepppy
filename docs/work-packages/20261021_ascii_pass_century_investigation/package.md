# ASCII PASS century investigation

Status: Closed 2026-10-21; diagnosed and reproduced, repair identified.
See [plan](prompts/completed/century_execplan.md) and [tracker](tracker.md).

The user's 200-year chemotherapeutic-scope watershed stop is caused by WEPP's
legacy century-day scheduling against Gregorian CLIGEN input. The same mismatch
shifts Julian-day hillslope output relative to calendar-dated event output;
climate EOF handling also permits stale buffered weather to be reused.

[Findings](artifacts/findings.md) retain all-hillslope date audits, original/replay
parity and exact failure diagnostics. [Robust repair](artifacts/repair-design.md)
specifies Gregorian scheduling, daily date/EOF checks, compatibility and recovery.
The user's request to identify the robust fix is documented in that design's
Required behavior and Compatibility and recovery sections.

The live project and release remain unchanged. No implementation, release or
deployment is included. Security and parameterization changes: none performed.
