# Production image reuse and first-install review

Reviewed by the implementing Codex agent, 2026-11-18 UTC. This is a dedicated
security/correctness review record, not an independent human approval.

## Authority and scope

The operator approved PR #678, then chose a canonical-script repair for first-time
services and explicitly selected build-once/direct image transfer. Forest1 and
CILogon activation remain excluded. Changes are limited to the deployment script,
retained-image helper, tests, and operator documentation. Existing application
images remain reusable; no registry, new authentication flow, or queue is added.

## Invariants checked

Source receipts are operator-owned 0600 files with an explicitly supplied SHA-256.
The helper requires successful clean source, application equivalence, consistent
image mappings, complete target selection coverage, and locally available exact
IDs. It does not trust mutable tags, retag images, or copy a source host's approval.
The target receives its own receipt, image override, release binding, and normal
pre-cutover checks. Image IDs returned by the helper are passed through directly
rather than resolved again from mutable names.

First installs require explicit service declarations recorded in deploy options.
Inventory errors and stopped existing containers fail. Absence is rechecked before
cutover. Rollback removes only introduced containers without volume deletion, then
restores existing images. It verifies both absence and existing-service readiness;
cleanup failure does not prevent attempting existing-service recovery, and an
unverified recovery keeps the RQ fence. Shape-parser fail-closed behavior remains.

## Validation and limits

All 118 retained-candidate, deployment execution, and deployment-plan tests pass.
Shell syntax, diff whitespace, and 11 documentation lint targets pass. The initial
new success test incorrectly expected transient rollback files to survive normal
cleanup; the fixture now captures the existing activation-ledger handoff. The
corrected test and all other new cases pass. No production logic was changed to
satisfy that fixture correction.

A read-only check on wepp1 validates the actual common, renderer, soil API, and
PostGIS IDs against source receipt
`4cef0868b8a309397558842331f31a2744934ffe9c4bc50dd8d693a27497f1aa`.
Original application source is `9a50ccbf7d7ef279c1b13c41d3b72eeff77e7a39`.
Archives are distributed through the existing shared NAS under a private directory,
with transport checksums and subsequent immutable-image validation. Host-local
activation and generated-artifact checks remain pending. The previous broad CI
runtime-prerequisite limitation and deferred live SDA parity remain visible.
