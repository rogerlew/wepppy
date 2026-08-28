# WP12D Forest writer acceptance

**Date**: 2026-08-28

**Host**: exact host `forest`

**Candidate**: `588608f1a048500815b4e9e264bcb51ef1fd596a`

**Reader floor**: `80f4810b7be59d90a64b4771f587eb360987a820`

**Image**: unchanged `wepppy-dev` image `6ac7e7103046`

**Production action**: none; production remains reserved to parent WP12

## Accepted run and reviewed preview

Acceptance used the existing schema-v3 Builder project
`/wc1/runs/bi/biomedical-sharp` with project config `config.cfg`. Before apply,
the run files were copied to
`/tmp/wp12d-forest-acceptance.BawWKB` and compared before each attempt.

- Initial config SHA-256:
  `92ed96056d1c8c4ebe25c79577c65d262c617a53848fed56a53ae08cc7fe0948`.
- Initial manifest SHA-256:
  `0e6234e4412fab86ea94c41750205a6356b6d2b9969c6d14ae7af7c0f8d43f34`.
- Authenticated preview ID:
  `pcu1-f39627aca036351ea992717a8b014b83b8d02a4b022d857d2d810b2c8739c921`.
- Update kind: `capability_refresh` with exact acknowledgment revision
  `PC-24-capability-refresh-v1`.
- Reviewed digest transition: `92ed9605…0948` to `f41b0672…d7ca`.

## Forest findings and recovery evidence

The first accepted job, `d2db892f-7715-45e3-a955-ca86bb2246c9`, exposed a
fresh-worker circular import before task execution. The second accepted job,
`76bde759-ef34-4a27-83a8-cecf963f60b8`, proved fresh task loading and then
failed closed because browser RQ tokens with an intentionally opaque subject
lost their signed numeric `user_id` during actor sanitization. Both failures
left config and manifest byte-identical to the backups and left no active
single-flight reservation.

The bounded corrections were independently reviewed and committed as:

- `326f2138c`: lazy worker authorization import and atomic Redis Lua
  compare-delete for reservation release;
- `924813874`: preserve the signed numeric browser-token identity in queued
  worker metadata; and
- `588608f1a`: settle selected-chain provenance from the newest validated
  capability amendment while preserving the immutable creation chain.

Live Forest Redis evidence proved that an expired worker cannot delete a
replacement reservation. Correctness and security reviews report READY with
High 0, Medium 0, and Low 0.

## Successful acknowledged apply

Authenticated job `b591cd8b-18b4-4005-ae2e-8edec2d7f594` finished. Its
terminal prior/resulting digest pair exactly matched the reviewed preview:

- prior config SHA-256:
  `92ed96056d1c8c4ebe25c79577c65d262c617a53848fed56a53ae08cc7fe0948`;
- resulting config SHA-256:
  `f41b0672f9463b4af94b08a02e833093407e2719a877a1627c853a8dabc0d7ca`;
- resulting manifest SHA-256:
  `82ff3f4d4900fa2aee449ef16ad35397dbc435e76e74a274f3b70ce8979023be`;
- durable amendment sequence: `1`; and
- durable update kind: `capability_refresh`.

After candidate restart, the authenticated availability endpoint returned HTTP
200 with `available = false`, `acknowledgment_required = false`, null
`update_kind`, the resulting config digest, and the original preview ID in
`last_update`. This proves the acknowledged discontinuity is settled rather
than repeatedly offered as a manifest-only refresh.

## Reader-floor rollback proof

A detached worktree at exact revision `80f4810b7` was bound read-only in
effect as the service source for `weppcloud`, `rq-engine`, and `rq-worker`; the
project-config update flag was explicitly false. No image was rebuilt.

The reader floor reopened the refreshed project with:

- reader mode `flattened` and valid manifest;
- capability schema version `3`;
- locale profile `continental-us`;
- provider revision
  `e75ab55a4e4a086bb81714db20e5e425066a686e080802af589d035c713613f8`;
  and
- station databases `cligen-stations-legacy`, `cligen-stations-2015`, and
  `cligen-stations-ghcn`.

The refreshed config and manifest hashes were unchanged after the reader-floor
reopen. Candidate `588608f1a` was then restored with the base development
Compose file and `--no-build`; both health endpoints returned HTTP 200, the run
reopened as valid schema v3, and authenticated availability remained settled.
The temporary worktree and override were removed.

## Validation summary

- Final complete Python gate: 7,221 passed, 63 skipped, 2,740 warnings in
  12 minutes 49 seconds.
- Complete frontend gate from the exact implementation candidate: 107 suites,
  808 tests; focused update controller: 19 tests.
- Final affected provenance/auth/RQ boundary: 177 passed; combined settlement
  rerun: 1 passed.
- Frontend lint, test stubs, Vulture, changed-file broad-exception enforcement,
  RQ dependency graph, documentation lint, and diff checks: passed.

WP12D is technically accepted on `forest`. Parent WP12 handoff awaits exact
ratification of scope audit correction `PC-24/WP12D-20260828-4`, documented in
`20260828_scope_audit_correction.md`. This artifact does not authorize merge to
`master` or production deployment.
