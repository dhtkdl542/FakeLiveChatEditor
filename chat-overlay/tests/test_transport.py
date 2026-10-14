import json
import socket
import unittest

from chatov.transport import HttpTransport, ServiceError
from tests.fakes import local_server


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class HttpTransportTest(unittest.TestCase):
    def test_posts_json_and_parses_reply(self):
        seen = {}

        def echo(body):
            seen["body"] = body
            return 200, json.dumps({"ok": True})

        with local_server({("POST", "/x"): echo}) as base:
            self.assertEqual(HttpTransport().json("POST", base + "/x", {"a": 1}), {"ok": True})
        self.assertEqual(seen["body"], {"a": 1})

    def test_empty_reply_is_empty_dict(self):
        with local_server({("DELETE", "/d"): lambda b: (200, "")}) as base:
            self.assertEqual(HttpTransport().json("DELETE", base + "/d", {"m": 1}), {})

    def test_http_error_becomes_service_error_with_detail(self):
        with local_server({("GET", "/bad"): lambda b: (500, "model not found")}) as base:
            with self.assertRaisesRegex(ServiceError, "500.*model not found"):
                HttpTransport().json("GET", base + "/bad")

    def test_refused_connection_is_service_error(self):
        with self.assertRaisesRegex(ServiceError, "연결할 수 없습니다"):
            HttpTransport().json("GET", f"http://127.0.0.1:{free_port()}/x", timeout=2)

    def test_stream_yields_each_json_line(self):
        lines = [json.dumps({"n": 1}), "", json.dumps({"n": 2})]
        with local_server({("POST", "/s"): lambda b: (200, lines)}) as base:
            self.assertEqual(list(HttpTransport().stream_lines(base + "/s", {})), [{"n": 1}, {"n": 2}])


if __name__ == "__main__":
    unittest.main()
