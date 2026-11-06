import json, os, sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from wepppy.weppcloud.configuration import _build_postgres_uri

mode = sys.argv[1]
assert mode in {'rehearsal', 'production'}
expected = 'cutover_rehearsal_20261106' if mode == 'rehearsal' else 'wepppy'
original = make_url(os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or _build_postgres_uri())
assert original.database == 'wepppy'
assert original.host == 'postgres'
url = original.set(database=expected)
os.environ['SQLALCHEMY_DATABASE_URI'] = url.render_as_string(hide_password=False)
os.environ['DATABASE_URL'] = os.environ['SQLALCHEMY_DATABASE_URI']
engine = create_engine(url)
with engine.connect() as conn:
    database, server = conn.execute(text('SELECT current_database(), inet_server_addr()::text')).one()
    assert database == expected and server
from wepppy.weppcloud.app import app, db
from flask_migrate import upgrade
with app.app_context():
    effective = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
    assert effective.database == expected and effective.host == 'postgres'
    with db.engine.connect() as conn:
        actual = conn.execute(text('SELECT current_database(), inet_server_addr()::text')).one()
        assert tuple(actual) == (database, server)
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'e7a1c9d204bf'
        assert conn.execute(text("SELECT to_regclass('public.notification')")).scalar_one() is None
        tables = ['user', 'run', 'runs_users', 'feature_access_membership']
        before = {name: conn.execute(text('SELECT count(*) FROM "' + name + '"')).scalar_one() for name in tables}
    upgrade(directory='/cutover/migrations', revision='f6b8d27a901c')
    with db.engine.connect() as conn:
        after = {name: conn.execute(text('SELECT count(*) FROM "' + name + '"')).scalar_one() for name in tables}
        assert before == after
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'f6b8d27a901c'
        assert conn.execute(text('SELECT count(*) FROM notification')).scalar_one() == 0
        assert conn.execute(text('SELECT count(*) FROM notification_recipient')).scalar_one() == 0
    print(json.dumps({'mode': mode, 'database': database, 'server': server, 'before': before, 'after': after, 'revision': 'f6b8d27a901c'}))
