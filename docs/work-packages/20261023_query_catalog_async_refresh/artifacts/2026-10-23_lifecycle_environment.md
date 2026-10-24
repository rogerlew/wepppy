# Authenticated lifecycle environment evidence

Completed 2026-10-23 20:48 UTC on the local forest stack. Scope was the isolated
private project `/wc1/runs/qc/qcat-archive-20261023`. No production or Mill Creek
model clone writes, deployments, service restarts, or account changes occurred.

## Identity, storage and authorization

The driver ran with `wctl docker compose exec -T weppcloud python -` as uid 1000,
gid 993, supplementary group 993. The actual running browse container reports
the same identity and umask 0022. Both access `/wc1` on NFS4 from `10.0.0.2:/`.
The restored Parquet ownership/mode read back from the browse container was
`1000:993 640`.

HTTP requests used the running `http://browse:9009` service, not a TestClient or
mocked authorization function. A short-lived, run-scoped session JWT cookie was
issued with the repository token API and paired with a real Redis session marker.
Only the User role was present. The marker was deleted in cleanup; no token or
credential was printed or retained. This validates the browser session cookie
and live route authorization boundary, but does not exercise the login page or
an interactive browser renderer.

## Results

- Anonymous private-project browse returned HTTP 302.
- Session-authenticated `browse/_query_engine/refresh/` returned HTTP 200 and
  exposed both the requests and attempts directories.
- Downloads of a pending receipt and a published attempt returned HTTP 200,
  with response bytes matching the filesystem files exactly; both had mode 0640.
- Actual `archive_rq` created a ZIP containing the receipt, attempt and Parquet
  with exact original bytes and Unix modes.
- After deliberately changing the isolated Parquet, actual `restore_archive_rq`
  restored those bytes and modes. The project incarnation changed.
- The restored pending receipt moved to visible `attempts/retired-*/` history,
  retaining its bytes/mode. Its authenticated download returned HTTP 200 and
  exact restored bytes. The published attempt remained intact.

The [machine-readable result](lifecycle_environment_result.json) retains exact
member paths, hashes and status codes. The archive and run-local result remain
under the isolated scope for inspection. Driver: `/tmp/qcat_lifecycle_environment.py`.

## Limits

This is real local service identity, mount, HTTP authorization and archive/restore
evidence. Production `wepp1` uses uid 1002/gid 130 and a different storage server;
this probe does not close the separate production-equivalent deployment gate.
The running browse service was not restarted: visibility uses the existing live
browse implementation, while archive/restore imported the current candidate code
in a separate process under the service identity. No deployment is implied.

## Fixture privacy cleanup

The environment review identified that a false `Ron.public` flag alone does not
make an unowned run private to Flask routes. Under the parent's explicit local
cleanup authorization, the isolated archive run was associated with the existing
active `dev-agent@example.com` through `user_datastore.create_run`. The process
first verified SQLAlchemy's database host `postgres` and database `wepppy`; it
made no user, password or role changes. Live anonymous Flask project access was
then checked separately. The accompanying `lifecycle_privacy_result.json` retains
the verified response and database scope. Driver: `/tmp/qcat_archive_privacy.py`.
