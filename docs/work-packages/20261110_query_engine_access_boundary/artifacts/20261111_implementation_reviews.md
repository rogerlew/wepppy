# Independent implementation reviews

Checkpoint ancestor: `2f9401f93`. Reviewed working implementation on 2026-11-11
UTC; candidate source manifest/commit binds the final handoff. All agents were
read-only and distinct from the implementation author.

## Correctness and UX

Reviewer `/root/contract_correctness`: local PASS. Earlier findings for Culvert
publicity, cookie/service activation, fork admission, stale tokens, Omni inputs,
relocated catalogs and repeated scans are closed. Final log permission finding
closed after preserving `0666 & umask` with `O_NOFOLLOW`. Expanded boundary/viewer
suite: 110 passed. Browser, 100-run capacity and rollout are separate gates.

## Code review

Reviewer `/root/implementation_code`: local PASS after three reproduced defects
were fixed and tested: post-admission backend errors leaked and wrote logs;
pending refresh rejected external DEM links previously skipped; parent-backed
climate/watershed `.nodir` links were rejected. Recheck errors now return503 with
byte-identical artifacts, native skip behavior is preserved, and canonical
archive links are admitted. No unresolved medium/high code finding.

## QA

Reviewer `/root/implementation_qa`: local PASS for QA-1 and QA-2. The admission
spy now wraps the actual context resolver; populated/empty denial states compare
catalog/log bytes. Current Admin/Root/PCV removal, PCV activation denial, ownerless
metadata, profile credentials, grouped policy and cookie-origin cases are covered.
QA-3 stays open until actual direct-page/collection-cookie browser evidence is
reviewed. Code quality telemetry lacks Radon and changed-file analysis; observe-only
output is retained without claiming those metrics were evaluated.

## Security

Reviewer `/root/contract_security`: local PASS at 2026-11-11 02:14:59 UTC.
Independent final targeted run: 11 passed in 13.11 seconds; retained boundary/viewer
suite: 110 passed. Closed SEC-I1 Culvert, SEC-I2 log symlinks/mode, SEC-I3 pre-read
source admission and SEC-I4 initial/repeated auth-store failures. Group-base
identity and missing matrix regressions are present. No medium/high source finding.

Subsequent bounded capacity corrections were independently approved after real
browser failures: Flask request-line cap 4094 -> 8190, and query-engine H11
incomplete-event buffer 16384 -> 131072. The reviewer checked installed Gunicorn's
bounded maximum and independently reproduced H11 fragmented-request rejection at
16384, success at131072, and431 for an oversized incomplete event. The latter is
not a total-header cap. No Caddy limit or topology change is authorized by these
reviews. Runtime browser acceptance remains required.

## Gate distinction

These dispositions approve local implementation, not production rollout or incident
closure. Failed attempts remain retained. Final focused release suite:
`focused_release.txt` — 478 passed, 2 skipped. Full suite and final environment
acceptance are tracked separately in the ExecPlan and tracker.
