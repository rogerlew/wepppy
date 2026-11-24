"""Real loopback PyCurl and Tornado consumers of the bundled decoder/TLS stack."""
import asyncio
import base64
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import gzip
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import ipaddress
import ssl
import threading
from urllib.request import parse_http_list, parse_keqv_list

import brotli
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import pycurl
import pytest
from tornado.curl_httpclient import CurlAsyncHTTPClient
from tornado.httpclient import HTTPClientError

pytestmark = pytest.mark.integration
BODY = bytes(range(256)) * 256 + "Unicode café\n".encode() * 100
COMPRESSED = brotli.compress(BODY)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/basic":
            valid = self.headers.get("Authorization") == "Basic " + base64.b64encode(b"fixture:password").decode()
            if not valid:
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="fixture"')
                self.end_headers()
                return
        if self.path == "/digest":
            authorization = self.headers.get("Authorization", "")
            valid = False
            if authorization.startswith("Digest "):
                fields = parse_keqv_list(parse_http_list(authorization[7:]))
                digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
                ha1 = digest("fixture:fixture:password")
                ha2 = digest("GET:/digest")
                expected = digest(f'{ha1}:fixture-nonce:{fields["nc"]}:{fields["cnonce"]}:auth:{ha2}')
                valid = fields["response"] == expected and fields["uri"] == "/digest"
            if not valid:
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Digest realm="fixture", nonce="fixture-nonce", algorithm=SHA-256, qop="auth"')
                self.end_headers()
                return
        encoding = self.path.removeprefix("/encoded/") if self.path.startswith("/encoded/") else "br"
        payload = {"br": COMPRESSED, "gzip": gzip.compress(BODY, mtime=0), "deflate": zlib.compress(BODY)}[encoding]
        if self.path == "/corrupt":
            payload = b"\xff" * 16
        self.send_response(200)
        self.send_header("Content-Encoding", encoding)
        self.send_header("X-Request-Accept-Encoding", self.headers.get("Accept-Encoding", ""))
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.path == "/truncated":
            payload = payload[:len(payload) // 2]
        try:
            # Deliberately split the compressed stream across socket writes.
            for offset in range(0, len(payload), 7):
                self.wfile.write(payload[offset:offset + 7])
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # Expected when the client rejects corrupt content and closes early.
            return


@pytest.fixture(scope="module")
def endpoints(tmp_path_factory):
    root = tmp_path_factory.mktemp("pycurl-tls")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fixture CA")])
    now = datetime.now(timezone.utc)
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
          .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
          .sign(key, hashes.SHA256()))
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fixture")]))
            .issuer_name(name).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
            .sign(key, hashes.SHA256()))
    trusted = root / "ca.pem"
    trusted.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (root / "server.pem").write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    (root / "key.pem").write_bytes(leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(root / "server.pem", root / "key.pem")
    servers, threads = [], []
    try:
        for secure in (False, True):
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            servers.append(server)
            if secure:
                server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            threads.append(thread)
        yield {"http": f"http://127.0.0.1:{servers[0].server_port}",
               "https": f"https://127.0.0.1:{servers[1].server_port}", "ca": str(trusted)}
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)
            assert not thread.is_alive()


def fetch(url, ca=None, authentication=None):
    output = BytesIO()
    with closing(pycurl.Curl()) as client:
        client.setopt(pycurl.URL, url)
        client.setopt(pycurl.PROXY, "")
        client.setopt(pycurl.ACCEPT_ENCODING, "br")
        client.setopt(pycurl.WRITEFUNCTION, output.write)
        client.setopt(pycurl.TIMEOUT_MS, 3000)
        client.setopt(pycurl.SSL_VERIFYPEER, 1)
        client.setopt(pycurl.SSL_VERIFYHOST, 2)
        if ca:
            client.setopt(pycurl.CAINFO, ca)
        if authentication:
            client.setopt(pycurl.USERPWD, "fixture:password")
            client.setopt(pycurl.HTTPAUTH, authentication)
        client.perform()
        assert client.getinfo(pycurl.RESPONSE_CODE) == 200
    return output.getvalue()


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_brotli_response_decodes_identically(endpoints, scheme):
    assert fetch(endpoints[scheme] + "/valid", endpoints["ca"]) == BODY


@pytest.mark.parametrize("path,authentication", [("basic", pycurl.HTTPAUTH_BASIC), ("digest", pycurl.HTTPAUTH_DIGEST)])
def test_supported_http_authentication(endpoints, path, authentication):
    assert fetch(endpoints["https"] + "/" + path, endpoints["ca"], authentication) == BODY


@pytest.mark.parametrize("path", ["corrupt", "truncated"])
def test_bad_or_incomplete_transfer_is_an_error(endpoints, path):
    with pytest.raises(pycurl.error) as error:
        fetch(endpoints["http"] + "/" + path)
    assert error.value.args[0] in {pycurl.E_BAD_CONTENT_ENCODING, pycurl.E_PARTIAL_FILE}


@pytest.mark.parametrize("failure", ["untrusted", "hostname"])
def test_tls_verification_remains_required(endpoints, failure):
    url = endpoints["https"]
    if failure == "hostname":
        url = url.replace("127.0.0.1", "localhost")
    with pytest.raises(pycurl.error) as error:
        fetch(url + "/valid", endpoints["ca"] if failure == "hostname" else None)
    assert error.value.args[0] == pycurl.E_PEER_FAILED_VERIFICATION


@pytest.mark.parametrize("path", ["valid", "corrupt", "truncated"])
def test_tornado_curl_backend_preserves_body_and_transport_errors(endpoints, path):
    async def request():
        client = CurlAsyncHTTPClient(force_instance=True)
        try:
            response = await client.fetch(endpoints["http"] + "/" + path,
                ca_certs=endpoints["ca"], request_timeout=3, decompress_response=True,
                prepare_curl_callback=lambda curl: curl.setopt(pycurl.PROXY, ""))
            return response.body
        finally:
            client.close()
    if path == "valid":
        assert asyncio.run(request()) == BODY
    else:
        with pytest.raises(HTTPClientError) as error:
            asyncio.run(request())
        assert error.value.code == 599
        assert error.value.errno == (pycurl.E_BAD_CONTENT_ENCODING if path == "corrupt" else pycurl.E_PARTIAL_FILE)


@pytest.mark.parametrize("failure", ["untrusted", "hostname"])
def test_tornado_curl_backend_rejects_invalid_tls(endpoints, failure):
    async def request():
        client = CurlAsyncHTTPClient(force_instance=True)
        url = endpoints["https"]
        if failure == "hostname":
            url = url.replace("127.0.0.1", "localhost")
        try:
            await client.fetch(url + "/valid", request_timeout=3,
                ca_certs=endpoints["ca"] if failure == "hostname" else None,
                prepare_curl_callback=lambda curl: curl.setopt(pycurl.PROXY, ""))
        finally:
            client.close()
    with pytest.raises(HTTPClientError) as error:
        asyncio.run(request())
    assert error.value.code == 599
    assert error.value.errno == pycurl.E_PEER_FAILED_VERIFICATION


@pytest.mark.parametrize("encoding", ["br", "gzip", "deflate"])
@pytest.mark.parametrize("decompress", [True, False])
def test_tornado_encoding_negotiation_and_raw_body(endpoints, encoding, decompress):
    async def request():
        client = CurlAsyncHTTPClient(force_instance=True)
        try:
            return await client.fetch(endpoints["https"] + "/encoded/" + encoding,
                ca_certs=endpoints["ca"], request_timeout=3, decompress_response=decompress,
                prepare_curl_callback=lambda curl: curl.setopt(pycurl.PROXY, ""))
        finally:
            client.close()
    response = asyncio.run(request())
    expected = {"br": COMPRESSED, "gzip": gzip.compress(BODY, mtime=0), "deflate": zlib.compress(BODY)}[encoding]
    assert response.body == (BODY if decompress else expected)
    assert response.headers["X-Request-Accept-Encoding"] == ("gzip,deflate" if decompress else "")
