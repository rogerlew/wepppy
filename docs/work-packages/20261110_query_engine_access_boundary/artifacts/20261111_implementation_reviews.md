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


## Candidate and browser follow-up

Implementation candidate committed as `5009b4f64`; source/config/test SHA256
manifest is `implementation_manifest.json`. QA independently reviewed
`forest_browser_capacity_pass.txt` and the browser assertions: QA-3 is closed
for direct-page and collection minting. Two50-run pages prove100-cookie retention
and successful63600-byte request transport through Caddy; they do not yet prove
a single100-run collection URL. That last capacity step awaits activating the
8190 request-line setting after the full Python process exits.

Candidate code-quality report now analyzes19 changed files (the tool compares
commits, so earlier staged runs had no changed-file analysis). New source modules
are green for size/function length. Existing run_0 remains red with only two
added call-site lines; preserving that structure avoids an unrelated refactor.
Other existing yellow files grew modestly for admission/rechecks. Radon remains
unavailable, so cyclomatic-complexity metrics are unknown. This is observe-only.


## Final forest review

QA and security independently accepted `forest_browser_candidate.txt` for
`5009b4f64`: the single 100-run collection page, 100-cookie request, oversized
request-line rejection and logout revocation all passed. QA-3 and the remaining
single-page capacity step are closed. Security rechecked the manifest (zero
mismatches), found no JWT-shaped artifact tokens, and read both running services
as UID 1000, GID/group 993, umask 0022. Full Python sanity remains a separate gate.
Production deployment/incident closure are not approved by these reviews.


## CID-5 reopened by final consumer check

Reviewer `/root/implementation_code` confirmed a medium compatibility finding:
collection admission accepts Admin/Root without requiring private Batch feature
membership, while query admission remains group-only. The resulting canonical
`rq_auth.AuthError` was not caught by the query-cookie helper, turning the admitted
page into500. This is a static policy distinction, not a hypothetical race.
`cookie_denial_red.txt` retains the failing collection regression. Closure requires
narrow401/403 omission, unchanged query enforcement, and regression/browser evidence.
All earlier source and forest findings remain closed; CID-5 is tracked separately.


## Final narrow follow-up closure

CID-5 and CID-6 are closed in `d033a33df`. CID-5 preserves an admitted collection
page when query-only authorization denies401/403, with no credential;503 remains
explicit. CID-6 removes untyped Batch aliases and restricts bare Culvert UUIDs
to the existing signed service-group provenance. The independent security reviewer
reproduced the original session-as-bearer scope collision using real JWT, Parquet
and routing; current group membership was still required.

Security final PASS covers `5009b4f64` plus these exact changes. Evidence:
`focused_followup.txt`487 passed/2 skipped; `culvert_human_followup.txt`1 passed
with current membership removal and unchanged artifact bytes;
`followup_browser_final.txt` passed ordinary private query, collection admission
without a query grant, bearer resource-binding rejection and logout. No unresolved
medium/high security finding remains. Source hashes are retained in
`final_source_manifest.json`. Broad evidence is explicitly13,362 passed/435 skipped/
one pre-existing usersum assertion, proven unchanged by
`full_suite_unrelated_failure.txt`; it is not a full-suite pass on the follow-up.

Code reviewer `/root/implementation_code` independently closed CID-5/CID-6 at
`d033a33df` after reading source and retained focused/browser evidence; no
remaining finding in its scope. Final documentation lint passed14 package files
and the canonical HTTP contract with zero errors/warnings. Exception enforcement
passed; follow-up cleanup readback reports zero fixture rows/directories/manifests.
