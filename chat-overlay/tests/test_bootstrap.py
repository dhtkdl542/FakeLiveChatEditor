import unittest
import urllib.error
import urllib.request
from pathlib import Path

import chat_app
from chatov.native import has_webview2
from chatov.server import App
from tests.test_server import FakeDialogs


class BootstrapTest(unittest.TestCase):
    def test_build_app_wires_real_objects_and_serves_web_index(self):
        app = chat_app.build_app()
        self.assertIsInstance(app, App)
        resp = app.get("/", {})
        self.assertEqual(resp.status, 200)
        self.assertIn(b"<html", resp.body.lower())

    def test_build_app_accepts_dialogs(self):
        dialogs = FakeDialogs(save="C:/o.mp4")
        self.assertEqual(chat_app.build_app(dialogs=dialogs).call("/api/pick-save", {}), {"path": "C:/o.mp4"})

    def test_source_paths_point_next_to_entry_script(self):
        here = Path(chat_app.__file__).resolve().parent
        self.assertEqual(chat_app.PATHS.web_root, here / "web")
        self.assertEqual(chat_app.PATHS.app_dir, here)

    def test_start_server_on_free_port_read_only(self):
        server, url = chat_app.start_server(chat_app.build_app(), allow_post=False)
        try:
            self.assertTrue(url.startswith("http://127.0.0.1:"))
            self.assertEqual(urllib.request.urlopen(url, timeout=5).status, 200)
            req = urllib.request.Request(url + "api/ollama/status", data=b"{}", headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 405)
        finally:
            server.shutdown()
            server.server_close()


class FakeWebview:
    """pywebview 대역: 창을 만들고 start() 는 바로 돌아온다 (사용자가 창을 닫은 것처럼)."""

    class FileDialog:
        OPEN, SAVE = "OPEN", "SAVE"

    def __init__(self, log):
        self.log = log

    def create_window(self, title, url, **kw):
        self.log.append(("window", title, url, sorted(kw)))
        return object()

    def start(self, **kw):
        self.log.append(("start", kw.get("gui")))


class RunNativeTest(unittest.TestCase):
    def test_opens_read_only_server_in_app_window_and_exits_hard_after_close(self):
        # pythonnet(.NET) 은 파이썬이 정리하며 끝날 때 가끔 예외를 낸다 → 창이 닫히면 바로 프로세스를 끝낸다
        log = []
        chat_app.run_native(webview=FakeWebview(log), exit_fn=lambda code: log.append(("exit", code)))
        window, start, exit_ = log
        self.assertEqual(window[0], "window")
        self.assertTrue(window[2].startswith("http://127.0.0.1:") and window[2].endswith("/?native=1"))
        self.assertIn("js_api", window[3])
        self.assertEqual(start, ("start", "edgechromium"))
        self.assertEqual(exit_, ("exit", 0))
        with self.assertRaises(Exception):  # 서버는 닫혔다
            urllib.request.urlopen(window[2], timeout=2)


class WebView2DetectionTest(unittest.TestCase):
    KEY = r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"

    def test_found_in_machine_registry(self):
        self.assertTrue(has_webview2(lambda hive, key: "154.0.4258.48" if key == self.KEY else None))

    def test_found_in_user_registry(self):
        user_key = r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        self.assertTrue(has_webview2(lambda hive, key: "120.0" if key == user_key else None))

    def test_missing_or_placeholder_version(self):
        self.assertFalse(has_webview2(lambda hive, key: None))
        self.assertFalse(has_webview2(lambda hive, key: "0.0.0.0"))


if __name__ == "__main__":
    unittest.main()
