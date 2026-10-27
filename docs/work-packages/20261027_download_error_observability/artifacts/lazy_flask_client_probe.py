"""Disposable local missing-secret probe; run in the configured dev container.

Pass a directory containing bootstrap download_http.py/download_with_aria2c.py.
This removes SECRET_KEY variables only in its own process and touches no project.
Never import into a live application process.
"""
import os
import socket
import sys
import threading
import time

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route

from wepppy.weppcloud.utils.helpers import get_run_owners_lazy
from wepppy.microservices.browse.errors import download_exception_handler


def main():
    sys.path.insert(0, sys.argv[1])
    from download_with_aria2c import download
    from download_http import DownloadError

    assert 'wepppy.weppcloud.app' not in sys.modules, 'Probe requires a fresh process'
    os.environ.pop('SECRET_KEY', None)
    os.environ.pop('SECRET_KEY_FILE', None)

    async def manifest(request):
        get_run_owners_lazy('diagnostic-nonexistent')

    app = Starlette(
        routes=[Route('/weppcloud/runs/test/cfg/aria2c.spec', manifest)],
        exception_handlers={Exception: download_exception_handler},
    )
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='critical'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.02)
        assert server.started, 'Local probe server failed to start'
        try:
            download('test', '/tmp/unused-destination', base_url=f'http://127.0.0.1:{port}')
        except DownloadError as error:
            message = str(error)
            assert 'SECRET_KEY' in message
            assert 'server_configuration_error' in message
            assert 'Request ID:' in message
            print(message)
            print('PASS real lazy Flask failure -> HTTP response -> bootstrap diagnostics')
        else:
            raise AssertionError('Expected configuration failure')
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()


if __name__ == '__main__':
    main()
