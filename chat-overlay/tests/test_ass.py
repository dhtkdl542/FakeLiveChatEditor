import dataclasses
import unittest

from chatov.ass import AssWriter, ChatLayout, OverlayStyle, ass_time, escape_ass, row_key
from chatov.badges import Badge
from chatov.icons import icon_drawing
from chatov.shapes import ring_drawing, rounded_rect_drawing
from chatov.timeline import ChatEvent

STYLE = OverlayStyle(align="right", side_margin=24, bottom_margin=24, line_h=30, visible=3, fade_in_ms=180,
                     fade_out_ms=450, fade_up=18, max_chars=6, nick_font="N", nick_size=20, nick_bold=False,
                     msg_font="M", msg_size=18, msg_color="#ffffff", outline=2, box=False, box_color="#000000",
                     box_opacity=0.5, box_padding=6, icon="", icon_color="", icon_scale=1.0,
                     highlight_color="#ff5fa2", highlight_opacity=0.85)


def style(**kw):
    return dataclasses.replace(STYLE, **kw)


def ev(t, nick="ㅇㅇ", msg="hi", color="#ff0000", highlight=False):
    return ChatEvent(t, nick, msg, color, highlight)


class OverlayStyleTest(unittest.TestCase):
    def test_defaults_put_chat_in_bottom_right_corner(self):
        s = OverlayStyle.from_settings({})
        self.assertEqual((s.align, s.side_margin, s.bottom_margin), ("right", 24, 24))
        self.assertEqual((s.visible, s.line_h, s.max_chars), (8, 36, 22))
        self.assertEqual((s.box, s.outline, s.icon, s.nick_bold, s.msg_color), (False, 2, "", False, "#ffffff"))

    def test_reads_settings(self):
        s = OverlayStyle.from_settings({"VISIBLE": 5, "ALIGN": "left", "NICK_FONT": "X", "BOX": True,
                                        "BOX_OPACITY": 0.3, "ICON": "heart", "NICK_BOLD": True})
        self.assertEqual((s.visible, s.align, s.nick_font, s.box, s.box_opacity, s.icon, s.nick_bold),
                         (5, "left", "X", True, 0.3, "heart", True))

    def test_unknown_align_falls_back_to_right(self):
        self.assertEqual(OverlayStyle.from_settings({"ALIGN": "middle"}).align, "right")


class ChatLayoutTest(unittest.TestCase):
    def setUp(self):
        self.layout = ChatLayout(STYLE)

    def test_first_event_has_one_newest_row(self):
        rows = self.layout.rows_at([ev(1)], 0)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].is_newest)
        self.assertEqual((rows[0].age, rows[0].alpha), (0, 0))

    def test_only_visible_rows_kept(self):
        rows = self.layout.rows_at([ev(i, msg=str(i)) for i in range(5)], 4)
        self.assertEqual([r.msg for r in rows], ["2", "3", "4"])
        self.assertEqual([r.age for r in rows], [2, 1, 0])

    def test_oldest_row_marked_when_full(self):
        events = [ev(i) for i in range(4)]
        self.assertTrue(self.layout.rows_at(events, 3)[0].is_oldest)
        self.assertFalse(self.layout.rows_at(events, 1)[0].is_oldest)

    def test_alpha_grows_with_age_and_caps(self):
        rows = ChatLayout(style(visible=20, fade_up=90)).rows_at([ev(i) for i in range(4)], 3)
        self.assertEqual([r.alpha for r in rows], [200, 180, 90, 0])

    def test_long_message_wraps_and_nick_only_on_first_piece(self):
        rows = self.layout.rows_at([ev(0, nick="닉", msg="가나다라마바사")], 0)
        self.assertEqual([(r.nick, r.msg) for r in rows], [("닉", "가나다라마바"), ("", "사")])

    def test_partial_old_message_keeps_its_tail(self):
        rows = self.layout.rows_at([ev(0, msg="가나다라마바사아자차"), ev(1, msg="끝")], 1)
        self.assertEqual([r.msg for r in rows], ["가나다라마바", "사아자차", "끝"])

    def test_position_hugs_bottom_right_corner(self):
        # 기준점 = 글자 줄의 오른쪽 아래. 박스를 켜면 박스 바깥선이 여백에 닿도록 안쪽으로 들인다
        row = self.layout.rows_at([ev(0)], 0)[0]
        self.assertEqual(self.layout.position(row, 1000, 600), (976, 576, "right"))
        boxed = ChatLayout(style(box=True, box_padding=6))
        self.assertEqual(boxed.position(row, 1000, 600), (970, 570, "right"))

    def test_older_rows_stack_upwards(self):
        rows = self.layout.rows_at([ev(0), ev(1)], 1)
        self.assertEqual(self.layout.position(rows[0], 1000, 600)[1], 576 - 30)

    def test_left_alignment(self):
        layout = ChatLayout(style(align="left", box=True, box_padding=6))
        row = layout.rows_at([ev(0)], 0)[0]
        self.assertEqual(layout.position(row, 1000, 600), (30, 570, "left"))


class AssWriterTest(unittest.TestCase):
    def build(self, events, duration=10.0, **kw):
        return AssWriter(1000, 600, style(**kw)).build(events, duration)

    def dialogues(self, text):
        return [line for line in text.splitlines() if line.startswith("Dialogue:")]

    def test_header_has_outline_and_box_styles(self):
        text = self.build([])
        self.assertIn("PlayResX: 1000", text)
        self.assertIn("PlayResY: 600", text)
        self.assertRegex(text, r"Style: Chat,M,18,.*,1,2,0,3,")
        self.assertRegex(text, r"Style: ChatBox,M,18,.*,4,0,0,3,")

    def test_single_event_line_in_outline_mode(self):
        line = self.dialogues(self.build([ev(1.5, nick="닉", msg="안녕")], duration=4))[0]
        self.assertTrue(line.startswith("Dialogue: 10,0:00:01.50,0:00:04.00,Chat,"))
        self.assertIn(r"\an3\pos(976,576)", line)
        self.assertIn(r"\fad(180,0)", line)
        self.assertIn(r"\bord2", line)
        self.assertIn(r"\1a&H00&\3c&H000000&\3a&H00&", line)
        self.assertIn(r"\c&H0000FF&}닉 ", line)
        self.assertTrue(line.endswith("안녕"))

    def test_box_mode_uses_one_box_behind_the_whole_row(self):
        line = self.dialogues(self.build([ev(0)], box=True, box_color="#102030", box_opacity=0.5))[0]
        self.assertIn(",ChatBox,", line)
        self.assertIn(r"\pos(970,570)", line)
        self.assertIn(r"\bord6\shad0", line)
        self.assertIn(r"\3a&HFF&", line)          # 글자 테두리는 숨기고 박스만
        self.assertIn(r"\4c&H302010&\4a&HFF&\t(0,180,\4a&H80&)", line)

    def test_box_fades_in_with_the_newest_row(self):
        # libass 의 \fad 는 BorderStyle 4 박스에 안 먹어서, 박스 투명도를 \t 로 따로 움직인다
        line = self.dialogues(self.build([ev(0)], box=True, box_opacity=0.5))[0]
        self.assertIn(r"\4a&HFF&\t(0,180,\4a&H80&)", line)

    def test_box_fades_out_with_the_oldest_row(self):
        lines = self.dialogues(self.build([ev(i) for i in range(4)], duration=5, box=True, box_opacity=0.5))
        oldest_in_last_frame = lines[-3]          # 3초~5초 화면 → 2000ms 동안, 마지막 450ms 에 사라짐
        self.assertIn(r"\t(1550,2000,\4a&HFF&)", oldest_in_last_frame)

    def test_box_fade_out_shorter_than_frame_starts_at_zero(self):
        lines = self.dialogues(self.build([ev(0), ev(0.1), ev(0.2), ev(0.3)], duration=0.4, box=True))
        self.assertIn(r"\t(0,100,\4a&HFF&)", lines[-3])

    def test_outline_mode_needs_no_box_animation(self):
        self.assertNotIn(r"\t(", self.build([ev(i) for i in range(4)], duration=5))

    def test_box_fades_with_age_like_the_text(self):
        lines = self.dialogues(self.build([ev(0), ev(1), ev(2)], box=True, box_opacity=0.5))
        oldest = lines[-3]
        self.assertIn(r"\1a&H24&", oldest)
        self.assertIn(r"\4a&H92&", oldest)        # 255 - 127×219/255

    def test_each_event_redraws_all_visible_rows_until_next_event(self):
        lines = self.dialogues(self.build([ev(1), ev(2), ev(3)], duration=5))
        self.assertEqual(len(lines), 1 + 2 + 3)
        self.assertTrue(lines[1].startswith("Dialogue: 10,0:00:02.00,0:00:03.00"))
        self.assertIn(r"\pos(976,546)", lines[1])

    def test_oldest_row_fades_out_when_full(self):
        last_frame = self.dialogues(self.build([ev(i) for i in range(4)], duration=5))[-3:]
        self.assertIn(r"\fad(0,450)", last_frame[0])
        self.assertIn(r"\1a&H24&", last_frame[0])

    def test_icon_is_drawn_before_nick_in_nick_color(self):
        lines = self.dialogues(self.build([ev(0, nick="닉", msg="가나다라마바사")], icon="heart"))
        first, continuation = lines
        self.assertIn(r"{\c&H0000FF&\p3}m ", first)
        self.assertLess(first.index(r"\p3"), first.index("닉"))
        self.assertIn(r"{\p0}", first)
        self.assertNotIn(r"\p3", continuation)

    def test_icon_custom_color(self):
        line = self.dialogues(self.build([ev(0)], icon="star", icon_color="#00ff00"))[0]
        self.assertIn(r"{\c&H00FF00&\p3}", line)

    def test_bold_nick_and_message_color(self):
        line = self.dialogues(self.build([ev(0, nick="닉", msg="말")], nick_bold=True, msg_color="#ffff00"))[0]
        self.assertIn(r"\b1\c&H0000FF&}닉", line)
        self.assertIn(r"\b0\c&H00FFFF&}말", line)

    def test_chat_is_drawn_on_layer_10_between_stickers_and_alerts(self):
        self.assertTrue(self.dialogues(self.build([ev(0)]))[0].startswith("Dialogue: 10,"))

    def test_header_has_sticker_style(self):
        self.assertIn("Style: Sticker,", self.build([]))

    def test_extra_dialogues_are_appended(self):
        text = AssWriter(1000, 600, STYLE).build([ev(0)], 5, extra=["Dialogue: 0,a", "Dialogue: 20,b"])
        self.assertTrue(text.rstrip().endswith("Dialogue: 0,a\nDialogue: 20,b"))

    def test_donation_row_gets_its_own_pink_box_even_without_box_mode(self):
        lines = self.dialogues(self.build([ev(0), ev(1, nick="별사", msg="♥ 하트 100개 선물!", highlight=True)],
                                          max_chars=30))
        donation = lines[-1]
        self.assertIn(",ChatBox,", donation)
        self.assertIn(r"\4c&HA25FFF&", donation)
        self.assertIn(r"\pos(970,570)", donation)     # 박스 여백만큼 안쪽
        self.assertIn(r"\b1\c&HFFFFFF&}♥ 하트 100개 선물!", donation)
        normal = lines[-2]
        self.assertIn(",Chat,", normal)
        self.assertIn(r"\pos(976,546)", normal)       # 위 줄은 그대로 (줄 간격 30)

    def test_highlight_flag_is_kept_on_wrapped_pieces(self):
        rows = ChatLayout(STYLE).rows_at([ev(0, msg="가나다라마바사", highlight=True)], 0)
        self.assertEqual([r.highlight for r in rows], [True, True])

    def test_text_cannot_inject_override_tags(self):
        line = self.dialogues(self.build([ev(0, msg=r"{\b1}x")]))[0]
        self.assertNotIn(r"{\b1}x", line)
        self.assertIn("｛＼b1｝x", line)


def dialogues(text):
    return [line for line in text.splitlines() if line.startswith("Dialogue:")]


MANAGER = Badge("manager", "매니저", "shield", "#22c55e", 1.0)


class OverlayStyleShapeAndBadgeTest(unittest.TestCase):
    def test_reads_box_shape_border_and_badges(self):
        s = OverlayStyle.from_settings({"BOX_SHAPE": "pill", "BOX_RADIUS": 10, "BOX_BORDER": 2, "BOX_BORDER_COLOR": "#ff0000",
                                        "BADGES_ON": True, "BADGE_OVERRIDES": {"코코넛": "sub"},
                                        "BADGES": [{"key": "manager", "label": "매니저", "icon": "crown",
                                                    "color": "#123456", "share": 0.5}]})
        self.assertEqual((s.box_shape, s.box_radius, s.box_border, s.box_border_color), ("pill", 10, 2, "#ff0000"))
        self.assertEqual((s.badges_on, s.badge_overrides), (True, {"코코넛": "sub"}))
        self.assertEqual(s.badges, (Badge("manager", "매니저", "crown", "#123456", 0.5),))

    def test_defaults_keep_the_old_look(self):
        s = OverlayStyle.from_settings({"BOX_SHAPE": "별모양"})
        self.assertEqual((s.box_shape, s.box_border, s.badges_on), ("square", 0, False))


class BadgeRowTest(unittest.TestCase):
    def build(self, events, **kw):
        return dialogues(AssWriter(1000, 600, style(**kw)).build(events, 4))

    def test_badge_is_drawn_before_nick_in_badge_color(self):
        line = self.build([ev(0, nick="닉")], badges_on=True, badges=(MANAGER,))[0]
        self.assertIn(r"{\c&H5EC522&\p3}" + icon_drawing("shield", 16) + r"{\p0} ", line)
        self.assertLess(line.index(r"\p3"), line.index("닉"))

    def test_badges_off_draws_nothing(self):
        self.assertNotIn(r"\p3", self.build([ev(0)], badges_on=False, badges=(MANAGER,))[0])

    def test_global_icon_comes_first_then_badge(self):
        line = self.build([ev(0, nick="닉")], icon="circle", badges_on=True, badges=(MANAGER,))[0]
        self.assertLess(line.index(icon_drawing("circle", 16)), line.index(icon_drawing("shield", 16)))

    def test_manual_no_badge(self):
        line = self.build([ev(0, nick="닉")], badges_on=True, badges=(MANAGER,), badge_overrides={"닉": ""})[0]
        self.assertNotIn(r"\p3", line)

    def test_continuation_piece_has_no_badge(self):
        lines = self.build([ev(0, nick="닉", msg="가나다라마바사")], badges_on=True, badges=(MANAGER,))
        self.assertNotIn(r"\p3", lines[1])


class ShapedBoxTest(unittest.TestCase):
    """둥근 · 알약 박스와 테두리는 브라우저가 잰 줄 폭으로 직접 그린다 (libass 줄 박스는 각진 모양뿐)."""
    WIDTHS = {row_key("닉", "안녕", False): 100, row_key("닉", "선물", True): 100, row_key("둘", "안녕", False): 50}

    def build(self, events, widths=None, **kw):
        kw = {"box": True, "box_color": "#102030", "box_opacity": 0.5, **kw}
        return dialogues(AssWriter(1000, 600, style(**kw), text_widths=self.WIDTHS if widths is None else widths)
                         .build(events, 4))

    def test_rounded_box_is_a_shape_under_the_text(self):
        box, text = self.build([ev(0, nick="닉", msg="안녕")], box_shape="rounded", box_radius=8)
        # 글자 폭 100 + 여백 6×2 = 112, 줄 높이 20 + 6×2 = 32. 글자 오른쪽 아래 (970,570) 에서 여백만큼 바깥이 박스
        self.assertTrue(box.startswith("Dialogue: 8,0:00:00.00,0:00:04.00,Chat,"))
        self.assertIn(r"{\an5\pos(920,560)\bord0\shad0\c&H302010&\1a&H80&\fad(180,0)\p3}"
                      + rounded_rect_drawing(112, 32, 8) + r"{\p0}", box)
        self.assertTrue(text.startswith("Dialogue: 10,0:00:00.00,0:00:04.00,Chat,"))
        self.assertIn(r"\an3\pos(970,570)\fad(180,0)\bord0\shad0\1a&H00&}", text)
        self.assertNotIn(r"\4c", text)

    def test_pill_uses_half_height_radius(self):
        box = self.build([ev(0, nick="닉", msg="안녕")], box_shape="pill")[0]
        self.assertIn(rounded_rect_drawing(112, 32, 16), box)

    def test_border_is_a_ring_on_top_of_an_inset_fill(self):
        fill, ring, _ = self.build([ev(0, nick="닉", msg="안녕")], box_shape="rounded", box_radius=8,
                                   box_border=2, box_border_color="#ff5fa2")
        self.assertIn(rounded_rect_drawing(108, 28, 6) + r"{\p0}", fill)
        self.assertTrue(ring.startswith("Dialogue: 9,"))
        self.assertIn(r"\c&HA25FFF&\1a&H00&\fad(180,0)\p3}" + ring_drawing(112, 32, 8, 2), ring)

    def test_square_with_border_is_drawn_too(self):
        fill = self.build([ev(0, nick="닉", msg="안녕")], box_shape="square", box_border=2)[0]
        self.assertIn(rounded_rect_drawing(108, 28, 0), fill)

    def test_left_aligned_box_grows_to_the_right(self):
        box = self.build([ev(0, nick="닉", msg="안녕")], box_shape="rounded", align="left")[0]
        self.assertIn(r"\pos(80,560)", box)

    def test_plain_square_box_keeps_the_libass_box(self):
        lines = self.build([ev(0, nick="닉", msg="안녕")], box_shape="square")
        self.assertEqual(len(lines), 1)
        self.assertIn(",ChatBox,", lines[0])

    def test_row_without_measured_width_falls_back_to_square_box(self):
        lines = self.build([ev(0, nick="닉", msg="안녕")], widths={}, box_shape="rounded")
        self.assertEqual(len(lines), 1)
        self.assertIn(",ChatBox,", lines[0])

    def test_donation_row_uses_highlight_color_and_the_shape(self):
        box = self.build([ev(0, nick="닉", msg="선물", highlight=True)], box=False, box_shape="pill")[0]
        self.assertIn(r"\c&HA25FFF&\1a&H26&", box)   # 분홍, 불투명도 0.85
        self.assertIn(rounded_rect_drawing(112, 32, 16), box)

    def test_older_rows_box_and_border_fade_with_age(self):
        lines = self.build([ev(0, nick="둘", msg="안녕"), ev(1, nick="닉", msg="안녕")], box_shape="rounded",
                           box_border=2)
        older_fill, older_ring = lines[3], lines[4]     # 두 번째 화면의 위 줄
        self.assertIn(r"\1a&H89&", older_fill)          # 255 - round(127×237/255)
        self.assertIn(r"\1a&H12&", older_ring)          # 테두리는 글자처럼 18 만큼만 흐려짐
        self.assertIn(rounded_rect_drawing(58, 28, 6), older_fill)


class HelpersTest(unittest.TestCase):
    def test_ass_time_format(self):
        self.assertEqual(ass_time(3725.5), "1:02:05.50")
        self.assertEqual(ass_time(-1), "0:00:00.00")

    def test_escape_removes_newlines(self):
        self.assertEqual(escape_ass("a\nb"), "a b")


if __name__ == "__main__":
    unittest.main()
