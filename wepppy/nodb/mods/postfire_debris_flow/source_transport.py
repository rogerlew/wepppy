"""Explicit bounded transports for the approved M3 and M1 Kf source endpoints.

Run in a dedicated main-thread preparation process: SIGALRM bounds DNS/TLS,
slow response bodies and native raster callbacks, not just socket inactivity.
No GDAL URL is exposed and no redirect or automatic retry is permitted.
"""
from contextlib import contextmanager
import io
import hashlib
import json
import re
import signal
import threading
import time
from urllib.request import HTTPRedirectHandler, Request, build_opener

__all__ = ['THICK_URL', 'KF_URL', 'SDA_URL', 'deadline', 'Transport', 'RangeFile']
THICK_URL = 'https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/675721b9d34e5c5dfd05c575/STATSGO-THICK.tif'
KF_URL = 'https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/6750c172d34ed8d3858534d8/statsgo-KFFACT.tif'
SDA_URL = 'https://SDMDataAccess.nrcs.usda.gov/Tabular/post.rest'
MAX_BODY = 96*1024*1024
MAX_TEXT = 1024*1024
_ACTIVE_DEADLINE = None  # Set only by the dedicated supervised child.


@contextmanager
def deadline(seconds):
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Bounded acquisition requires a dedicated main-thread process')
    if seconds <= 0:
        raise TimeoutError('Source acquisition deadline exceeded')
    previous = signal.getsignal(signal.SIGALRM)
    old_delay, old_interval = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    def expired(signum, frame):
        raise TimeoutError('Source acquisition deadline exceeded')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, min(seconds,old_delay) if old_delay else seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)
        if old_delay:
            signal.setitimer(signal.ITIMER_REAL,max(.000001,old_delay-(time.monotonic()-started)),old_interval)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Source redirect is forbidden')


class Transport:
    """One acquisition's aggregate response budget and retained request log."""
    def __init__(self, output, *, seconds=120, limit=MAX_BODY):
        self.output = output
        self.until = time.monotonic()+seconds
        self.limit = min(limit,MAX_BODY)
        self.received = 0
        self.requests = 0
        self.opener = build_opener(_NoRedirect())

    def request(self, url, *, method='GET', headers=None, data=None, expected=None, limit=None):
        if url not in (THICK_URL,KF_URL,SDA_URL):
            raise ValueError('Unapproved source endpoint')
        if method not in ('GET','HEAD','POST') or (url == SDA_URL) != (method == 'POST'):
            raise ValueError('Unapproved source method')
        if data is not None and len(data) > MAX_TEXT:
            raise ValueError('Encoded source request exceeds 1 MiB')
        remaining = self.limit-self.received
        cap = min(remaining,remaining if limit is None else limit)
        if cap < 0 or (method != 'HEAD' and cap == 0):
            raise ValueError('Aggregate source response limit exhausted')
        self.requests += 1
        record = {'url':url,'method':method,'headers':headers or {},'received_bytes':0,'status':'incomplete'}
        with (self.output/f'request-{self.requests:05d}-start.json').open('x') as stream:
            json.dump(record,stream,sort_keys=True)
        raw = b''
        try:
            if _ACTIVE_DEADLINE is not None:
                _ACTIVE_DEADLINE.value = min(self.until,time.monotonic()+30)
            with deadline(min(30,self.until-time.monotonic())):
                request = Request(url,data=data,headers={'Accept-Encoding':'identity',**(headers or {})},method=method)
                with self.opener.open(request,timeout=min(30,max(.001,self.until-time.monotonic()))) as response:
                    info = {k.lower():v for k,v in response.headers.items()}
                    record.update(http_status=response.status,response_headers=info)
                    if response.geturl() != url or info.get('content-encoding','identity') != 'identity':
                        raise ValueError('Redirected or encoded source response')
                    if expected is not None:
                        expected(response.status,info)
                    elif response.status != 200:
                        raise ValueError('Unexpected source HTTP status')
                    if method != 'HEAD':
                        length = info.get('content-length')
                        if length is not None and (not length.isdecimal() or int(length) > cap):
                            raise ValueError('Invalid or over-budget response length')
                        chunks = []
                        checksum = hashlib.sha256()
                        left = cap if length is None else int(length)
                        with (self.output/f'request-{self.requests:05d}.body').open('xb') as retained:
                            while left:
                                chunk = response.read(min(left,65536))
                                if not chunk:
                                    if length is not None:
                                        raise ValueError('Truncated source response')
                                    break
                                left -= len(chunk)
                                self.received += len(chunk)
                                record['received_bytes'] += len(chunk)
                                retained.write(chunk)
                                checksum.update(chunk)
                                chunks.append(chunk)
                            else:
                                if length is None:
                                    raise ValueError('Unframed source response exhausted byte limit')
                        raw = b''.join(chunks)
                        record['body_sha256'] = checksum.hexdigest()
                    record['status'] = 'complete'
                    return info,raw
        except Exception as exc:  # noqa: BLE001 -- retained transport diagnostic boundary; re-raises.
            # Transport boundary: retain the failed request, then propagate;
            # malformed/network/native callback errors never become fallback.
            record.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:2048])
            if isinstance(getattr(exc,'code',None),int):
                record['http_status'] = exc.code
            raise
        finally:
            if _ACTIVE_DEADLINE is not None:
                _ACTIVE_DEADLINE.value = 0
            # Every admitted request has an immutable diagnostic, even when a
            # callback/HTTP/deadline failure prevents receiving a usable body.
            name = self.output/f'request-{self.requests:05d}.json'
            with name.open('x') as stream:
                json.dump(record,stream,sort_keys=True)


class RangeFile(io.RawIOBase):
    """Seekable original object, served solely by identity-pinned HTTP ranges."""
    def __init__(self, transport, *, url=None):
        self.transport = transport
        self.url = THICK_URL if url is None else url
        if self.url not in (THICK_URL, KF_URL):
            raise ValueError('Unapproved raster endpoint')
        headers,_ = transport.request(self.url,method='HEAD')
        self.identity = self._identity(headers)
        self.etag,self.size,self.modified = self.identity
        self.position = 0
        self.path,self.mode,self.fs = self.url.rsplit('/',1)[-1],'rb',self
        self.blocks = {}
        self._failure = [None]

    @property
    def failure(self): return self._failure[0]

    def open(self, path, mode):
        # Rasterio FilePath's documented file-object clone protocol. Each
        # handle has its own cursor but shares the single budget/cache/latch.
        if path != self.path or mode != self.mode:
            raise ValueError('Only the pinned original object can be opened')
        clone = RangeFile.__new__(RangeFile)
        clone.__dict__.update(self.__dict__)
        clone.position = 0
        return clone

    @staticmethod
    def _identity(headers):
        etag = headers.get('etag','')
        length = headers.get('content-length','')
        if not re.fullmatch(r'"[^"\r\n]+"',etag) or not length.isdecimal() or int(length) <= 0:
            raise ValueError('Missing strong object identity/length')
        return etag,int(length),headers.get('last-modified')

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.position+offset if whence == 1 else self.size+offset if whence == 2 else -1
        if position < 0:
            raise ValueError('Invalid range seek')
        self.position = position
        return position

    def read(self, size=-1):
        try:
            return self._read(size)
        except (OSError,ValueError,RuntimeError) as exc:
            self._failure[0] = exc
            raise

    def _read(self, size):
        if self.failure is not None:
            raise self.failure
        if size is None or size < 0:
            raise ValueError('Whole-object read is forbidden')
        end = min(self.size,self.position+size)
        if end-self.position > MAX_BODY:
            raise ValueError('Raster read exceeds acquisition budget')
        result = []
        try:
            while self.position < end:
                start = (self.position//65536)*65536
                stop = min(start+65536,self.size)-1
                if start not in self.blocks:
                    def validate(status,headers):
                        if (status != 206 or headers.get('etag') != self.etag
                                or headers.get('content-range') != f'bytes {start}-{stop}/{self.size}'
                                or headers.get('content-length') != str(stop-start+1)):
                            raise ValueError('Range or object identity mismatch')
                    _,block = self.transport.request(self.url,headers={'Range':f'bytes={start}-{stop}','If-Match':self.etag},
                                                     expected=validate,limit=stop-start+1)
                    self.blocks[start] = block
                count = min(end,self.position+(stop-self.position+1))-self.position
                result.append(self.blocks[start][self.position-start:self.position-start+count])
                self.position += count
            return b''.join(result)
        except (OSError,ValueError) as exc:
            # GDAL's callback boundary can catch Python exceptions. Latch the
            # failure so callers cannot accept a partially decoded raster.
            self._failure[0] = exc
            raise

    def verify(self):
        if self.failure is not None:
            raise self.failure
        headers,_ = self.transport.request(self.url,method='HEAD')
        if self._identity(headers) != self.identity:
            raise ValueError('Source object changed during preparation')
