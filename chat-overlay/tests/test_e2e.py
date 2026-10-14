"""실제 서버 + 헤드리스 Chrome 으로 화면이 오류 없이 뜨는지 확인한다. Chrome/Edge 가 없으면 건너뛴다."""
import os
import re
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import chat_app
from chatov.server import make_handler

BROWSERS = [
    Path(os.environ.get("PROGRAMFILES", "C:/Program Files"), "Google/Chrome/Application/chrome.exe"),
    Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"), "Microsoft/Edge/Application/msedge.exe"),
]
BROWSER = next((b for b in BROWSERS if b.exists()), None)


@unittest.skipUnless(BROWSER, "Chrome/Edge 없음")
class BrowserSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(chat_app.build_app()))
        cls.srv.RequestHandlerClass.log_message = lambda *a: None
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}/"
        with tempfile.TemporaryDirectory() as profile:
            proc = subprocess.run(
                [str(BROWSER), "--headless=new", "--disable-gpu", f"--user-data-dir={profile}",
                 "--window-size=1500,1000", "--virtual-time-budget=4000", "--dump-dom", cls.url],
                capture_output=True, text=True, encoding="utf-8", timeout=90)
        cls.dom = proc.stdout

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_app_initialises_without_script_errors(self):
        self.assertIn('data-ready="1"', self.dom, "main.js 초기화가 끝나지 않았습니다")
        self.assertNotIn("data-error", self.dom)

    def test_sample_stage_shows_chat_lines(self):
        self.assertGreaterEqual(len(re.findall(r'class="vline"', self.dom)), 3)

    def test_tabs_and_panels_exist(self):
        for name in ("style", "timing", "lines", "ai"):
            self.assertIn(f'data-tab="{name}"', self.dom)

    def test_ollama_catalog_rendered(self):
        self.assertIn("EXAONE 3.5 7.8B", self.dom)

    def test_sections_placeholder_rendered(self):
        self.assertIn("아직 구간이 없습니다", self.dom)

    def test_chat_lines_anchor_to_bottom_right_by_default(self):
        self.assertIn("translate(-100%, -100%)", self.dom)

    def test_chat_style_presets_and_icon_choices_rendered(self):
        for label in ("반투명 박스", "박스 + 닉 색 아이콘", "♥ 하트", "★ 별"):
            self.assertIn(label, self.dom)

    def test_manual_line_inputs_still_exist(self):
        self.assertRegex(self.dom, r'<textarea[^>]*data-field="nicks"')
        self.assertRegex(self.dom, r'<textarea[^>]*data-field="msgs"')


if __name__ == "__main__":
    unittest.main()
