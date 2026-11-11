# Forest browser and environment acceptance

Candidate: `5009b4f64c00c048aaf98a49ad631eba12c49454`, following approved contract
checkpoint `2f9401f93`. Production source/config/test hashes are retained in
`implementation_manifest.json`; independent security review found zero mismatches.
No task production source changed after this candidate commit. The shared working
tree retains pre-existing unrelated user edits (including management metadata and
controller-contract work); they were neither staged nor reverted. The manifest
binds the task-specific production source, configuration and tests.

## Environment

- Existing forest dev Compose stack and actual Tailscale HTTPS/Caddy ingress:
  `https://forest.tail305ec9.ts.net`.
- Current PostgreSQL account/ownership and Redis session/revocation stores; real
  password/CAP login, browser cookies and native parquet/catalog execution.
- Query-engine and Flask: UID 1000, GID/supplementary group 993, umask 0022, verified
  independently from running process status. Source and `/wc1` mount selections
  are retained in `forest_rendered_candidate.json`.
- Query-engine selected `H11Protocol`, incomplete-event buffer 131072; Flask
  Gunicorn request-line cap 8190. Running command readbacks are retained separately.
- Caddy configuration validation passed. No Caddy/header/body limit, identity,
  ownership policy, feature membership or service topology was changed.
- Created 101 synthetic runs: 100 private, one public, owned by the existing
  dev-agent account. A disposable ordinary account held no roles or runs.
  Cleanup evidence is separate; no existing project was modified.

## Browser results

`forest_browser_candidate.txt` and its reproducible `forest_browser.cjs` retain
assertions and results, including the actual catalog/log SHA256 manifest.

| Check | Result |
| --- | --- |
| Password/CAP login and direct Flask run page | Passed; 200 page and one Secure/HttpOnly/Lax query-prefix cookie |
| Token in JavaScript-readable cookie or HTML | Absent |
| Owner private query |200; exact synthetic records 3 and 7 |
| Anonymous private/public query |401  / 200 with exact public records |
| Unrelated account page / absent-cookie query | Existing Flask 404 concealment  / 401; no query cookie minted |
| Unrelated current-account bearer schema |403 through real account state |
| Denied requests and method/origin rejections | Existing catalog/log SHA256 manifest unchanged |
| GET activation / hostile Origin POST |405  / 403 |
| Same-origin cookie POST activation |200 and real catalog publication |
| Single 100-run collection page |200 ; 100 query cookies retained |
| Cookie transport through Caddy |63600 bytes; final private query200 with exact records |
| URL above 8190 bytes |400; configured bound retained |
| Logout with retained query cookies | Subsequent private query 401 |

## Capacity corrections and retained failures

The initial 100-run URL failed at 5537 bytes against Gunicorn's 4094-byte default.
Two 50-run pages then proved browser retention but the 63600-byte cookie request
failed before application admission against H11's 16384-byte incomplete-event
buffer. Both failures are retained. Independent security review approved the
smallest bounded server-setting corrections without changing cookie transport or
Caddy. It independently reproduced fragmented-request rejection/acceptance and
rejection of an incomplete event above the configured limit. The H11 setting is not a universal
header-size cap; see the canonical HTTP operations guide for cost and rollback.

## Independent disposition and remaining gates

QA closed QA-1/QA-2/QA-3 and the single 100-run workflow after reading the final
browser assertions and runtime settings. Security accepted the bounded candidate
and forest workflow, verified source hashes and found no JWT-shaped token literals
in retained artifacts. No medium/high source or forest-workflow finding remains.

The full candidate Python suite finished with 13,362 passed, 435 skipped and
one pre-existing usersum template assertion. `full_suite_unrelated_failure.txt`
proves both implicated files are unchanged from pre-work `b3786ae7e`. The earlier evolving-tree run was intentionally interrupted after 4013
passed / 126 skipped and is not a full-pass receipt. Focused release tests passed 478
with 2 skipped; frontend 124 suites / 1069 tests, stubs and exception enforcement passed.

This is forest acceptance, not a wepp1 deployment receipt or SEC-F1 incident
closure. Production rollout still requires explicit authorization, host-specific
parity/controlled acceptance and the observation/recurrence disposition specified
in the active ExecPlan.


## Cleanup readback

`forest_fixture_cleanup_retry.txt`, `forest_unrelated_cleanup.txt` and
`forest_cleanup_readback.txt` verify removal of all 101 synthetic run rows,
ownership associations and directories, the disposable account and temporary
credential/manifest files. Exact fixture NoDb/WD caches and resource session
markers were cleared. Readback counts are all zero. The initial NFS-handle cleanup
failure and bounded recovery remain retained in the fixture plan and transcripts.


## Narrow follow-up acceptance

Follow-up commit `d033a33df` preserves collection rendering on query denial and
closes same-named grouped-resource bearer binding. `followup_browser_final.txt`
passes both cases plus ordinary private query records and logout revocation.
`cookie_denial_cleanup.txt` and `followup_cleanup_readback.txt` retain removal
and zero-count verification for the two additional disposable fixtures/manifest.
