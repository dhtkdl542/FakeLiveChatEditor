import tempfile
import unittest
from pathlib import Path

from chatov.files import ByteRange, RangeNotSatisfiable, StaticFiles, VideoRegistry


class VideoRegistryTest(unittest.TestCase):
    def test_register_gives_url_with_token_and_extension(self):
        reg = VideoRegistry(token_factory=lambda: "abc123")
        url = reg.register(Path("C:/v/clip.MOV"))
        self.assertEqual(url, "/video/abc123.mov")
        self.assertEqual(reg.resolve_url("/video/abc123.mov"), Path("C:/v/clip.MOV"))

    def test_unknown_token_resolves_to_none(self):
        reg = VideoRegistry()
        self.assertIsNone(reg.resolve_url("/video/nope.mp4"))
        self.assertIsNone(reg.resolve_url("/other"))

    def test_other_prefix_for_images(self):
        reg = VideoRegistry(token_factory=lambda: "img1", prefix="/media/")
        self.assertEqual(reg.register(Path("C:/s/heart.PNG")), "/media/img1.png")
        self.assertEqual(reg.resolve_url("/media/img1.png"), Path("C:/s/heart.PNG"))
        self.assertIsNone(reg.resolve_url("/video/img1.png"))

    def test_default_tokens_are_unguessable_and_unique(self):
        reg = VideoRegistry()
        a, b = reg.register(Path("a.mp4")), reg.register(Path("b.mp4"))
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(a.split("/")[-1].split(".")[0]), 16)


class ByteRangeTest(unittest.TestCase):
    def test_no_header_is_whole_file(self):
        self.assertEqual(ByteRange.parse("", 100), ByteRange(0, 99, 100, False))

    def test_open_ended_range(self):
        self.assertEqual(ByteRange.parse("bytes=10-", 100), ByteRange(10, 99, 100, True))

    def test_closed_range_is_clamped(self):
        self.assertEqual(ByteRange.parse("bytes=10-500", 100), ByteRange(10, 99, 100, True))

    def test_suffix_range(self):
        self.assertEqual(ByteRange.parse("bytes=-30", 100), ByteRange(70, 99, 100, True))

    def test_start_past_end_not_satisfiable(self):
        with self.assertRaises(RangeNotSatisfiable):
            ByteRange.parse("bytes=200-", 100)

    def test_garbage_falls_back_to_whole_file(self):
        self.assertEqual(ByteRange.parse("bytes=abc", 100), ByteRange(0, 99, 100, False))

    def test_length_and_content_range(self):
        r = ByteRange(10, 19, 100, True)
        self.assertEqual((r.length, r.content_range), (10, "bytes 10-19/100"))


class StaticFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name, "web")
        (root / "js").mkdir(parents=True)
        (root / "index.html").write_text("<html>")
        (root / "js" / "main.js").write_text("x")
        Path(self.tmp.name, "secret.txt").write_text("secret")
        self.files = StaticFiles(root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_root_serves_index(self):
        path, ctype = self.files.resolve("/")
        self.assertEqual((path.name, ctype), ("index.html", "text/html; charset=utf-8"))

    def test_js_gets_module_friendly_mime(self):
        # 윈도우 레지스트리가 .js 를 text/plain 으로 알려주면 모듈 스크립트가 막힌다
        self.assertEqual(self.files.resolve("/js/main.js")[1], "text/javascript; charset=utf-8")

    def test_traversal_blocked(self):
        self.assertIsNone(self.files.resolve("/../secret.txt"))
        self.assertIsNone(self.files.resolve("/js/../../secret.txt"))
        self.assertIsNone(self.files.resolve("/%2e%2e/secret.txt"))

    def test_missing_and_directories_are_none(self):
        self.assertIsNone(self.files.resolve("/nope.js"))
        self.assertIsNone(self.files.resolve("/js"))


if __name__ == "__main__":
    unittest.main()
