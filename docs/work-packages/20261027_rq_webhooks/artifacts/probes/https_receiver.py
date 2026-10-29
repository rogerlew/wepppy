"""Disposable network-isolated TLS receiver; never use with real client traffic."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ssl
import json
from pathlib import Path
import time


class Receiver(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = self.rfile.read(min(int(self.headers.get('Content-Length', '0')), 4096)).decode('utf-8')
        with Path('/evidence/workflow_receiver.jsonl').open('a') as audit:
            audit.write(json.dumps({'body': body, 'event_id': self.headers.get('Webhook-Id'), 'received_at': time.time()}) + '\n')
        if self.path == '/hang':
            time.sleep(12)
            return
        if self.path == '/slow':
            for value in b'HTTP/1.1 204 No Content\r\n\r\n':
                try:
                    self.wfile.write(bytes([value]))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                    return
                time.sleep(.2)
            return
        if self.path == '/oversize':
            self.wfile.write(b'HTTP/1.1 200 OK\r\nX-Padding: ' + b'a' * 17000 + b'\r\n\r\n')
            return
        self.send_response({'/ack': 204, '/redirect': 302, '/retry': 503, '/failure': 503, '/deny': 403}.get(self.path, 404))
        if self.path == '/redirect':
            self.send_header('Location', 'https://localhost/must-not-follow')
        if self.path == '/retry':
            self.send_header('Retry-After', '999999')
        self.end_headers()


server = ThreadingHTTPServer(('0.0.0.0', 443), Receiver)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/tls/cert.pem', '/tls/key.pem')
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
