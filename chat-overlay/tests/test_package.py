import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.package import Packager


class PackagerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.app = root / "dist" / "FakeLiveChat"
        (self.app / "_internal" / "web").mkdir(parents=True)
        (self.app / "FakeLiveChat.exe").write_bytes(b"exe")
        self.ffmpeg_root = root / "ffmpeg"
        (self.ffmpeg_root / "bin").mkdir(parents=True)
        for name in ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe"):
            (self.ffmpeg_root / "bin" / name).write_bytes(name.encode())
        (self.ffmpeg_root / "LICENSE").write_text("GPL v3")
        self.packager = Packager(self.app, self.ffmpeg_root / "bin")

    def tearDown(self):
        self.tmp.cleanup()

    def test_copies_only_needed_ffmpeg_tools_with_license(self):
        self.packager.add_ffmpeg()
        names = sorted(p.name for p in (self.app / "ffmpeg").iterdir())
        self.assertEqual(names, ["LICENSE.txt", "SOURCE.txt", "ffmpeg.exe", "ffprobe.exe"])
        self.assertIn("GPL", (self.app / "ffmpeg" / "LICENSE.txt").read_text())
        self.assertIn("ffmpeg.org", (self.app / "ffmpeg" / "SOURCE.txt").read_text(encoding="utf-8"))

    def test_missing_ffmpeg_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            Packager(self.app, Path(self.tmp.name, "nowhere")).add_ffmpeg()

    def test_writes_readme_for_recipients(self):
        self.packager.add_readme()
        text = (self.app / "읽어주세요.txt").read_text(encoding="utf-8")
        for must in ("FakeLiveChat.exe", "WebView2", "Ollama", "추가 정보"):
            self.assertIn(must, text)

    def test_zip_contains_app_folder(self):
        self.packager.add_ffmpeg()
        zip_path = self.packager.make_zip()
        self.assertEqual(zip_path, self.app.parent / "FakeLiveChat.zip")
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
        self.assertIn("FakeLiveChat/FakeLiveChat.exe", names)
        self.assertIn("FakeLiveChat/ffmpeg/ffmpeg.exe", names)

    def test_find_ffmpeg_bin_from_path(self):
        found = Packager.find_ffmpeg_bin(which=lambda n: str(self.ffmpeg_root / "bin" / "ffmpeg.exe"))
        self.assertEqual(found, self.ffmpeg_root / "bin")
        self.assertIsNone(Packager.find_ffmpeg_bin(which=lambda n: None))


if __name__ == "__main__":
    unittest.main()
