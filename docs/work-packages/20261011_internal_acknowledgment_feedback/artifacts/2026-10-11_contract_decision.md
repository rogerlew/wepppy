# Contract decision: immediate internal acceptance feedback

Starting implementation: `29868fe65b13e3efa4d61cdd89551510706bb519`.
Unrelated existing worktree changes are excluded from this checkpoint.

Authority: `docs/schemas/feature-access-governance-contract.md`, especially its
user-facing surface and transport sections; shared presentation/accessibility
requirements in `docs/ui-docs/controller-contract.md`; unchanged
`docs/schemas/weppcloud-csrf-contract.md` and the synchronous message/result
response convention. No other contract's normative behavior changes.

The operator explicitly requests that clicking acceptance remove the button and
show “You have accepted this version.” Classify as a bounded presentation
enhancement: the current UI leaves the form and exposes a refresh link.
Amend the feature-access contract before implementation. Use the existing
server-rendered accepted text as the visual reference. Update current membership
acknowledgment descriptions in place so the page cannot contradict its success
message. Keep inactive/expired membership descriptions intact.

State matrix: no memberships, active memberships, inactive/expired memberships,
already accepted current version, legacy acceptance of another version, pending
request, failed/malformed response, and successful duplicate acceptance. Only
confirmed success transitions the current form; failures remain retryable.
No membership is granted, no acceptance is fabricated, and the checkbox remains
required before submission. Security impact is low and APIs are unchanged.

Regression evidence: success transitions without refresh and retains focused
status, status descriptions update selectively, repeated submission sends no
second request, failures retain controls, and PowerUser/membership forms retain
their existing behavior. Update the existing real-session browser acceptance to
assert the new state before any reload.

Two independent read-only reviews and disposition precede the standalone
checkpoint commit. Implementation remains pending until that commit exists.
