# Forest fixture compatibility and regression plan

Create 100 private synthetic runs and one public synthetic run under the canonical
`/wc1/runs` root, owned by the existing dev-agent account. Use new random
`qe-boundary-` IDs, real Ron/Wepp initialization, a small parquet dataset and a
synthetic map extent. Do not mutate existing runs or account privileges. Create one disposable
ordinary account with no roles/runs for the unrelated-user browser check, then
remove that account and its ignored, bind-mounted mode-0600 credential file.

Exercise direct page and bounds collection responses, actual HttpOnly cookies,
Caddy header capacity, authorized query records, anonymous denial, and explicit
activation/origin behavior. Compare catalog/log hashes around denials. Fixture
creation changes no application schema or scientific defaults. Keep an exact
manifest for cleanup of only fixture run rows, ownership associations and run
directories. Credentials stay in existing ignored secret files or browser memory;
retained output contains status/counts only. Forest is development; this does not
authorize a production deployment or claim production equivalence by itself.


Fixture recovery: container-local `/tmp` manifests did not survive the planned
web recreation. The exact101-run manifest was reconstructed from the retained
creation log; the one disposable no-role/no-run account was removed and recreated.
The scripts now keep manifests/credentials in ignored, bind-mounted
`docker/secrets/qe-boundary-*.json`, preserving cleanup authority across recreates.
No real user account or project was selected by this recovery.


NFS cleanup observation: the first removal stopped on `.nfs` files held by live
Flask NoDb log handlers. Read-only FD inspection found fixture handles in web
workers only, none in query-engine. A graceful Gunicorn HUP releases these handles
without terminating the separate full pytest process. Cleanup is idempotent per
manifest row and clears exact fixture NoDb/WD caches and resource session markers;
logout revocation fences retain their normal lifetime.
