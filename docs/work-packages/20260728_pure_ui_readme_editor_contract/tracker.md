# Tracker - SURF-09 Pure UI README Editor Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-09 after verified SURF-08.
- [x] Ratified the concise viewer/editor/preview/save/lock/reload contract.
- [x] Complete actual-render and executable inline-client evidence.
- [x] Complete authorization, path, Markdown, concurrency, persistence, and
  reload evidence.
- [x] Repair only confirmed contract mismatches.
- [x] Complete focused and broad validation, security review, parent
  reconciliation, commit, and clean closeout.

## Findings

- The apparent duplicate `pollLock` declaration was an inspection-output
  overlap, not a source defect.
- Client/server invalidation and Ron-update shapes, revision ordering, lock
  identity, owner/readonly enforcement, confined atomic writes, request and
  render limits, and missing-file read behavior required production repairs.
- The shared CSRF interceptor remains the authoritative transport boundary and
  is exercised by the executable client evidence.

## Decisions

- Treat fixed `README.md` under `RunContext.active_root` as the only authorized
  filesystem target.
- Treat owner/admin edit capability, readonly denial, and stale-tab
  invalidation as server-enforced contracts, not presentation-only controls.
- Exercise the real inline script rather than duplicating its behavior in a
  hand-authored test client.
- Limit README templates to literal Markdown and bounded variable
  interpolation; reject operators, filters, calls, and control structures
  before evaluation.

## Validation

- Focused Python: 186 passed.
- Focused inline Jest: 2 suites, 7 tests passed.
- Full frontend: 93 suites, 687 tests passed; lint passed.
- Documentation: child, parent, ADR, exception allowlist, and project tracker
  lint passed; `git diff --check` passed.
- Broad Python: the known unrelated GridMET `_FakeUnits.degC` fixture failure
  recurred after 2,462 passes and 40 skips.
- Independent security review: passed with no unresolved high or medium
  findings.
