# Tracker - Browse listing output safety

## Status

Updated 2026-11-11 UTC: **implemented and locally validated; not deployed**.
M0-M3 complete. M4 requires separate operator authorization and production-equivalent
identity, mount, routing and template evidence. Security impact: high.

- [x] M0: canonical amendment and independent correctness/security review.
- [x] M1: eight focused red cases prove injected HTML from real entries.
- [x] M2: contextual escaping and exactly-once URL encoding implemented.
- [x] M3: 10 focused tests pass; correctness, QA and security gates pass.
- [ ] M4: separately authorized rollout and production smoke.

Base: `c040d51d09530dee7f1562c467b98d74c8d6c5a4`.
Contract checkpoint: `5e6de201b` (standalone ancestor before implementation).
Implementation reviewed and tested: `73d219877`.

## Decisions and discoveries

Canonical decision: `docs/schemas/browse-filesystem-contract.md`, section
"Filesystem names in HTML and URLs". Preserve names and current access policies;
escape text/attributes, encode filename segments, and encode queries separately.
CSP remains separate. No data/schema/default changes.

The complete decoded path must come from ASGI scope, because URL.path truncates
at decoded `#`/`?`. Missing-path breadcrumbs repeat the defect and were repaired.
Starlette TestClient double-unquotes literal percent escapes; the nested `%23`
byte readback uses installed HTTPX ASGITransport. No production fallback added.

## Evidence and handoff

See `artifacts/20261110_validation.md` for commands, red/green outcomes and
limitations, plus the failure matrix and independent correctness, QA and security
reviews. All High/Medium findings are locally closed. Optional QA suggestions
are retained without expanding this patch.

Full Python/frontend suites were explicitly not run. External action backends and
production-equivalent identities were not exercised. No deployment or incident
resolution claim is made. Continue only with separately authorized M4; preserve
unrelated existing worktree changes and the generated usersum index.
