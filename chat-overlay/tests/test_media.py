import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from chatov.media import FFmpeg, FontCollector, HiddenRunner, OverlayRenderer, RenderError, ToolMissing, VideoInfo
from chatov.stickers import ImagePrim


class FakeRun:
    """subprocess.run 대역. 받은 명령을 기록하고 정해 둔 결과를 돌려준다."""

    def __init__(self, stdout="", returncode=0, stderr="", on_call=None):
        self.calls = []
        self.stdout, self.returncode, self.stderr, self.on_call = stdout, returncode, stderr, on_call

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if self.on_call:
            self.on_call(cmd, kw)
        return subprocess.CompletedProcess(cmd, self.returncode, self.stdout, self.stderr)


PROBE_JSON = json.dumps({"streams": [{"width": 1280, "height": 720, "duration": "12.5"}],
                         "format": {"duration": "12.6"}})


class FFmpegTest(unittest.TestCase):
    def test_missing_tool_raises(self):
        with self.assertRaises(ToolMissing):
            FFmpeg(run=FakeRun(), which=lambda name: None).ensure_available()

    def test_probe_reads_size_and_duration(self):
        run = FakeRun(stdout=PROBE_JSON)
        info = FFmpeg(run=run, which=lambda n: n).probe(Path("v.mp4"))
        self.assertEqual(info, VideoInfo(1280, 720, 12.5))
        self.assertEqual(run.calls[0][0][0], "ffprobe")

    def test_probe_falls_back_to_container_duration(self):
        data = json.dumps({"streams": [{"width": 10, "height": 20}], "format": {"duration": "3.0"}})
        self.assertEqual(FFmpeg(run=FakeRun(stdout=data), which=lambda n: n).probe(Path("v")).duration, 3.0)

    def test_burn_failure_raises_with_stderr_tail(self):
        ff = FFmpeg(run=FakeRun(returncode=1, stderr="boom"), which=lambda n: n)
        with self.assertRaisesRegex(RenderError, "boom"):
            ff.burn(Path("in.mp4"), "chat.ass", Path("out.mp4"), cwd=Path("."))

    def test_commands_use_resolved_tool_paths(self):
        # exe 옆에 같이 넣은 ffmpeg 를 쓰려면 이름이 아니라 찾은 경로로 실행해야 한다
        run = FakeRun(stdout=PROBE_JSON)
        ff = FFmpeg(run=run, which=lambda n: f"E:/app/ffmpeg/{n}.exe")
        ff.probe(Path("v.mp4"))
        ff.burn(Path("in.mp4"), "chat.ass", Path("out.mp4"), cwd=Path("."))
        self.assertEqual([c[0][0] for c in run.calls], ["E:/app/ffmpeg/ffprobe.exe", "E:/app/ffmpeg/ffmpeg.exe"])

    def test_missing_tool_message_mentions_bundle(self):
        with self.assertRaisesRegex(ToolMissing, "ffmpeg"):
            FFmpeg(run=FakeRun(), which=lambda name: None).probe(Path("v.mp4"))

    def test_burn_with_image_overlays_uses_filter_graph(self):
        run = FakeRun()
        FFmpeg(run=run, which=lambda n: n).burn(Path("in.mp4"), "chat.ass", Path("out.mp4"), cwd=Path("."),
                                                overlays=[ImagePrim(320, 360, 240, 160, "C:/a.png", "")])
        cmd = run.calls[0][0]
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("[1:v]scale=240:160[i1]", graph)
        self.assertIn("[0:v][i1]overlay=200:280[v1]", graph)
        self.assertIn("[v1]ass=chat.ass:fontsdir=.[vout]", graph)
        self.assertEqual(cmd[cmd.index("-map") + 1], "[vout]")
        self.assertIn("0:a?", cmd)
        self.assertEqual(cmd[cmd.index(str(Path("C:/a.png"))) - 1], "-i")
        self.assertNotIn("-vf", cmd)

    def test_burn_uses_relative_subtitle_path(self):
        run = FakeRun()
        FFmpeg(run=run, which=lambda n: n).burn(Path("C:/in.mp4"), "chat.ass", Path("C:/o.mp4"), cwd=Path("C:/w"))
        cmd, kw = run.calls[0]
        self.assertIn("ass=chat.ass:fontsdir=.", cmd)
        self.assertEqual(kw["cwd"], str(Path("C:/w")))


class HiddenRunnerTest(unittest.TestCase):
    def test_adds_no_window_flag_so_no_console_pops_up(self):
        run = FakeRun()
        HiddenRunner(run, no_window_flag=0x08000000)(["ffmpeg"], cwd="x")
        cmd, kw = run.calls[0]
        self.assertEqual(kw["creationflags"], 0x08000000)
        self.assertEqual(kw["cwd"], "x")


class FontCollectorTest(unittest.TestCase):
    def test_copies_ttf_files_from_sources(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as dest:
            Path(a, "font.ttf").write_bytes(b"x")
            Path(a, "note.txt").write_bytes(b"x")
            FontCollector([Path(a), Path("does-not-exist")]).copy_into(Path(dest))
            self.assertEqual(sorted(p.name for p in Path(dest).iterdir()), ["font.ttf"])


class FakeFFmpeg:
    def __init__(self, info=VideoInfo(1000, 600, 5.0)):
        self.info, self.burned = info, []

    def ensure_available(self):
        pass

    def probe(self, path):
        return self.info

    def burn(self, src, ass_name, out, cwd, overlays=()):
        self.burned.append((src, ass_name, out, Path(cwd, ass_name).read_text(encoding="utf-8")))
        self.overlays = list(overlays)
        Path(out).write_bytes(b"mp4")


SETTINGS = {"NICKS": ["닉"], "MSGS": ["안녕"], "COLORS": ["#ff0000"], "SEED": 3, "SPEED_PHASES": [0, 0, 0]}


class OverlayRendererTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.src = self.dir / "clip.mov"
        self.src.write_bytes(b"video")
        self.ff = FakeFFmpeg()
        self.renderer = OverlayRenderer(self.ff, FontCollector([]))

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_output_next_to_source(self):
        out = self.renderer.render(self.src, SETTINGS)
        self.assertEqual(out, self.dir / "clip_chat.mp4")
        self.assertTrue(out.exists())

    def test_output_forced_to_mp4(self):
        out = self.renderer.render(self.src, SETTINGS, self.dir / "result.avi")
        self.assertEqual(out.suffix, ".mp4")

    def test_uses_browser_timeline_when_given(self):
        settings = {**SETTINGS, "EVENTS": [{"t": 1.0, "nick": "보낸닉", "msg": "보낸말", "color": "#00ff00"}]}
        self.renderer.render(self.src, settings)
        ass = self.ff.burned[0][3]
        self.assertIn("보낸닉", ass)
        self.assertEqual(ass.count("Dialogue:"), 1)

    def test_generates_timeline_when_not_given(self):
        self.renderer.render(self.src, SETTINGS)
        self.assertGreater(self.ff.burned[0][3].count("Dialogue:"), 3)

    def test_leaves_no_temp_files_next_to_output(self):
        self.renderer.render(self.src, SETTINGS)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["clip.mov", "clip_chat.mp4"])

    def test_missing_source_raises(self):
        with self.assertRaises(RenderError):
            self.renderer.render(self.dir / "nope.mp4", SETTINGS)

    def test_stickers_are_written_under_the_chat(self):
        self.renderer.render(self.src, {**SETTINGS, "STICKERS": [{"type": "text", "text": "스티커닉"}]})
        ass = self.ff.burned[0][3]
        self.assertIn("Style: Sticker,", ass)
        self.assertRegex(ass, r"Dialogue: [0-3],[^\n]*Sticker,[^\n]*스티커닉")

    def test_alerts_from_browser_donations(self):
        settings = {**SETTINGS, "STICKERS": [{"type": "alert", "unit": "별풍선"}],
                    "DONATIONS": [{"t": 1.0, "nick": "소다", "amount": 100, "msg": ""}]}
        self.renderer.render(self.src, settings)
        self.assertIn("별풍선 100개", self.ff.burned[0][3])

    def test_platform_and_unit_reach_alerts_and_chat(self):
        settings = {**SETTINGS, "PLATFORM": "youtube", "DONATION_UNIT": "₩", "STICKERS": [{"type": "alert"}],
                    "DONATIONS": [{"t": 1.0, "nick": "소다", "amount": 2000, "msg": ""}]}
        self.renderer.render(self.src, settings)
        ass = self.ff.burned[0][3]
        self.assertIn("♥ ₩2,000 후원!", ass)            # 채팅 후원 줄
        self.assertRegex(ass, r"Dialogue: 2\d,[^\n]*\\c&HD4B800&")  # 슈퍼챗 하늘색 머리띠(#00b8d4) 알림

    def test_generated_donations_join_the_chat_when_no_browser_timeline(self):
        settings = {**SETTINGS, "DONATIONS_ON": True, "DONATION_EVERY": 1, "DONATION_UNIT": "하트"}
        self.renderer.render(self.src, settings)
        self.assertRegex(self.ff.burned[0][3], r"ChatBox,[^\n]*♥ 하트")

    def test_image_stickers_go_to_ffmpeg_overlays(self):
        png = self.dir / "s.png"
        png.write_bytes(b"png")
        self.renderer.render(self.src, {**SETTINGS, "STICKERS": [{"type": "image", "path": str(png), "height": 100}]})
        self.assertEqual([o.path for o in self.ff.overlays], [str(png)])

    def test_missing_image_files_are_skipped(self):
        self.renderer.render(self.src, {**SETTINGS, "STICKERS": [{"type": "image", "path": "C:/없는/파일.png"}]})
        self.assertEqual(self.ff.overlays, [])

    def test_empty_lists_raise(self):
        with self.assertRaises(RenderError):
            self.renderer.render(self.src, {**SETTINGS, "MSGS": []})


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg 없음")
class RealFFmpegIntegrationTest(unittest.TestCase):
    def test_renders_stickers_alerts_and_image_overlay(self):
        with tempfile.TemporaryDirectory() as d:
            src, png = Path(d, "src.mp4"), Path(d, "sticker.png")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x240:d=3",
                            "-pix_fmt", "yuv420p", str(src)], check=True)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=40x40",
                            "-frames:v", "1", str(png)], check=True)
            settings = {**SETTINGS, "STICKERS": [
                {"type": "text", "text": "별사"}, {"type": "goal"}, {"type": "alert"},
                {"type": "image", "path": str(png), "url": "/media/x.png", "height": 200, "aspect": 1, "x": 0.5, "y": 0.5}],
                "DONATIONS": [{"t": 0.5, "nick": "소다", "amount": 550, "msg": ""}]}
            ff = FFmpeg()
            out = OverlayRenderer(ff, FontCollector([])).render(src, settings, Path(d, "out.mp4"))
            self.assertEqual(ff.probe(out).width, 320)
            frame = Path(d, "f.png")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1.5", "-i", str(out), "-vf", "crop=4:4:158:118",
                            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", str(frame)], check=True)
            r, g, b = frame.read_bytes()[:3]
            self.assertGreater(r, 200)   # 가운데에 빨간 그림 스티커가 들어갔다
            self.assertLess(g, 80)

    def test_renders_a_real_clip(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "src.mp4")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x240:d=2",
                            "-pix_fmt", "yuv420p", str(src)], check=True)
            ff = FFmpeg()
            out = OverlayRenderer(ff, FontCollector([])).render(src, SETTINGS, Path(d, "out.mp4"))
            info = ff.probe(out)
            self.assertEqual((info.width, info.height), (320, 240))
            self.assertAlmostEqual(info.duration, 2.0, delta=0.2)


if __name__ == "__main__":
    unittest.main()
