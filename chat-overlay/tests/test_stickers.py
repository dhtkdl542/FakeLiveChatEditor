import unittest

from chatov.donations import Donation
from chatov.stickers import (AlertSticker, BannerSticker, GoalSticker, HistorySticker, ImagePrim, ImageSticker, RankingSticker, TableSticker,
                             RectPrim, Run, Sticker, StickerState, TextPrim, TextSticker)

EMPTY = StickerState({}, 0)


def texts(prims):
    return [p for p in prims if isinstance(p, TextPrim)]


def rects(prims):
    return [p for p in prims if isinstance(p, RectPrim)]


class FactoryTest(unittest.TestCase):
    def test_builds_each_type_with_defaults(self):
        for kind, cls in [("text", TextSticker), ("ranking", RankingSticker), ("goal", GoalSticker),
                          ("banner", BannerSticker), ("alert", AlertSticker), ("image", ImageSticker)]:
            self.assertIsInstance(Sticker.from_dict({"type": kind}), cls)

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            Sticker.from_dict({"type": "spaceship"})

    def test_reads_fields(self):
        s = Sticker.from_dict({"type": "text", "text": "갓스", "x": 0.3, "y": 0.2, "scale": 1.5, "heart": False})
        self.assertEqual((s.text, s.x, s.y, s.scale, s.heart), ("갓스", 0.3, 0.2, 1.5, False))

    def test_only_ranking_and_goal_follow_donations(self):
        self.assertTrue(Sticker.from_dict({"type": "ranking"}).dynamic)
        self.assertTrue(Sticker.from_dict({"type": "goal"}).dynamic)
        self.assertFalse(Sticker.from_dict({"type": "ranking", "auto": False}).dynamic)
        self.assertFalse(Sticker.from_dict({"type": "text"}).dynamic)


class StickerStateTest(unittest.TestCase):
    def test_sums_donations_up_to_time(self):
        ds = [Donation(1, "a", 10, ""), Donation(2, "b", 5, ""), Donation(3, "a", 7, "")]
        self.assertEqual(StickerState.at(ds, 2.5), StickerState({"a": 10, "b": 5}, 15, tuple(ds[:2])))
        self.assertEqual(StickerState.at(ds, 1, "₩", "youtube").platform, "youtube")
        self.assertEqual(StickerState.at(ds, 0.5), EMPTY)


class TextStickerTest(unittest.TestCase):
    def test_two_layers_white_inner_and_colored_outer_outline(self):
        s = TextSticker.from_dict({"type": "text", "text": "별사", "x": 0.1, "y": 0.5, "size": 56,
                                   "fill": "#b07cff", "inner": "#ffffff", "outer": "#6a3fb5",
                                   "innerWidth": 6, "outerWidth": 3, "heartColor": "#ff5fa2"})
        outer, inner = s.layout(1920, 1080, EMPTY)
        self.assertEqual((outer.x, outer.y, outer.align), (192, 540, "center"))
        self.assertEqual((outer.outline_w, outer.outline_color, outer.layer), (9, "#6a3fb5", 2))
        self.assertEqual((inner.outline_w, inner.outline_color, inner.layer), (6, "#ffffff", 3))
        self.assertEqual(outer.lines, ((Run("별사", 56, "#b07cff", True, "Malgun Gothic"),
                                        Run("♡", 39.2, "#ff5fa2", True, "Malgun Gothic")),))

    def test_scales_with_video_height_and_sticker_scale(self):
        s = TextSticker.from_dict({"type": "text", "size": 60, "scale": 1.5, "innerWidth": 4, "outerWidth": 2})
        outer, _ = s.layout(1280, 720, EMPTY)
        self.assertEqual(outer.lines[0][0].size, 60)
        self.assertEqual(outer.outline_w, 6)

    def test_without_heart(self):
        outer, _ = TextSticker.from_dict({"type": "text", "heart": False}).layout(1920, 1080, EMPTY)
        self.assertEqual(len(outer.lines[0]), 1)


class RankingStickerTest(unittest.TestCase):
    BASE = {"type": "ranking", "x": 0.5, "y": 0.5, "width": 300, "rows": 3, "title": "오늘의 후원 순위",
            "entries": [["별사", 6558], ["갓스", 5326], ["워린", 1452], ["소다", 10]]}

    def test_panel_box_and_rows(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY)
        box = rects(prims)[0]
        self.assertEqual((box.cx, box.cy, box.w, box.h), (960, 540, 300, 14 * 2 + 38 + 3 * 30))
        title, *rows = texts(prims)
        self.assertEqual((title.x, title.y, title.align), (960 - 150 + 14, 540 - 78 + 14 + 19, "left"))
        self.assertEqual(title.lines[0][0].text, "오늘의 후원 순위")
        self.assertEqual(len(rows), 3 * 3)
        rank, nick, amount = rows[0:3]
        self.assertEqual([rank.lines[0][0].text, nick.lines[0][0].text, amount.lines[0][0].text], ["1등", "별사", "6,558"])
        self.assertEqual(rank.y, 540 - 78 + 14 + 38 + 15)
        self.assertEqual((amount.x, amount.align), (960 + 150 - 14, "right"))

    def test_donations_reorder_the_ranking(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, StickerState({"워린": 6000, "새닉": 100}, 6100))
        names = [p.lines[0][0].text for p in texts(prims)[1:]][1::3]
        self.assertEqual(names, ["워린", "별사", "갓스"])

    def test_manual_ranking_ignores_donations(self):
        prims = Sticker.from_dict({**self.BASE, "auto": False}).layout(1920, 1080, StickerState({"워린": 9999}, 9999))
        self.assertEqual([p.lines[0][0].text for p in texts(prims)[1:]][1::3], ["별사", "갓스", "워린"])


class GoalStickerTest(unittest.TestCase):
    BASE = {"type": "goal", "x": 0.5, "y": 0.5, "width": 320, "current": 16719, "target": 38000}

    def test_value_text_and_progress_bar(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY)
        box, track, fill = rects(prims)
        self.assertEqual(texts(prims)[1].lines[0][0].text, "16,719 / 38,000 (43%)")
        self.assertEqual((track.w, track.h), (320 - 28, 16))
        self.assertAlmostEqual(fill.w, round((320 - 28) * 16719 / 38000, 2), places=2)
        self.assertAlmostEqual(fill.cx - fill.w / 2, track.cx - track.w / 2, places=1)  # 왼쪽부터 찬다

    def test_donations_fill_the_goal(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, StickerState({"a": 1281}, 1281))
        self.assertEqual(texts(prims)[1].lines[0][0].text, "18,000 / 38,000 (47%)")

    def test_empty_goal_has_no_fill_and_full_goal_caps(self):
        empty = Sticker.from_dict({**self.BASE, "current": 0}).layout(1920, 1080, EMPTY)
        self.assertEqual(len(rects(empty)), 2)
        full = Sticker.from_dict({**self.BASE, "current": 99999}).layout(1920, 1080, EMPTY)
        self.assertEqual(rects(full)[2].w, rects(full)[1].w)


class BannerStickerTest(unittest.TestCase):
    def test_lines_are_centered_and_stacked(self):
        s = Sticker.from_dict({"type": "banner", "x": 0.5, "y": 0.5, "width": 260,
                               "lines": ["방송시간", "오후 1시 ~ 5시", "BJ닉네임"]})
        prims = s.layout(1920, 1080, EMPTY)
        box = rects(prims)[0]
        self.assertAlmostEqual(box.h, 2 * 12 + (30 + 22 + 22) * 1.35, places=2)
        first, second, _ = texts(prims)
        self.assertEqual((first.x, first.align, first.lines[0][0].size, first.lines[0][0].bold), (960, "center", 30, True))
        self.assertAlmostEqual(first.y, 540 - box.h / 2 + 12 + 30 * 1.35 / 2, places=2)
        self.assertAlmostEqual(second.y - first.y, (30 + 22) * 1.35 / 2, places=2)


class AlertStickerTest(unittest.TestCase):
    def test_one_line_alert(self):
        s = Sticker.from_dict({"type": "alert", "x": 0.5, "y": 0.5, "width": 520, "unit": "하트"})
        prims = s.layout_alert(1920, 1080, Donation(1, "소다", 550, ""))
        box = rects(prims)[0]
        self.assertEqual((box.cx, box.cy, box.w, box.h), (960, 540, 520, 16 * 2 + 28))
        self.assertGreater(box.border_w, 0)
        text = texts(prims)[0]
        self.assertEqual((text.x, text.y, text.align), (960, 540, "center"))
        self.assertEqual([r.text for r in text.lines[0]], ["♥ ", "소다", "님 ", "하트 550개", " 선물!"])

    def test_message_adds_second_line(self):
        s = Sticker.from_dict({"type": "alert", "unit": "별풍선"})
        prims = s.layout_alert(1920, 1080, Donation(1, "a", 1000, "사랑해요"))
        self.assertEqual(rects(prims)[0].h, 16 * 2 + 28 + 20)
        self.assertEqual([r.text for r in texts(prims)[0].lines[1]], ["사랑해요"])
        self.assertIn("별풍선 1,000개", [r.text for r in texts(prims)[0].lines[0]])

    def test_unit_and_look_follow_the_platform_when_blank(self):
        s = Sticker.from_dict({"type": "alert"})
        self.assertEqual((s.unit, s.style), ("", ""))
        prims = s.layout_alert(1920, 1080, Donation(1, "a", 100, ""), StickerState({}, 0, (), "별풍선", "afreeca"))
        words = [r.text for p in texts(prims) for line in p.lines for r in line]
        self.assertIn("별풍선 100개", words)
        self.assertIn("100", words)  # 아프리카 카드형: 큰 숫자

    def test_explicit_style_and_unit_win(self):
        s = Sticker.from_dict({"type": "alert", "style": "panda", "unit": "하트"})
        prims = s.layout_alert(1920, 1080, Donation(1, "a", 100, ""), StickerState({}, 0, (), "₩", "youtube"))
        self.assertIn("하트 100개", [r.text for r in texts(prims)[0].lines[0]])

    def test_alert_shows_nothing_in_static_layout(self):
        self.assertEqual(Sticker.from_dict({"type": "alert"}).layout(1920, 1080, EMPTY), [])


class TableStickerTest(unittest.TestCase):
    """엑셀방송의 '엑셀 표': 금색 머리줄 + 멤버별 별풍점수 · 기여도 + 총합. 후원이 오면 멤버 점수가 오른다."""
    BASE = {"type": "table", "x": 0.5, "y": 0.5, "width": 360, "rows": 3, "title": "BJ 엑셀",
            "headers": ["BJ", "별풍점수", "기여도"], "highlightRow": 1, "showTotal": True,
            "entries": [["소야", 500], ["요아정", 300], ["린린", 200]]}

    def test_size_from_title_header_rows_and_total(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY)
        box = rects(prims)[0]
        self.assertEqual((box.cx, box.cy, box.w, box.h), (960, 540, 360, 30 + 28 + (3 + 1) * 26))

    def test_cells_show_members_scores_and_contribution(self):
        cells = [p.lines[0][0].text for p in texts(Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY))]
        self.assertEqual(cells[0], "BJ 엑셀")
        self.assertEqual(cells[1:4], ["BJ", "별풍점수", "기여도"])
        self.assertEqual(cells[4:7], ["소야", "500", "50.0%"])
        self.assertEqual(cells[-3:], ["총합", "1,000", "100%"])

    def test_numbers_right_aligned_names_left(self):
        t = texts(Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY))
        name, score, share = t[4:7]
        self.assertEqual((name.align, score.align, share.align), ("left", "right", "right"))
        self.assertEqual(name.x, 960 - 180 + 8)

    def test_highlighted_row_and_grid_lines(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY)
        colors = [r.color for r in rects(prims)]
        self.assertIn("#ffb6d9", colors)   # 강조 줄
        thin = [r for r in rects(prims) if min(r.w, r.h) <= 1.5]
        self.assertGreaterEqual(len(thin), 2 + 4)  # 세로 칸막이 2 + 가로 줄

    def test_donations_go_to_a_member_and_reorder(self):
        s = Sticker.from_dict(self.BASE)
        member = TableSticker.member_for("시청자", 1000, 3)
        ds = (Donation(1, "시청자", 1000, ""),)
        cells = [p.lines[0][0].text for p in texts(s.layout(1920, 1080, StickerState({"시청자": 1000}, 1000, ds)))]
        winner = self.BASE["entries"][member][0]
        self.assertEqual(cells[4], winner)
        self.assertEqual(cells[-2], "2,000")

    def test_member_choice_is_deterministic(self):
        # 후원자 닉 글자 코드 합 + 금액 → 멤버 (미리보기와 결과 영상이 같은 멤버를 고른다)
        self.assertEqual(TableSticker.member_for("ab", 10, 3), (97 + 98 + 10) % 3)

    def test_manual_table_and_no_total(self):
        s = Sticker.from_dict({**self.BASE, "auto": False, "showTotal": False, "title": ""})
        prims = s.layout(1920, 1080, StickerState({"x": 999}, 999, (Donation(1, "x", 999, ""),)))
        self.assertEqual(rects(prims)[0].h, 28 + 3 * 26)
        self.assertNotIn("총합", [p.lines[0][0].text for p in texts(prims)])


YT = StickerState({}, 0, (), "₩", "youtube")


class YoutubeSuperChatTest(unittest.TestCase):
    """유튜브 슈퍼챗: 금액대 색 머리띠(아바타 · 이름 · 금액) + 아래 메시지 칸"""

    def alert(self, amount, msg=""):
        s = Sticker.from_dict({"type": "alert", "x": 0.5, "y": 0.5, "width": 420})
        return s.layout_alert(1920, 1080, Donation(1, "소다", amount, msg), YT)

    def test_header_only_without_message(self):
        card = rects(self.alert(10000))[0]
        self.assertEqual((card.cx, card.cy, card.w, card.h), (960, 540, 420, 64))
        self.assertEqual(card.color, "#ffb300")

    def test_message_adds_lighter_body_below_the_header(self):
        prims = self.alert(10000, "가" * 30)  # 22자씩 → 2줄
        card, header, cover = rects(prims)[0], rects(prims)[1], rects(prims)[2]
        self.assertEqual(card.h, 64 + 2 * 24 + 24)
        self.assertEqual((card.color, header.color, cover.color), ("#ffca28", "#ffb300", "#ffb300"))
        self.assertEqual(cover.r, 0)   # 머리띠 아래 모서리를 각지게 덮는다

    def test_avatar_circle_with_initial(self):
        prims = self.alert(1000)
        avatar = [r for r in rects(prims) if r.w == r.h][0]
        self.assertEqual((avatar.w, avatar.r), (40, 20))
        self.assertIn("소", [p.lines[0][0].text for p in texts(prims)])

    def test_name_and_amount(self):
        t = texts(self.alert(50000, "축하해요"))
        words = [p.lines[0][0].text for p in t]
        self.assertIn("소다", words)
        self.assertIn("₩50,000", words)
        self.assertIn("축하해요", words)

    def test_tier_colors_follow_youtube(self):
        tier = AlertSticker.youtube_tier
        self.assertEqual(tier(1000)[0], "#1565c0")
        self.assertEqual(tier(2000)[0], "#00b8d4")
        self.assertEqual(tier(5000)[0], "#00bfa5")
        self.assertEqual(tier(20000)[0], "#e65100")
        self.assertEqual(tier(100000)[0], "#d00000")
        self.assertEqual(tier(10000)[2], "#000000")   # 노랑 띠에는 검은 글자
        self.assertEqual(tier(50000)[2], "#ffffff")


class AfreecaAlertTest(unittest.TestCase):
    def test_big_number_card(self):
        s = Sticker.from_dict({"type": "alert", "style": "afreeca", "x": 0.5, "y": 0.5, "width": 380})
        prims = s.layout_alert(1920, 1080, Donation(1, "구릭", 1000, ""), StickerState({}, 0, (), "별풍선", "afreeca"))
        card = rects(prims)[0]
        self.assertEqual((card.w, card.border_color), (380, "#ff3b5c"))
        outer, inner, line = texts(prims)
        self.assertEqual((outer.lines[0][0].text, inner.outline_color), ("1000", "#ffffff"))
        self.assertEqual([r.text for r in line.lines[0]], ["구릭", "님 ", "별풍선 1,000개", " 선물!"])

    def test_message_line(self):
        s = Sticker.from_dict({"type": "alert", "style": "afreeca"})
        with_msg = s.layout_alert(1920, 1080, Donation(1, "a", 10, "사랑해"), EMPTY)
        without = s.layout_alert(1920, 1080, Donation(1, "a", 10, ""), EMPTY)
        self.assertEqual(rects(with_msg)[0].h - rects(without)[0].h, 24)


class HistoryStickerTest(unittest.TestCase):
    """아프리카TV 의 후원 카드 더미: 큰 숫자 카드가 세로로 쌓이고, 새 후원이 맨 위에 온다."""
    BASE = {"type": "history", "x": 0.5, "y": 0.5, "width": 200, "count": 3, "unit": "별풍선",
            "entries": [["구릭", 4860], ["채원♥익", 2871], ["보라", 486], ["하늘", 10]]}

    def cards(self, prims):
        return [p for p in rects(prims)]

    def test_stack_size_and_card_boxes(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY)
        cards = self.cards(prims)
        self.assertEqual(len(cards), 3)
        h = 3 * 108 + 2 * 10
        self.assertEqual([c.cy for c in cards], [540 - h / 2 + 54, 540 - h / 2 + 172, 540 - h / 2 + 290])
        self.assertEqual((cards[0].w, cards[0].h), (200, 108))

    def test_caption_stays_inside_the_card_border(self):
        prims = Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY)
        card, caption = rects(prims)[0], texts(prims)[3]
        bottom_inside = card.cy + card.h / 2 - card.border_w
        self.assertLessEqual(caption.y + caption.lines[0][0].size / 2, bottom_inside - 2)

    def test_card_shows_big_number_nick_and_caption(self):
        t = texts(Sticker.from_dict(self.BASE).layout(1920, 1080, EMPTY))
        # 카드마다: 숫자(바깥 테두리 층) · 숫자(안쪽 흰 테두리 층) · 닉 · 안내
        outer, inner, nick, caption = t[0:4]
        self.assertEqual((outer.lines[0][0].text, inner.lines[0][0].text), ("4860", "4860"))
        self.assertEqual((inner.outline_color, outer.layer < inner.layer), ("#ffffff", True))
        self.assertEqual(nick.lines[0][0].text, "구릭")
        self.assertEqual(caption.lines[0][0].text, "별풍선 4,860개 선물!")

    def test_number_color_by_amount_tier(self):
        s = Sticker.from_dict({**self.BASE, "count": 4})
        fills = [p.lines[0][0].color for p in texts(s.layout(1920, 1080, EMPTY))[0::4]]
        self.assertEqual(fills, ["#ff3b5c", "#ff3b5c", "#2f80ff", "#20b26b"])
        self.assertEqual(HistorySticker.tier_color(500), "#ff8a00")

    def test_blank_unit_follows_platform(self):
        s = Sticker.from_dict({**self.BASE, "unit": ""})
        caption = texts(s.layout(1920, 1080, StickerState({}, 0, (), "₩", "youtube")))[3]
        self.assertEqual(caption.lines[0][0].text, "₩4,860 후원!")

    def test_new_donations_go_on_top(self):
        ds = (Donation(1, "소다", 999, ""), Donation(2, "뭉치", 333, ""))
        t = texts(Sticker.from_dict(self.BASE).layout(1920, 1080, StickerState({}, 0, ds)))
        self.assertEqual([p.lines[0][0].text for p in t[0::4]], ["333", "999", "4860"])
        self.assertEqual(t[2].lines[0][0].text, "뭉치")


class MvpStickerTest(unittest.TestCase):
    def test_shows_top_donor(self):
        s = Sticker.from_dict({"type": "mvp", "x": 0.5, "y": 0.1, "entries": [["구릭", 8132], ["보라", 100]]})
        (line,) = s.layout(1920, 1080, EMPTY)
        self.assertEqual([r.text for r in line.lines[0]], ["MVP ", "구릭", " 8,132개"])
        self.assertEqual((line.x, line.y, line.align), (960, 108, "center"))
        self.assertGreater(line.outline_w, 0)

    def test_donations_can_take_over_mvp(self):
        s = Sticker.from_dict({"type": "mvp", "entries": [["구릭", 8132]]})
        state = StickerState({"보라": 5000, "구릭": 0}, 5000, (Donation(1, "보라", 9000, ""),))
        (line,) = s.layout(1920, 1080, StickerState({"보라": 9000}, 9000, state.donations))
        self.assertEqual(line.lines[0][1].text, "보라")
        self.assertEqual(line.lines[0][2].text, " 9,000개")

    def test_money_platform_shows_amount_as_money(self):
        s = Sticker.from_dict({"type": "mvp", "entries": [["구릭", 10000]]})
        (line,) = s.layout(1920, 1080, StickerState({}, 0, (), "₩", "youtube"))
        self.assertEqual(line.lines[0][2].text, " ₩10,000")
        (line,) = s.layout(1920, 1080, StickerState({}, 0, (), "별풍선", "afreeca"))
        self.assertEqual(line.lines[0][2].text, " 10,000개")

    def test_dynamic_follows_auto(self):
        self.assertTrue(Sticker.from_dict({"type": "mvp"}).dynamic)
        self.assertTrue(Sticker.from_dict({"type": "history"}).dynamic)


class ImageStickerTest(unittest.TestCase):
    def test_size_from_reference_height_and_aspect(self):
        s = Sticker.from_dict({"type": "image", "x": 0.25, "y": 0.5, "height": 240, "aspect": 1.5, "scale": 1,
                               "path": "C:/a.png", "url": "/media/t.png"})
        (img,) = s.layout(1280, 720, EMPTY)
        self.assertEqual(img, ImagePrim(320, 360, 240, 160, "C:/a.png", "/media/t.png"))


if __name__ == "__main__":
    unittest.main()
