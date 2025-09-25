
import os
from datetime import timedelta

import redis


def _build_session_redis(db_default: int = 11):
    url = os.getenv('SESSION_REDIS_URL') or os.getenv('REDIS_URL')
    db = int(os.getenv('SESSION_REDIS_DB', db_default))

    if url:
        return redis.from_url(url, db=db)

    host = os.getenv('SESSION_REDIS_HOST', os.getenv('REDIS_HOST', 'localhost'))
    port = int(os.getenv('SESSION_REDIS_PORT', os.getenv('REDIS_PORT', '6379')))
    return redis.Redis(host=host, port=port, db=db)


def config_app(app):

    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] = 'jdskdu29uhr2uh2uheufujhe287'
    app.config['SECURITY_PASSWORD_SALT'] = b'djskhfusdifwuhfsdkjf'
    app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////geodata/weppcloud_runs/standalone.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Use endpoint names so Flask-Security runs responses through url_for,
    # which keeps redirects correct regardless of reverse-proxy layout.
    app.config['SECURITY_POST_LOGOUT_VIEW'] = 'index'
    app.config['SECURITY_POST_LOGIN_VIEW'] = 'index'
    app.config['SECURITY_POST_REGISTER_VIEW'] = 'index'
    app.config['SECURITY_LOGIN_ERROR_VIEW'] = 'security.login'
    app.config['SITE_PREFIX'] = ''
    app.config['SECURITY_CONFIRMABLE'] = True
    app.config['SECURITY_LOGIN_WITHOUT_CONFIRMATION'] = True
    app.config['SECURITY_REGISTERABLE'] = True
    app.config['SECURITY_TRACKABLE'] = True
    app.config['SECURITY_CHANGEABLE'] = True
    app.config['SECURITY_RECOVERABLE'] = True

    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = _build_session_redis()
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_KEY_PREFIX'] = 'session:'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

    app.config['W3W_API_KEY'] = 'XBL7LV7I'

    return app


def _init(db, user_datastore):

    print(db)
    
    from os.path import exists

    if exists('/geodata/weppcloud_runs/standalone.db'):
        return

    try:
        db.drop_all()
    except:
        pass

    db.create_all()
    user_datastore.create_role(name='User', description='Regular WeppCloud User')
    user_datastore.create_role(name='PowerUser', description='WeppCloud PowerUser')
    user_datastore.create_role(name='Admin', description='WeppCloud Administrator')
    user_datastore.create_role(name='Dev', description='Developer')
    user_datastore.create_role(name='Root', description='Root')

    user_datastore.create_user(email='root@weppcloud.com', password='test123',
                               first_name='Super', last_name='User')
    user_datastore.add_role_to_user('root@weppcloud.com', 'User')
    user_datastore.add_role_to_user('root@weppcloud.com', 'PowerUser')
    user_datastore.add_role_to_user('root@weppcloud.com', 'Admin')
    user_datastore.add_role_to_user('root@weppcloud.com', 'Dev')
    user_datastore.add_role_to_user('root@weppcloud.com', 'Root')

    db.session.commit()

    assert 1
