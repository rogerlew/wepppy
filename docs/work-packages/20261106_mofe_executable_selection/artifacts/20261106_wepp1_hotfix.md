# wepp1 hotfix evidence

Implementation `a17aa349a`, checkpoint `ffc15f1da`; pushed to origin/master.
Applied 2026-11-07 00:08 UTC; graceful reloads 00:09 UTC.
Host identity: wepp1, /home/roger. Runtime root: /workdir/wepppy.

## Applied scope and rollback

Guarded SHA-256 replacement of only `wepppy/nodb/wepp_binary_policy.py` and
`wepppy/microservices/rq_engine/schema_defaults_routes.py` in
`docker-weppcloud-1` and `docker-rq-engine-1`. Both baseline checks matched.
Backups append `.bak.20261107T000843Z` in web and
`.bak.20261107T000855Z` in rq-engine. Rollback: restore those two backups in
that container and gracefully HUP its verified supervisor (PID 7 at hotfix).
Host checkout and worker images were not synchronized by this hotfix; future
image deployment must include a17aa349a or later.

Executed staged `/tmp/mofe-apply.py` with container uid 0 solely for file
replacement; preserved source file owner/mode. Validation ran as uid 1002,
gid 130, with existing runtime secrets/mounts. No run settings changed.
Both supervisors received `kill -HUP 7`, after checking actual process command
lines; installed Uvicorn supports HUP. No host/container restart, no RQ job
worker restart, no queue mutation or model rerun.

## Evidence and limits

- Production candidate read-only preflight against bronzed-liberator passed.
- Actual WEPP Exec Jinja template rendered all five choices, with no disabled
  entries; validator accepted each. Saved selection remains wepp_261029.
- Actual rq-engine runtime schema loader reports exactly wepp_260803,
  wepp_261010, wepp_261021, wepp_261026, wepp_261029.
- rq-engine `/health` returned status ok after reload; web container healthy.
- Web and rq-engine StartedAt remain 2026-11-06 07:53:09 UTC. Default and batch
  RQ containers remain started 2026-11-06 07:53:29 UTC.
- Anonymous HTTP page checks return the expected CAPTCHA gate; no authenticated
  browser claim is made. Template and schema verification were in-container.
- No generated model output parity claim: selection fix only. Full model-output
  acceptance remains outside this operator-requested scoped hotfix.

Final file SHA-256:
- policy: ed204510cb2598afa48061e5f4b2af8aacb7c2e15ebbf28cab3bf9aaa6341a39
- schema: bbad7df66db033f00fad49e4dbcd4b9537b35164a4f7779041e34aada12ecdbc
