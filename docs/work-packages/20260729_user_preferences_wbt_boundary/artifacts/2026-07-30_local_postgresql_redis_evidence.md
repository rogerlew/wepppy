# Local PostgreSQL and Redis Evidence

**Date**: 2026-07-30 UTC

**Scope**: SURF-14A remediation evidence on the local development stack.

**Forest or production mutation**: none.

## PostgreSQL migration cycle

A disposable PostgreSQL database named `surf14a_migration_fresh` was created
on the local Compose PostgreSQL service. The current application schema was
used as the representative baseline because the historical Alembic graph
starts by altering an already-existing `user` table and cannot bootstrap an
empty database.

The disposable database was stamped with both merge parents:

```text
7b3c068e7a1d
b7d9c3e2f1a4
```

`flask db upgrade` then reported:

```text
Running upgrade 7b3c068e7a1d, b7d9c3e2f1a4 -> c91f6b2a4d7e
c91f6b2a4d7e (head) (mergepoint)
```

PostgreSQL introspection returned exactly:

```text
ck_user_preferences_unit_system
ck_user_preferences_wbt_boundary_touch_behavior
fk_user_preferences_user_id_user ... ON DELETE CASCADE
pk_user_preferences
```

A valid `si`/`error` row inserted successfully. A PostgreSQL
`check_violation` handler confirmed rejection of the invalid `metric` token.
The migration's `downgrade()` and `upgrade()` bodies were then executed through
Alembic `Operations` against the disposable PostgreSQL connection. The table
was absent after downgrade and present after upgrade, while the seeded User
row remained. Deleting that User after reinserting preferences left zero
preference rows, proving the cascading foreign key.

The graph-level relative command `flask db downgrade -- -1` was also tested and
reported `Ambiguous walk` because the revision is an unlabeled two-parent
merge. This is an Alembic traversal limitation, not a DDL failure; the
PostgreSQL migration body cycle above and the unit migration cycle exercise
the reversible revision directly. Forest rollback therefore remains the
contracted nondestructive application rollback unless an explicitly reviewed
migration target is supplied.

The disposable database was dropped after the checks.

## Database-backed service and concurrency tests

The following command ran against the local PostgreSQL application database:

```text
wctl run-pytest tests/weppcloud/test_user_preferences_postgres.py -q
```

Result: **5 passed**. The tests cover named constraints, cascade behavior,
deterministic concurrent first inserts, serialized whole-record updates,
numeric-ID and exact-`fs_uniquifier` identity binding, conflicting, unknown,
missing, and inactive identity rejection, real Run ownership, exact
receipt-bound compensation, and preservation of a preexisting colliding Run.

## Real Redis/RQ lifecycle

The following command used a real `redis.StrictRedis` connection and inline
`WepppyRqWorker`:

```text
wctl run-pytest tests/rq/test_wbt_controlled_failure_integration.py -q
```

The focused controls passed. They prove deferred-registry and dependency-set
cleanup, controlled RQ failure retention without traceback or source path,
terminal failed root aggregation, canceled/non-executed abstraction, sanitized
`GET /api/jobinfo/{job_id}`, structured diagnostic correlation, and a
successful subsequent build/abstraction pair with an empty deferred registry.

No credentials, JWTs, cookies, CSRF values, or database passwords are recorded
in this artifact.
