"""여러 테스트에서 같이 쓰는 대역(가짜) 객체."""
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@contextmanager
def local_server(routes):
    """routes: {(method, path): handler(req_body:dict) -> (status, body:str|list[str])}.
    body 가 list 면 한 줄씩 흘려보낸다(스트리밍)."""

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _serve(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            body = json.loads(raw) if raw else None
            fn = routes.get((method, self.path))
            if not fn:
                self.send_response(404)
                self.end_headers()
                return
            status, payload = fn(body)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if isinstance(payload, list):
                for line in payload:
                    self.wfile.write((line + "\n").encode("utf-8"))
                    self.wfile.flush()
            else:
                self.wfile.write(payload.encode("utf-8"))

        def do_GET(self):
            self._serve("GET")

        def do_POST(self):
            self._serve("POST")

        def do_DELETE(self):
            self._serve("DELETE")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


class FakeTransport:
    """HttpTransport 대역. (method, url) 별로 응답을 정해 두고 요청을 기록한다."""

    def __init__(self, responses=None, streams=None):
        self.responses = responses or {}
        self.streams = streams or {}
        self.requests = []

    def json(self, method, url, body=None, timeout=300):
        self.requests.append((method, url, body))
        r = self.responses.get((method, url))
        if isinstance(r, Exception):
            raise r
        if callable(r):
            return r(body)
        if r is None:
            raise AssertionError(f"예상하지 못한 요청: {method} {url}")
        return r

    def stream_lines(self, url, body, timeout=120):
        self.requests.append(("STREAM", url, body))
        r = self.streams.get(url)
        if isinstance(r, Exception):
            raise r
        return iter(r or [])
