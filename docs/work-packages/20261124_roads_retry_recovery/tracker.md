# Roads retry recovery

## Progress

Contract checkpoint 92770cf9d accepted by correctness and security reviewers. Implemented browser backoff and structured retry eligibility. Focused validation underway.

## Surprises & Discoveries

The observed local timeout consumed 20 seconds of a 25-second server budget and was terminal.

## Decision Log

Wait between completed requests in the browser so a busy public service has time to recover without occupying a worker. Keep existing clients compatible.

## Outcomes & Retrospective

Verify actual upstream count, deadline handling and real Fetch output before delivery.

## OSMnx 2.2.0 revision

Checkpoints d1a25ec45 and 84429c510 supersede the initial timing. The implementation uses a fixed 55-second cooldown and a separate run-authorized slot check. WEPPcloud Compose routes the existing run URL to Flask. The open-wepp-org HTTPRoute also forwards the run prefix to Flask, permits public egress, builds generated UI assets at initialization and configures a 120-second web worker timeout. No changes to the cluster manifests are required. Focused validation includes real HTTP slot and interpreter responses, timeout classification, advisory waits, capped retry scheduling, and upload compatibility.

Security and correctness accepted the six-minute ceiling so that an unknown-slot wait both before and after a full interpreter timeout can still recover. UI review identified a terminal message that promised an unscheduled retry. Updated it to explain that the suggested wait exceeds the remaining window. Real socket/route/publication suites passed (66 passed, one skipped). The controller regressions cover both status waits, cooldown and recovery.
