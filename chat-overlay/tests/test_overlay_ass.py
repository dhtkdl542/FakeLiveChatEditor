import unittest

from chatov.donations import Donation
from chatov.overlay_ass import ALERT_ANIMATION, PrimAssWriter, StickerTrack
from chatov.shapes import ring_drawing, rounded_rect_drawing
from chatov.stickers import RectPrim, Run, Sticker, TextPrim


def dialogues(lines):
    return [l for l in lines if l.startswith("Dialogue:")]


class PrimAssWriterTest(unittest.TestCase):
    def test_text_prim_with_runs_lines_and_outline(self):
        prim = TextPrim(100.5, 50, "center", ((Run("별사", 56, "#b07cff", True, "F"), Run("♡", 39.2, "#ff5fa2", True, "F")),
                                             (Run("둘째", 20, "#333333", False, "G"),)), 9, "#6a3fb5", 2)
        line = PrimAssWriter.text(prim, 0, 5)
        self.assertTrue(line.startswith("Dialogue: 2,0:00:00.00,0:00:05.00,Sticker,"))
        self.assertIn(r"{\an5\pos(100.5,50)\bord9\shad0\3c&HB53F6A&}", line)
        self.assertIn(r"{\fnF\fs56\b1\c&HFF7CB0&}별사{\fnF\fs39.2\b1\c&HA25FFF&}♡\N{\fnG\fs20\b0\c&H333333&}둘째", line)

    def test_text_alignment_tags(self):
        mk = lambda a: PrimAssWriter.text(TextPrim(0, 0, a, ((Run("x", 10, "#fff", False, "F"),),), 0, "", 2), 0, 1)
        self.assertIn(r"\an4", mk("left"))
        self.assertIn(r"\an6", mk("right"))

    def test_text_escapes_override_braces(self):
        line = PrimAssWriter.text(TextPrim(0, 0, "left", ((Run("{\\b1}", 10, "#fff", False, "F"),),), 0, "", 2), 0, 1)
        self.assertIn("｛＼b1｝", line)

    def test_rect_with_border_is_fill_plus_ring(self):
        prim = RectPrim(100, 50, 200, 80, 16, "#ffffff", 0.5, 4, "#ff5fa2", 0)
        fill, ring = PrimAssWriter.rect(prim, 0, 5)
        self.assertTrue(fill.startswith("Dialogue: 0,"))
        self.assertIn(r"{\an5\pos(100,50)\bord0\shad0\c&HFFFFFF&\1a&H80&\p3}", fill)
        self.assertTrue(fill.endswith(rounded_rect_drawing(192, 72, 12) + r"{\p0}"))
        self.assertTrue(ring.startswith("Dialogue: 1,"))
        self.assertIn(r"\c&HA25FFF&\1a&H80&", ring)
        self.assertIn(ring_drawing(200, 80, 16, 4), ring)

    def test_rect_without_border_is_one_shape(self):
        self.assertEqual(len(PrimAssWriter.rect(RectPrim(0, 0, 10, 10, 2, "#000", 1, 0, "", 1), 0, 1)), 1)

    def test_extra_tags_go_inside_the_first_block(self):
        line = PrimAssWriter.text(TextPrim(0, 0, "center", ((Run("x", 10, "#fff", False, "F"),),), 0, "", 2), 0, 1,
                                  extra=r"\fad(1,2)")
        self.assertIn(r"\shad0\3c&H000000&\fad(1,2)}", line)


class StickerTrackTest(unittest.TestCase):
    def test_static_sticker_spans_whole_video(self):
        track = StickerTrack(1920, 1080, [Sticker.from_dict({"type": "text", "text": "별사"})], [], 30)
        lines = dialogues(track.dialogues())
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(",0:00:00.00,0:00:30.00," in l for l in lines))

    def test_ranking_changes_when_donations_arrive(self):
        ds = [Donation(10, "워린", 9000, "")]
        track = StickerTrack(1920, 1080, [Sticker.from_dict({"type": "ranking", "rows": 1})], ds, 30)
        lines = dialogues(track.dialogues())
        before = [l for l in lines if ",0:00:00.00,0:00:10.00," in l]
        after = [l for l in lines if ",0:00:10.00,0:00:30.00," in l]
        self.assertTrue(any("별사" in l for l in before))
        self.assertTrue(any("워린" in l for l in after))
        self.assertTrue(any("10,452" in l for l in after))

    def test_alerts_pop_in_on_top_of_the_chat(self):
        ds = [Donation(2, "소다", 550, "")]
        track = StickerTrack(1920, 1080, [Sticker.from_dict({"type": "alert", "show": 4})], ds, 30)
        lines = dialogues(track.dialogues())
        self.assertEqual(len(lines), 3)  # 바탕 + 테두리 + 글자
        self.assertTrue(all(",0:00:02.00,0:00:06.00," in l for l in lines))
        self.assertTrue(all(ALERT_ANIMATION in l for l in lines))
        self.assertTrue(all(int(l.split(",")[0].split(" ")[1]) > 10 for l in lines))  # 채팅 층(10)보다 위
        self.assertTrue(any("하트 550개" in l for l in lines))

    def test_alerts_use_platform_look_and_unit(self):
        ds = [Donation(2, "소다", 10000, "축하")]
        track = StickerTrack(1920, 1080, [Sticker.from_dict({"type": "alert"})], ds, 30, unit="₩", platform="youtube")
        text = "\n".join(track.dialogues())
        self.assertIn("₩10,000", text)
        self.assertIn("축하", text)
        self.assertIn(r"\c&H00B3FF&", text)   # 노랑 슈퍼챗 머리띠 (#ffb300)

    def test_history_caption_uses_platform_unit(self):
        track = StickerTrack(1920, 1080, [Sticker.from_dict({"type": "history", "count": 1})], [], 30, unit="하트")
        self.assertIn("하트 4,860개 선물!", "\n".join(track.dialogues()))

    def test_no_alert_sticker_means_no_alerts(self):
        track = StickerTrack(1920, 1080, [], [Donation(2, "a", 1, "")], 30)
        self.assertEqual(track.dialogues(), [])

    def test_images_are_collected_for_ffmpeg(self):
        s = Sticker.from_dict({"type": "image", "path": "C:/a.png", "url": "/media/a.png", "height": 100})
        track = StickerTrack(1920, 1080, [s], [], 30)
        self.assertEqual([i.path for i in track.images()], ["C:/a.png"])
        self.assertEqual(track.dialogues(), [])

    def test_images_without_file_are_skipped(self):
        track = StickerTrack(1920, 1080, [Sticker.from_dict({"type": "image"})], [], 30)
        self.assertEqual(track.images(), [])


if __name__ == "__main__":
    unittest.main()
