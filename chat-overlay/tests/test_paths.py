import tempfile
import unittest
from pathlib import Path

from chatov.paths import AppPaths, ToolLocator


class AppPathsTest(unittest.TestCase):
    def test_source_checkout(self):
        p = AppPaths.detect(frozen=False, executable="C:/py/python.exe", meipass=None, source_dir=Path("D:/app"))
        self.assertEqual(p.web_root, Path("D:/app/web"))
        self.assertEqual(p.app_dir, Path("D:/app"))
        self.assertEqual(p.tool_dirs, (Path("D:/app/ffmpeg"),))

    def test_frozen_exe_reads_bundle_and_folder_next_to_exe(self):
        p = AppPaths.detect(frozen=True, executable="E:/share/FakeLiveChat/FakeLiveChat.exe",
                            meipass="E:/share/FakeLiveChat/_internal", source_dir=Path("ignored"))
        self.assertEqual(p.web_root, Path("E:/share/FakeLiveChat/_internal/web"))
        self.assertEqual(p.app_dir, Path("E:/share/FakeLiveChat"))
        self.assertEqual(p.tool_dirs, (Path("E:/share/FakeLiveChat/ffmpeg"), Path("E:/share/FakeLiveChat/_internal/ffmpeg")))


class ToolLocatorTest(unittest.TestCase):
    def test_bundled_tool_wins_over_path(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d, "ffmpeg.exe")
            exe.write_bytes(b"")
            find = ToolLocator([Path("missing"), Path(d)], which=lambda n: "C:/sys/ffmpeg.exe")
            self.assertEqual(find("ffmpeg"), str(exe))

    def test_falls_back_to_path(self):
        self.assertEqual(ToolLocator([Path("missing")], which=lambda n: "C:/sys/" + n)("ffprobe"), "C:/sys/ffprobe")

    def test_not_found(self):
        self.assertIsNone(ToolLocator([], which=lambda n: None)("ffmpeg"))


if __name__ == "__main__":
    unittest.main()
