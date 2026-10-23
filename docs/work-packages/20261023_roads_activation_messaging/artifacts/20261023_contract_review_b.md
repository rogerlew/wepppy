# Independent UX contract review

Reviewer: `/root/roads_message_review_b` (UX reviewer). Date: 2026-10-23 UTC.
Disposition: approve bounded wording revision; no blocking findings.

Reviewed the contract decision, Roads specification activation-message paragraph,
and `_sync_roads_enabled_state` in roads_bp.py before implementation. The accepted
scope preserves state checks, exception/response handling and diagnostics. The
proposed wording identifies server responsibility and gives a useful support
handoff with the project URL. It does not blame uploaded data or prescribe an
unverified retry/toggle recovery. “Request” fits uploads, reads and other guarded
operations. No new controls or user configuration are needed.

## Optional polish

UX-01 (low), Roads specification / Activation mismatch message contract:
“activation is incomplete” is clearest for the observed module-enabled/controller-
disabled case. The reverse disagreement can follow incomplete deactivation.
Prefer neutral wording for both directions:

> Roads is unavailable because of a server configuration problem. This request could not be processed. Contact support and include this project's URL.

Smallest improvement: substitute only the message. Acceptance: both mismatch
directions display the same accurate server-problem/support instruction, without
implying that changing the GeoJSON or retrying will repair the project.

## Evidence limits

This is an agent wording/contract review, not a human usability study, live UI
validation, accessibility certification or deployment evidence. Implementation
and rendered response conformance remain pending. Broader traceback presentation,
clickable support contact and activation repair are outside this bounded change.

## Post-amendment disposition

UX-01 resolved: independently reread the decision and specification; both now use
the neutral wording above exactly. Approved with no unresolved findings. The
message remains factual for either direction of disagreement, identifies the
blocked request and server responsibility, and asks for the project URL needed
for support. The amendment does not expand implementation or recovery scope.
