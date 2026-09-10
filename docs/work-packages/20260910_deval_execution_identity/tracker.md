# DEVAL execution identity tracker

Status: active. Owner: Codex.

September 10 UTC: confirmed legacy 0600 input recurrence; recovered single job;
verified deployed writer fix and diagnosed worker/renderer UID mismatch. Started
independent review and owner-identity runtime probing.

Decision: restore existing shared-filesystem render contract; no report schema,
queue topology, authentication, or model data change. Select the trusted worker's
effective UID/GID for Docker exec. Security delta is low; no root escalation or
request-controlled identity. Legacy direct Plumber migration is outside this fix.

September 10 04:21-04:25 UTC: four-line source hotfix installed atomically with
timestamped backups in default/batch worker containers on wepp1, then wepp2.
No containers restarted; no queues cleared or model data modified. Both hosts
consume the same default/batch queues, so stopping at wepp1 would leave recurrence.

Validation: 52 focused tests passed. Real image preflight passed as 1002:130.
Fresh canary from aliquot-shoji with soils 0600 produced 13,494,027 bytes and retained
input SHA256/mode. Regeneration via deployed Soils writer preserved the DataFrame,
published 0644, and rendered with absent export (13,494,033 bytes). Actual default
queue job `deb10627-1fbd-48d7-87e3-55fcc3ab1283` finished at 04:22:21 UTC, replaced
existing output (13,494,023 bytes), and authenticated Flask route readback returned
200 with matching artifact SHA256. Correctness and QA reviews found no blockers.

The installed fix also rendered successfully on wepp2 with unchanged 0600 input,
producing 13,494,036 bytes. Evidence is in `artifacts/production-verification.md`.

Full broad validation passed: 8,194 passed, 77 skipped in 854.71 seconds, including
the disturbed simulation matrix. Documentation lint passed. The isolated canary
copy was removed after retaining reviewed evidence.

Acceptance outstanding: commit and push only this repair and fast-forward host
source checkouts. Container-layer fixes survive ordinary
restart; the canonical deployment rebuilds locally built images from the fixed
source before recreation. Do not recreate from an older image outside that workflow.
