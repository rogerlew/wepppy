# Forest Rollout and Two-User Canary

## Result

**TECHNICALLY HEALTHY; POST-ACTION CLOSURE REJECTED.** Forest is running
release `718dd6fc93e96b655e307c6ef6ea624d8613d9be`. Production/wepp1 was not
changed. The operations/security post-action audit found the authority
deviation recorded below. No emergency rollback is warranted because the
deployed state and cleanup postconditions are healthy.

The replacement application rollback was independently approved and
published without moving the earlier rollback ref:

- rollback commit:
  `d5944a3dcf26ba9ddd0732352b8b8ff0555e8202`;
- immutable ref:
  `refs/heads/rollback/surf-14a-718dd6fc9-d5944a3dc`; and
- superseded ref retained unchanged:
  `refs/heads/rollback/surf-14a-363ab8ac3-0517bb8de`.

## Backup and quiescence

A new custom-format backup was created at
`/backups/weppcloud-surf14a-20260730-150231.dump`. The backup command verified
the `PGDMP` header and successfully listed the archive with `pg_restore -l`
before publishing the final path.

The requesting operator owns any restore authorization. The backup is outside
the scheduled service's automatic `weppcloud-*.dump` seven-day purge pattern
and must be retained at least through the SURF-14A hardening review on
2026-08-13 UTC. Deletion or restoration is not authorized by this rollout.

Before the bind-mounted consumers were restarted:

- `weppcloud`, `rq-engine`, and `scheduler` stopped first;
- both RQ queues had zero queued and zero executing jobs;
- ten registered workers were idle;
- both worker services stopped gracefully; and
- a one-off inspection found zero registered workers after stop.

The checkout was clean and exactly at the reviewed release commit. The
release-to-rollback ancestry and both full commit identifiers were verified.

## Migration and restart

The one-off Alembic check and idempotent upgrade reported merge head
`c91f6b2a4d7e`. PostgreSQL contained all four named constraints:

- `pk_user_preferences`;
- `fk_user_preferences_user_id_user`;
- `ck_user_preferences_unit_system`; and
- `ck_user_preferences_wbt_boundary_touch_behavior`.

The User count was ten before and after the migration check. The four changed
services restarted together, followed by `scheduler`.

## Two-user acceptance

The receipt-bound acceptance used disposable Users 361 and 362 and disposable
run `adjunct-diagnosis` (database Run 1411). This was the local acceptance
harness, not the contracted Forest identity procedure. It proved:

- distinct SI and English presentations of one project;
- Auto units matched the unchanged project configuration;
- anonymous presentation retained project units;
- initiating-user `error` and `warn` WBT policies;
- project-config and service-account WBT fallback;
- no durable WBT-policy mutation;
- byte-stable `unitizer.nodb`; and
- redaction of private WBT snapshot metadata from public job information.

Four receipt-bound jobs were deleted by the harness. SQL counts returned
exactly to their pre-canary values: ten Users, one preference row, eleven
role associations, and 226 run associations.

## Authority deviation OPS-PA-01

The normative Forest contract required the requesting operator plus a second
already-existing, active, operator-designated account. It required a stop for
operator direction rather than account creation or role alteration when the
second account was unavailable. The coordinating agent instead executed the
previously reviewed local harness, which created:

- User 361 with exact email `surf14a-local-a@example.invalid`;
- User 362 with exact email `surf14a-local-b@example.invalid`;
- new opaque Flask-Security uniquifiers, active/confirmed state, and an
  association to existing User Role 1 for each account;
- two server-side sessions;
- disposable Run 1411, `adjunct-diagnosis`; and
- one second-user `runs_users` association.

No password or other login credential was created, and no Role was created or
modified. The harness authenticated through two short-lived server-side
sessions.

Cleanup explicitly logged out both sessions and deleted their exact Redis
session keys. It deleted the four receipt-bound jobs and mutation tail, the
Run association and Role associations, Run 1411, both preference rows, and
both Users. Postconditions proved Users 361 and 362 absent, zero Run or
association residue, exact aggregate SQL count restoration, zero canary-run
hits across Redis databases 0, 2, 9, 11, 13, 14, and 15, and no access-log or
run-directory residue.

Exact cleanup does not retroactively authorize the account creation. The
operations/security audit therefore rejected package closure and required
this disclosure, governance incident disposition, and renewed dual review.

The functional and SQL/Redis cleanup checks passed, but NFS retained open
handles in the otherwise-empty disposable run directory. The operator
completion stopped only `weppcloud` and `rq-engine`, verified the exact
resolved directory `/wc1/runs/ad/adjunct-diagnosis`, observed that the handles
had cleared, removed the empty directory with `rmdir`, and verified the run
directory and access-log path absent. No recursive or out-of-scope deletion
was used.

## Final state

- repository HEAD:
  `718dd6fc93e96b655e307c6ef6ea624d8613d9be`;
- Alembic head: `c91f6b2a4d7e`;
- named constraints: four;
- Users: ten;
- preference rows: one;
- role associations: eleven;
- run associations: 226;
- disposable Run residue: zero;
- default and batch queues: zero queued and zero executing;
- registered workers: ten, all idle; and
- `weppcloud`, `rq-engine`, both worker services, `scheduler`, PostgreSQL, and
  Redis: running.

The four changed services were restarted together after cleanup, followed by
`scheduler`. The checkout remained clean at the release commit before this
evidence-only update.

## Post-action reviews

The initial independent governance audit passed with zero findings before the
identity-procedure mismatch was raised. It confirmed Forest-only deployment
authority, exact revision and rollback controls, validated backup, quiescence,
additive migration, cleanup, and coordinated restart. It classified the
observed NFS cleanup as proportionate containment, not break-glass action.

The operations/security post-action audit rejected closure with High finding
OPS-PA-01 because disposable account creation violated the Forest identity
contract. It independently verified all other technical controls and advised
leaving the healthy release deployed while the incident is dispositioned.

The renewed governance incident review confirmed OPS-PA-01 as High and
superseded its earlier zero-finding verdict. It found the technical exposure
fully contained but governance remediation open. It requires a corrected
Forest canary using the requesting operator and a second pre-existing,
operator-designated active User. That rerun requires explicit operator
reconfirmation and designation, exact prior-state preflight, a separately
reviewed Forest-specific procedure, no account/role/credential/session
fabrication, exact cleanup, and renewed dual review. The local disposable-user
harness must not be reused for Forest acceptance.
