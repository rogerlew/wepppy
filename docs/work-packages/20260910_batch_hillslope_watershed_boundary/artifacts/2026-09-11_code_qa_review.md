# QA/code review — batch task boundary

Reviewer: `/root/implementation_qa` (independent read-only QA), 2026-09-11.
Contract ancestors: `869ca7dcf`, `f221e7f2a`.

| Finding | Severity | Resolution |
| --- | --- | --- |
| Production worker overwrote composite identity with batch name | High | Exactly these stages defer run extraction/logging to validated task boundary; actual forking-worker regression |
| Freshness fake always returned a new instance | Medium | Real NoDb/Redis stale-cache same-signature test proves eviction and guard ordering; hostile path test |

Both findings independently confirmed resolved. Extraction and synchronous
compatibility wrapper are cohesive; the existing standalone WATAR evidence
script requires the wrapper. No unresolved high/medium QA findings.

Non-blocking feedback also addressed: concurrent Omni test now uses an explicit
multiprocessing barrier; operator/developer note documents the worker logging
exception. Review used code inspection and reported test results, not an
independent test rerun. Full-suite and Forest acceptance are separate gates.
