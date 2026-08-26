# Project Config Builder UI (WP07)

**Status**: Complete (2026-08-26)
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `ddac050c3`
**Security impact**: high; dedicated review required

## Objective

Add an authenticated, optional, one-page Config Builder that consumes WP06's
server-described registry, validates complete selections, presents the exact
server-resolved review, and creates a fixed-token `/config/` project without
changing or replacing the Interfaces workflow.

## Compatibility and Regression Plan

The change is additive: `/interfaces/` and every existing named-config creation
form retain their routes, config IDs, CAPTCHA behavior, and copy. The new page
submits only registered stable IDs, an opaque registry revision, and a generated
idempotency key through the existing same-origin browser-to-rq-engine token
bridge. It never accepts a config token, filename, path, or raw configuration
key. Invalidated dependent values are removed visibly before the next payload.
Successful creation navigates to the server-provided `/config/` location;
errors preserve valid selections and cannot mark a project ready.

## Owned Requirements

PC-13: N-038 through N-046, N-048, N-051, R-036, R-042, R-043, R-045,
R-047, and R-048.

## Success Criteria

- [x] Config Builder is a distinct authenticated path and Interfaces is unchanged.
- [x] One-page dependent controls submit stable server-described IDs only.
- [x] Ordinary and privileged cell-size experiences match the server role result.
- [x] Validation errors, stale schema, review, and status are accessible and actionable.
- [x] Duplicate submission is blocked and success navigates to the fixed `/config/` project.
- [x] Frontend, template, route, accessibility, documentation, and full-suite gates pass.

## Rollout

The WP06 writer flag remains strict and default-off. The page can describe and
validate while creation reports its canonical disabled state. WP11 owns Forest
acceptance and WP12 owns production enablement.
