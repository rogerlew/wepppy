"""Run only against the isolated Redis transport acceptance Compose project."""
import asyncio
from datetime import timedelta
import json
import operator
import os
from pathlib import Path
import tempfile
import time
import uuid

import redis
from rq import Queue, Worker
from flask import Flask, session
import requests

from wepppy.config import redis_settings as settings
from wepppy.weppcloud.configuration import _build_session_redis
from wepppy.weppcloud.session_migration import MigratingRedisSessionInterface


def main():
    password = Path(os.environ['REDIS_PASSWORD_FILE']).read_bytes().rstrip(b'\n')
    prefix = 'transport-acceptance:' + uuid.uuid4().hex + ':'
    results = {}
    for db in [0, 2, 9, 11, 13, 14, 15]:
        client = settings.redis_client(db)
        assert client.ping() and client.client_info()['db'] == db
        assert password.decode() not in repr(client.connection_pool.connection_kwargs)
        client.set(prefix+'value', 'ok', ex=30)
        assert client.get(prefix+'value') == b'ok'
        client.delete(prefix+'value')
        client.close()
    results['sync_databases'] = [0, 2, 9, 11, 13, 14, 15]

    async def async_probe():
        client = settings.redis_async_client(2)
        assert await client.ping()
        async with client.pubsub() as pubsub:
            await pubsub.subscribe(prefix+'channel')
            await client.publish(prefix+'channel', 'payload')
            deadline = time.monotonic()+5
            while time.monotonic()<deadline:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if msg:
                    assert msg['data'] == b'payload'
                    break
            else:
                raise AssertionError('async PubSub timed out')
        await client.aclose()
    asyncio.run(async_probe())
    results['async_ping_pubsub'] = True

    connection = _build_session_redis()
    assert connection.client_info()['db'] == 11
    app = Flask(__name__)
    app.secret_key = 'transport-session-fixture'
    app.session_cookie_name = '__Host-weppcloud_session'
    app.config.update(PERMANENT_SESSION_LIFETIME=timedelta(seconds=1),
                      SESSION_COOKIE_MIGRATION_ENABLED=True, SESSION_COOKIE_SECURE=True,
                      SESSION_COOKIE_NAME='__Host-weppcloud_session', SESSION_COOKIE_LEGACY_NAME='session',
                      SESSION_USE_SIGNER=True, SESSION_COOKIE_PATH='/')
    app.session_interface = MigratingRedisSessionInterface(connection, prefix+'session:', use_signer=True, permanent=True)
    @app.get('/set')
    def set_session():
        session['value']='roundtrip'
        return 'ok'
    @app.get('/get')
    def get_session():
        return session.get('value', 'expired')
    browser=app.test_client()
    assert browser.get('/set', base_url='https://example.test').status_code == 200
    assert browser.get('/get', base_url='https://example.test').data == b'roundtrip'
    time.sleep(2)
    assert browser.get('/get', base_url='https://example.test').data == b'expired'
    results['session_roundtrip_expiry'] = True

    rq_connection = settings.redis_client(9)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline and not Worker.all(connection=rq_connection):
        time.sleep(.2)
    workers=Worker.all(connection=rq_connection)
    assert workers and all('default' in worker.queue_names() for worker in workers)
    job=Queue('default', connection=rq_connection).enqueue(operator.add, 20, 22, result_ttl=60)
    while time.monotonic()<deadline:
        job.refresh()
        if job.is_finished:
            break
        assert not job.is_failed, 'isolated RQ job failed'
        time.sleep(.2)
    assert job.result == 42
    results['rq_workers'] = len(workers)
    results['rq_job_result'] = 42
    results['rq_job_id'] = job.id
    job.delete()

    for name, port in [('status',9002), ('preflight',9001)]:
        response=requests.get(f'http://{name}:{port}/health', timeout=5)
        assert response.status_code == 200 and response.text == 'OK'
    results['go_health'] = True
    response=requests.get('http://rq-dashboard:9181/rq-dashboard/', timeout=10)
    assert response.status_code == 200
    results['dashboard_http'] = True

    kwargs=settings.redis_connection_kwargs(9)
    kwargs.pop('password')
    for bad_password in [None, 'wrong-transport-password']:
        client=redis.Redis(**kwargs, password=bad_password)
        try:
            client.ping()
        except redis.exceptions.AuthenticationError:
            pass
        else:
            raise AssertionError('wrong/missing credentials accepted')
        finally:
            client.close()
    original=os.environ['REDIS_PASSWORD_FILE']
    os.environ['REDIS_PASSWORD_FILE']='/missing-transport-secret'
    try:
        settings.redis_connection_kwargs(9)
    except ValueError:
        pass
    else:
        raise AssertionError('missing password file accepted')
    finally:
        os.environ['REDIS_PASSWORD_FILE']=original
    results['negative_auth_and_missing_file'] = True
    assert password.decode() not in json.dumps(results)
    print(json.dumps(results, sort_keys=True))


if __name__ == '__main__':
    main()
