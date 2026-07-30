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

The graph-level relative command `flask db downgrade -- -1` reported
`Ambiguous walk` because `-1` does not identify a branch for the two-parent
merge. A second disposable database, `surf14a_graph_cycle_0735`, then used the
reviewed explicit parent target and completed the supported graph cycle:

```text
flask db upgrade
  7b3c068e7a1d, b7d9c3e2f1a4 -> c91f6b2a4d7e

flask db downgrade 7b3c068e7a1d
  c91f6b2a4d7e -> 7b3c068e7a1d, b7d9c3e2f1a4

flask db current
  b7d9c3e2f1a4
  7b3c068e7a1d

flask db upgrade
  7b3c068e7a1d, b7d9c3e2f1a4 -> c91f6b2a4d7e
```

The database was newly created, initialized with the representative
application schema, had `user_preferences` removed, and recorded both actual
parent revisions before the first graph upgrade. After re-upgrade, one
application-context check returned:

```json
{
  "constraints": [
    "ck_user_preferences_unit_system",
    "ck_user_preferences_wbt_boundary_touch_behavior",
    "fk_user_preferences_user_id_user",
    "pk_user_preferences"
  ],
  "missing": ["config", "config"],
  "saved": ["si", "error"],
  "rows_after_user_delete": 0
}
```

The redacted reproducible command sequence, run from
`/home/workdir/wepppy`, was:

```text
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres createdb -U wepppy surf14a_graph_cycle_0735

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0735 weppcloud bash -lc '
    cd /workdir/wepppy
    PYTHONPATH=/workdir/wepppy /opt/venv/bin/python -c "
from sqlalchemy import text
from wepppy.weppcloud.app import app, db
app.app_context().push()
db.create_all()
db.session.execute(text(\"DROP TABLE user_preferences\"))
db.session.execute(text(\"CREATE TABLE alembic_version
  (version_num VARCHAR(32) NOT NULL PRIMARY KEY)\"))
db.session.execute(
  text(\"INSERT INTO alembic_version(version_num) VALUES (:a), (:b)\"),
  {\"a\": \"7b3c068e7a1d\", \"b\": \"b7d9c3e2f1a4\"},
)
db.session.commit()
"'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0735 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud \
  bash -lc 'cd /workdir/wepppy && /opt/venv/bin/flask db upgrade'
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0735 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud \
  bash -lc 'cd /workdir/wepppy && /opt/venv/bin/flask db downgrade 7b3c068e7a1d'
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0735 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud \
  bash -lc 'cd /workdir/wepppy && /opt/venv/bin/flask db current'
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0735 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud \
  bash -lc 'cd /workdir/wepppy && /opt/venv/bin/flask db upgrade'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres dropdb -U wepppy surf14a_graph_cycle_0735
```

Every command exited zero. The application-context assertion between the
second upgrade and `dropdb` used SQLAlchemy inspection plus the production
`load_user_preferences()` and `save_user_preferences()` functions to produce
the exact JSON above. `surf14a_migration_fresh` was the earlier direct-body
fixture and was also dropped; `surf14a_graph_cycle_0735` is the later
graph-level fixture documented here.

The historical
repository base still cannot bootstrap a literally empty database because its
first revision alters an application-owned `user` table; the amended contract
therefore names this new representative application schema as the supported
fresh test baseline. Forest rollback remains the contracted nondestructive
application rollback unless a later destructive downgrade receives separate
approval.

The disposable database was dropped after the checks.

### Fully reproducible graph-cycle rerun

Reviewer feedback correctly noted that the earlier transcript narrated its
application assertions without retaining the literal assertion command. A new
disposable database, `surf14a_graph_cycle_0815`, reran the complete cycle. The
exact commands, from `/home/workdir/wepppy`, were:

```text
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres createdb -U wepppy surf14a_graph_cycle_0815

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0815 \
  -e PYTHONPATH=/workdir/wepppy weppcloud /opt/venv/bin/python -c \
  'from sqlalchemy import text; from wepppy.weppcloud.app import app, db; app.app_context().push(); db.create_all(); db.session.execute(text("DROP TABLE user_preferences")); db.session.execute(text("DROP TABLE IF EXISTS alembic_version")); db.session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")); db.session.execute(text("INSERT INTO alembic_version(version_num) VALUES (:a), (:b)"), {"a":"7b3c068e7a1d","b":"b7d9c3e2f1a4"}); db.session.commit()'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0815 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db upgrade

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0815 \
  -e PYTHONPATH=/workdir/wepppy weppcloud /opt/venv/bin/python -c \
  'import json; from sqlalchemy import inspect; from wepppy.weppcloud.app import app, db, User; from wepppy.weppcloud.user_preferences import load_user_preferences, save_user_preferences; app.app_context().push(); u=User(email="surf14a-graph-0815@example.invalid", active=True, fs_uniquifier="surf14a-graph-0815", password=""); db.session.add(u); db.session.commit(); uid=int(u.id); missing=load_user_preferences(uid); saved=save_user_preferences(uid, "si", "error"); names=sorted(c["name"] for c in inspect(db.engine).get_check_constraints("user_preferences"))+sorted(c["name"] for c in inspect(db.engine).get_foreign_keys("user_preferences"))+sorted(c["name"] for c in inspect(db.engine).get_pk_constraint("user_preferences") and [inspect(db.engine).get_pk_constraint("user_preferences")]); print(json.dumps({"user_id":uid,"constraints":sorted(names),"missing":[missing.unit_system,missing.wbt_boundary_touch_behavior],"saved":[saved.unit_system,saved.wbt_boundary_touch_behavior]}))'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0815 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud \
  flask db downgrade 7b3c068e7a1d
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0815 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db current
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0815 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db upgrade

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0815 \
  -e PYTHONPATH=/workdir/wepppy weppcloud /opt/venv/bin/python -c \
  'import json; from sqlalchemy import func, inspect, select; from wepppy.weppcloud.app import app, db, User, UserPreferences; from wepppy.weppcloud.user_preferences import load_user_preferences, save_user_preferences; app.app_context().push(); u=db.session.execute(select(User).where(User.email=="surf14a-graph-0815@example.invalid")).scalar_one(); user_count_before=int(db.session.scalar(select(func.count()).select_from(User))); missing=load_user_preferences(int(u.id)); saved=save_user_preferences(int(u.id), "english", "warn"); names=sorted(c["name"] for c in inspect(db.engine).get_check_constraints("user_preferences"))+sorted(c["name"] for c in inspect(db.engine).get_foreign_keys("user_preferences"))+sorted(c["name"] for c in inspect(db.engine).get_pk_constraint("user_preferences") and [inspect(db.engine).get_pk_constraint("user_preferences")]); db.session.delete(u); db.session.commit(); prefs_after=int(db.session.scalar(select(func.count()).select_from(UserPreferences))); print(json.dumps({"constraints":sorted(names),"user_preserved":user_count_before==1,"missing_after_graph_cycle":[missing.unit_system,missing.wbt_boundary_touch_behavior],"saved_after_graph_cycle":[saved.unit_system,saved.wbt_boundary_touch_behavior],"rows_after_user_delete":prefs_after}))'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres dropdb -U wepppy surf14a_graph_cycle_0815
```

Every command exited zero. The first assertion returned the four exact
constraints, missing `config/config`, and saved `si/error`. The post-cycle
assertion returned:

```json
{
  "constraints": [
    "ck_user_preferences_unit_system",
    "ck_user_preferences_wbt_boundary_touch_behavior",
    "fk_user_preferences_user_id_user",
    "pk_user_preferences"
  ],
  "user_preserved": true,
  "missing_after_graph_cycle": ["config", "config"],
  "saved_after_graph_cycle": ["english", "warn"],
  "rows_after_user_delete": 0
}
```

The final `dropdb` succeeded. No application database, Forest database, or
production database was changed.

### Retained single-fixture graph transition transcript

The disposable `surf14a_graph_cycle_0910` rerun used these exact commands:

```text
docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres createdb -U wepppy surf14a_graph_cycle_0910

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e PYTHONPATH=/workdir/wepppy weppcloud /opt/venv/bin/python -c \
  'from sqlalchemy import text; from wepppy.weppcloud.app import app, db; app.app_context().push(); db.create_all(); db.session.execute(text("DROP TABLE user_preferences")); db.session.execute(text("DROP TABLE IF EXISTS alembic_version")); db.session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")); db.session.execute(text("INSERT INTO alembic_version(version_num) VALUES (:a), (:b)"), {"a":"7b3c068e7a1d","b":"b7d9c3e2f1a4"}); db.session.commit()'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres psql -U wepppy -d surf14a_graph_cycle_0910 -Atc \
  'SELECT version_num FROM alembic_version ORDER BY version_num;'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db upgrade

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db current

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e PYTHONPATH=/workdir/wepppy weppcloud /opt/venv/bin/python -c \
  'import json; from sqlalchemy import inspect; from wepppy.weppcloud.app import app, db, User; from wepppy.weppcloud.user_preferences import load_user_preferences, save_user_preferences; app.app_context().push(); u=User(email="surf14a-graph-0910@example.invalid", active=True, fs_uniquifier="surf14a-graph-0910", password=""); db.session.add(u); db.session.commit(); uid=int(u.id); missing=load_user_preferences(uid); saved=save_user_preferences(uid, "si", "error"); i=inspect(db.engine); names=sorted([c["name"] for c in i.get_check_constraints("user_preferences")]+[c["name"] for c in i.get_foreign_keys("user_preferences")]+[i.get_pk_constraint("user_preferences")["name"]]); print(json.dumps({"user_id":uid,"constraints":names,"missing":[missing.unit_system,missing.wbt_boundary_touch_behavior],"saved":[saved.unit_system,saved.wbt_boundary_touch_behavior]}))'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud \
  flask db downgrade 7b3c068e7a1d

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres psql -U wepppy -d surf14a_graph_cycle_0910 -Atc \
  'SELECT version_num FROM alembic_version ORDER BY version_num;'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db upgrade

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e FLASK_APP=wepppy.weppcloud.app:app weppcloud flask db current

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  -e POSTGRES_DB=surf14a_graph_cycle_0910 \
  -e PYTHONPATH=/workdir/wepppy weppcloud /opt/venv/bin/python -c \
  'import json; from sqlalchemy import func, inspect, select; from wepppy.weppcloud.app import app, db, User, UserPreferences; from wepppy.weppcloud.user_preferences import load_user_preferences, save_user_preferences; app.app_context().push(); u=db.session.execute(select(User).where(User.email=="surf14a-graph-0910@example.invalid")).scalar_one(); user_count_before=int(db.session.scalar(select(func.count()).select_from(User))); missing=load_user_preferences(int(u.id)); saved=save_user_preferences(int(u.id), "english", "warn"); i=inspect(db.engine); names=sorted([c["name"] for c in i.get_check_constraints("user_preferences")]+[c["name"] for c in i.get_foreign_keys("user_preferences")]+[i.get_pk_constraint("user_preferences")["name"]]); db.session.delete(u); db.session.commit(); prefs_after=int(db.session.scalar(select(func.count()).select_from(UserPreferences))); print(json.dumps({"constraints":names,"user_preserved":user_count_before==1,"missing_after_graph_cycle":[missing.unit_system,missing.wbt_boundary_touch_behavior],"saved_after_graph_cycle":[saved.unit_system,saved.wbt_boundary_touch_behavior],"rows_after_user_delete":prefs_after}))'

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres dropdb -U wepppy surf14a_graph_cycle_0910

docker compose -p docker -f docker/docker-compose.dev.yml exec -T \
  postgres psql -U wepppy -d postgres -Atc \
  "SELECT count(*) FROM pg_database WHERE datname='surf14a_graph_cycle_0910';"
```

The complete transition and assertion output from that one fixture was:

```text
createdb surf14a_graph_cycle_0910
exit=0

representative schema + both parent rows initialized
exit=0

SELECT version_num FROM alembic_version ORDER BY version_num;
7b3c068e7a1d
b7d9c3e2f1a4
exit=0

flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade 7b3c068e7a1d,
b7d9c3e2f1a4 -> c91f6b2a4d7e, Add typed account preferences and merge
the current migration heads.
exit=0

flask db current
c91f6b2a4d7e (head) (mergepoint)
exit=0

{"user_id": 1, "constraints":
["ck_user_preferences_unit_system",
"ck_user_preferences_wbt_boundary_touch_behavior",
"fk_user_preferences_user_id_user", "pk_user_preferences"],
"missing": ["config", "config"], "saved": ["si", "error"]}
exit=0

flask db downgrade 7b3c068e7a1d
INFO  [alembic.runtime.migration] Running downgrade c91f6b2a4d7e ->
7b3c068e7a1d, b7d9c3e2f1a4, Add typed account preferences and merge
the current migration heads.
exit=0

SELECT version_num FROM alembic_version ORDER BY version_num;
7b3c068e7a1d
b7d9c3e2f1a4
exit=0

flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade 7b3c068e7a1d,
b7d9c3e2f1a4 -> c91f6b2a4d7e, Add typed account preferences and merge
the current migration heads.
exit=0

flask db current
c91f6b2a4d7e (head) (mergepoint)
exit=0

{"constraints": ["ck_user_preferences_unit_system",
"ck_user_preferences_wbt_boundary_touch_behavior",
"fk_user_preferences_user_id_user", "pk_user_preferences"],
"user_preserved": true,
"missing_after_graph_cycle": ["config", "config"],
"saved_after_graph_cycle": ["english", "warn"],
"rows_after_user_delete": 0}
exit=0

dropdb surf14a_graph_cycle_0910
exit=0

SELECT count(*) FROM pg_database
WHERE datname='surf14a_graph_cycle_0910';
0
exit=0
```

The PostgreSQL implementation/context lines appeared before each Alembic
transition and current-head result and reported transactional DDL. Every
command above was executed through the same local Compose project and database
environment shown in the literal command block. A preliminary disposable
`surf14a_graph_cycle_0900` attempt was explicitly dropped after its multi-head
`flask db current` nonzero status interrupted shell sequencing; it produced no
retained application state. Neither rerun touched the application database,
Forest, or production.

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
