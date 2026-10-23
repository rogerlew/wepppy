# Independent contract review A

Reviewed 2026-10-23T20:19:11.121901+00:00 by roads_message_review_a.
Disposition: approved; no high/medium findings.

Reviewed the contract decision, the Roads specification amendment under Common
API error messages, and the unchanged `_sync_roads_enabled_state` guard in
wepppy/weppcloud/routes/nodb_api/roads_bp.py. The wording accurately directs users
to a server-side activation failure and a useful project-URL support handoff.
“Request” is appropriate because the guard also serves non-upload operations.
It avoids implying that modifying GeoJSON or retrying fixes the state mismatch.

The amendment is bounded to exception text. It preserves RuntimeError, existing
response/traceback handling, authorization and state checks, and makes no state
writes. Both mismatch directions and agreeing states are explicitly covered;
missing-controller behavior remains outside this revision. Security impact is
low, with no additional diagnostic values exposed.

Validation should exercise the actual guard for both mismatch directions and
agreeing states and run existing Roads route tests. A permanent test asserting
only the new literal is unnecessary. Final review must confirm implementation
changes only the exception string after the contract checkpoint commit.

Residual limitations: the original activation defect and the existing technical
traceback details remain; this revision improves explanation rather than repairing
production or redesigning error rendering. No production deployment is authorized
or claimed by this checkpoint.

## Wording confirmation

Reviewed 2026-10-23T20:19:30.611714+00:00. Approved the updated direction-neutral
wording in the decision and specification:

> Roads is unavailable because of a server configuration problem. This request could not be processed. Contact support and include this project's URL.

This is more precise for both flag-mismatch directions and preserves the approved
scope. No new findings.
