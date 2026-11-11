# Forest fixture compatibility and regression plan

Create 100 private synthetic runs and one public synthetic run under the canonical
`/wc1/runs` root, owned by the existing dev-agent account. Use new random
`qe-boundary-` IDs, real Ron/Wepp initialization, a small parquet dataset and a
synthetic map extent. Do not mutate existing runs or account privileges. Create one disposable
ordinary account with no roles/runs for the unrelated-user browser check, then
remove that account and its temporary mode-0600 credential file.

Exercise direct page and bounds collection responses, actual HttpOnly cookies,
Caddy header capacity, authorized query records, anonymous denial, and explicit
activation/origin behavior. Compare catalog/log hashes around denials. Fixture
creation changes no application schema or scientific defaults. Keep an exact
manifest for cleanup of only fixture run rows, ownership associations and run
directories. Credentials stay in existing ignored secret files or browser memory;
retained output contains status/counts only. Forest is development; this does not
authorize a production deployment or claim production equivalence by itself.
