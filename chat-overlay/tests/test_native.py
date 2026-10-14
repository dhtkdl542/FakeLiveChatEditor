import tempfile
import unittest
from pathlib import Path

from chatov.media import RenderError
from chatov.native import Bridge, WebviewDialogs
from chatov.server import ApiError
from tests.test_server import FakeDialogs, FakeRenderer, make_app


class AppCallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_call_returns_plain_dict(self):
        app, _ = make_app(self.tmp.name, dialogs=FakeDialogs(save="C:/o.mp4"))
        self.assertEqual(app.call("/api/pick-save", {"suggest": "a.mp4"}), {"path": "C:/o.mp4"})

    def test_call_unknown_raises_api_error(self):
        app, _ = make_app(self.tmp.name)
        with self.assertRaises(ApiError):
            app.call("/api/nope", {})


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_is_wrapped_with_ok(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(Bridge(app).call("/api/llm-models", {"base": "x"}), {"ok": True, "models": ["m1"]})

    def test_errors_never_escape_to_javascript(self):
        app, _ = make_app(self.tmp.name, renderer=FakeRenderer(error=RenderError("ffmpeg 터짐")))
        result = Bridge(app).call("/api/render", {"videoPath": "C:/v.mp4", "settings": {}})
        self.assertEqual(result, {"ok": False, "error": "ffmpeg 터짐", "status": 500})

    def test_api_errors_keep_status(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(Bridge(app).call("/api/nope", {})["status"], 404)

    def test_payload_may_be_missing(self):
        app, _ = make_app(self.tmp.name)
        self.assertTrue(Bridge(app).call("/api/ollama/status", None)["ok"])

    def test_only_api_paths_are_callable(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(Bridge(app).call("../../etc", {})["status"], 404)


class FakeWindow:
    def __init__(self, result):
        self.result, self.calls = result, []

    def create_file_dialog(self, dialog_type, **kw):
        self.calls.append((dialog_type, kw))
        return self.result


class WebviewDialogsTest(unittest.TestCase):
    def make(self, result):
        win = FakeWindow(result)
        return WebviewDialogs(lambda: win, open_type="OPEN", save_type="SAVE"), win

    def test_open_video_returns_first_path(self):
        dialogs, win = self.make(("C:/v/a.mp4",))
        self.assertEqual(dialogs.open_video(), "C:/v/a.mp4")
        dialog_type, kw = win.calls[0]
        self.assertEqual(dialog_type, "OPEN")
        self.assertIn("*.mp4", kw["file_types"][0])

    def test_open_image_asks_for_picture_files(self):
        dialogs, win = self.make(("C:/s/heart.png",))
        self.assertEqual(dialogs.open_image(), "C:/s/heart.png")
        self.assertIn("*.png", win.calls[0][1]["file_types"][0])

    def test_cancel_returns_empty(self):
        self.assertEqual(self.make(None)[0].open_video(), "")
        self.assertEqual(self.make(())[0].save_mp4("x.mp4"), "")

    def test_save_accepts_string_or_tuple_and_suggests_name(self):
        dialogs, win = self.make("C:/o/out.mp4")
        self.assertEqual(dialogs.save_mp4("clip_chat.mp4"), "C:/o/out.mp4")
        self.assertEqual(win.calls[0][1]["save_filename"], "clip_chat.mp4")
        self.assertEqual(self.make(("C:/o/t.mp4",))[0].save_mp4("a"), "C:/o/t.mp4")

    def test_save_adds_mp4_extension(self):
        self.assertEqual(self.make("C:/o/out")[0].save_mp4("a"), str(Path("C:/o/out.mp4")))


if __name__ == "__main__":
    unittest.main()
