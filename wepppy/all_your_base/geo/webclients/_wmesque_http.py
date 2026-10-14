"""urllib transport with a deadline covering response headers as well as body.

An idle socket timeout alone allows a trickling header to exhaust failover time.
"""
import http.client
import io
import socket
import time
from urllib.request import HTTPHandler, HTTPSHandler, build_opener


class _DeadlineReader(socket.SocketIO):
    def __init__(self, sock, deadline):
        super().__init__(sock, "rb")
        self.deadline = deadline

    def readinto(self, buffer):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise socket.timeout("WMesque response deadline exceeded")
        self._sock.settimeout(remaining)
        return super().readinto(buffer)


class _DeadlineSocket:
    def __init__(self, sock, deadline):
        self.sock, self.deadline = sock, deadline

    def __getattr__(self, name):
        return getattr(self.sock, name)

    def makefile(self, mode, buffering=None):
        if mode != "rb":
            raise ValueError("WMesque transport only supports binary response reads")
        # SocketIO owns a reference just as socket.makefile does; preserve its
        # lifetime when HTTPConnection closes its reference after the response.
        self.sock._io_refs += 1
        return io.BufferedReader(_DeadlineReader(self.sock, self.deadline))


def open_with_deadline(url, timeout):
    deadline = time.monotonic() + timeout

    class HTTPConnection(http.client.HTTPConnection):
        def connect(self):
            super().connect()
            self.sock = _DeadlineSocket(self.sock, deadline)

    class HTTPSConnection(http.client.HTTPSConnection):
        def connect(self):
            super().connect()
            self.sock = _DeadlineSocket(self.sock, deadline)

    class HTTP(HTTPHandler):
        def http_open(self, request):
            return self.do_open(HTTPConnection, request)

    class HTTPS(HTTPSHandler):
        def https_open(self, request):
            return self.do_open(HTTPSConnection, request, context=self._context)

    return build_opener(HTTP(), HTTPS()).open(url, timeout=timeout)
