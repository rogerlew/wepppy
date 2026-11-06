# WEPP1 Runs table hotfix

Applied reviewed commit `a6745b94a` to `docker-weppcloud-1` on `wepp1`
on 2026-11-06 at 17:33:11 UTC, following the explicit web-container-only request.
Host working directory: `/workdir/wepppy`.

## Scope and recovery

Only these container files changed, relative to `/workdir/wepppy`:

- `wepppy/weppcloud/routes/user.py`
- `wepppy/weppcloud/templates/user/runs2.html`
- `wepppy/weppcloud/routes/usersum/weppcloud/run-ttl-deletion.md`

All three SHA-256 preimages matched the parent of the reviewed commit. A staged
Python script applied only its changed line blocks, checked target SHA-256 values,
and retained adjacent backups with suffix `.bak.20261106T173311Z` before writing.
Python and Jinja parsing passed before writes. No host checkout, image, scheduler,
RQ service, run data, or authentication changes were made.

Patch command: `wctl docker compose exec -T -u 0 weppcloud python -`, with the
staged `/tmp/wepp1-runs-table-hotfix.py` on stdin. Verified Gunicorn master PID 7
(command and parent PID 1), then sent `os.kill(7, signal.SIGHUP)` at
17:33:29 UTC. No container restart. For rollback, restore the three adjacent
backups in this same container and HUP the reverified Gunicorn master.
The source fix is already pushed; future deployments must include `a6745b94a`.

## Verification

Container ID: `7973f9ba83d08418faa122013666b7944722e08e64ed089ec7a175ba2cafdcac`.
StartedAt remained `2026-11-06T07:53:09.812694152Z`; status running and healthy
at 17:33:57 UTC. Ten new worker PIDs were 37115 through 37124.

The actual in-container sort function produced early, late, unknown, disabled
ascending, and late, early, unknown, disabled descending. The actual template
macro generated ascending after another column, descending after ascending, and
ascending after descending. Fixed layout, wrapping, colgroup and one help link
were confirmed. This was isolated function/template verification, not an
authenticated production browser session; earlier browser evidence is in
`validation.md` and `forest-readonly-smoke.log`.

`wctl docker compose exec -T weppcloud curl --max-time 15 -fsS
http://localhost:8000/health` returned `"OK"` after worker rotation.
`curl --max-time 25 -fsS https://wepp.cloud/weppcloud/health` returned `OK`.
