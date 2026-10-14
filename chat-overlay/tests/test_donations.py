import unittest

from chatov.donations import (Donation, DonationGenerator, alert_opacity, alert_scale, donation_chat_text, format_gift, is_money,
                              donations_from_payload, merge_into_chat, schedule_alerts)
from chatov.rng import Mulberry32
from chatov.timeline import ChatEvent

CFG = {"NICKS": ["별사", "갓스", "워린"], "MSGS": ["화이팅", "오늘 이쁘다"], "COLORS": ["#ff0000", "#00ff00"],
       "CHAT_START": 0.5, "DONATION_EVERY": 10, "DONATION_AMOUNTS": [10, 100, 1000], "DONATION_MSG_CHANCE": 0.5}


class DonationGeneratorTest(unittest.TestCase):
    def test_same_seed_same_donations(self):
        a = DonationGenerator.from_settings(CFG, 7).generate(120)
        self.assertEqual(a, DonationGenerator.from_settings(CFG, 7).generate(120))
        self.assertNotEqual(a, DonationGenerator.from_settings(CFG, 8).generate(120))

    def test_spacing_follows_average_interval(self):
        ds = DonationGenerator.from_settings(CFG, 1).generate(600)
        gaps = [b.t - a.t for a, b in zip(ds, ds[1:])]
        self.assertGreaterEqual(min(gaps), 5 - 1e-6)
        self.assertLessEqual(max(gaps), 15 + 1e-6)
        self.assertLess(ds[-1].t, 600 - 1)

    def test_uses_lists_and_amount_choices(self):
        ds = DonationGenerator.from_settings(CFG, 3).generate(600)
        self.assertTrue(all(d.nick in CFG["NICKS"] for d in ds))
        self.assertTrue(all(d.amount in (10, 100, 1000) for d in ds))
        self.assertTrue(all(d.msg in ("", "화이팅", "오늘 이쁘다") for d in ds))
        self.assertTrue(any(d.msg for d in ds) and any(not d.msg for d in ds))

    def test_small_amounts_are_more_common(self):
        ds = DonationGenerator.from_settings(CFG, 5).generate(3000)
        counts = {a: sum(1 for d in ds if d.amount == a) for a in (10, 100, 1000)}
        self.assertGreater(counts[10], counts[1000])

    def test_off_or_empty_lists_give_nothing(self):
        self.assertEqual(DonationGenerator.from_settings({**CFG, "NICKS": []}, 1).generate(100), [])

    def test_seed_differs_from_chat_seed(self):
        # 채팅과 같은 난수열을 쓰면 후원자 순서가 채팅 순서와 똑같아져서 어색하다
        self.assertEqual(DonationGenerator.donation_seed(1), (1 ^ 0x9E3779B9) & 0xFFFFFFFF)


class PayloadAndChatTest(unittest.TestCase):
    def test_from_payload(self):
        ds = donations_from_payload([{"t": 5, "nick": "별사", "amount": 550, "msg": "와"},
                                     {"t": 1, "nick": "갓스", "amount": 10}], duration=60)
        self.assertEqual(ds, [Donation(1.0, "갓스", 10, ""), Donation(5.0, "별사", 550, "와")])

    def test_chat_text(self):
        self.assertEqual(donation_chat_text(Donation(1, "a", 1550, ""), "하트"), "♥ 하트 1,550개 선물!")
        self.assertEqual(donation_chat_text(Donation(1, "a", 10, "사랑해"), "별풍선"), "♥ 별풍선 10개 선물! 사랑해")

    def test_chat_text_for_money(self):
        self.assertEqual(donation_chat_text(Donation(1, "a", 10000, ""), "₩"), "♥ ₩10,000 후원!")
        self.assertEqual(donation_chat_text(Donation(1, "a", 5000, "굿"), "원"), "♥ 5,000원 후원! 굿")


class FormatGiftTest(unittest.TestCase):
    """후원 금액 표기: 개수형(하트 · 별풍선 · 치즈) 과 돈(₩ · $ · 원)"""

    def test_count_units(self):
        self.assertEqual(format_gift(550, "하트"), "하트 550개")
        self.assertEqual(format_gift(4860, "별풍선"), "별풍선 4,860개")

    def test_currency_symbols_go_in_front(self):
        self.assertEqual(format_gift(10000, "₩"), "₩10,000")
        self.assertEqual(format_gift(5, "$"), "$5")

    def test_won_goes_after(self):
        self.assertEqual(format_gift(3000, "원"), "3,000원")

    def test_blank_unit_falls_back_to_count(self):
        self.assertEqual(format_gift(3, " "), "3개")

    def test_money_detection(self):
        self.assertTrue(is_money("₩"))
        self.assertTrue(is_money("원"))
        self.assertFalse(is_money("하트"))

    def test_merge_inserts_highlighted_rows_in_time_order(self):
        chat = [ChatEvent(1.0, "x", "ㅋㅋ", "#111111"), ChatEvent(3.0, "y", "와", "#222222")]
        merged = merge_into_chat(chat, [Donation(3.0, "별사", 100, "")], ["#ff0000", "#00ff00"], "하트")
        self.assertEqual([e.msg for e in merged], ["ㅋㅋ", "와", "♥ 하트 100개 선물!"])
        self.assertTrue(merged[2].highlight)
        self.assertFalse(merged[0].highlight)
        self.assertEqual(merged[2].nick, "별사")


class AlertScheduleTest(unittest.TestCase):
    def test_alerts_queue_when_donations_overlap(self):
        ds = [Donation(1.0, "a", 10, ""), Donation(2.0, "b", 10, ""), Donation(20.0, "c", 10, "")]
        slots = schedule_alerts(ds, duration=60, show=4.0, gap=0.3)
        self.assertEqual([(s.start, s.end) for s in slots], [(1.0, 5.0), (5.3, 9.3), (20.0, 24.0)])
        self.assertEqual(slots[1].donation.nick, "b")

    def test_alerts_past_the_end_are_dropped(self):
        slots = schedule_alerts([Donation(58.0, "a", 1, ""), Donation(59.0, "b", 1, "")], duration=60, show=4)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0].end, 60)


class AlertAnimationTest(unittest.TestCase):
    def test_pop_in_scale(self):
        self.assertAlmostEqual(alert_scale(-5), 0.7)
        self.assertAlmostEqual(alert_scale(0), 0.7)
        self.assertAlmostEqual(alert_scale(75), 0.89)
        self.assertAlmostEqual(alert_scale(150), 1.08)
        self.assertAlmostEqual(alert_scale(200), 1.04)
        self.assertAlmostEqual(alert_scale(250), 1.0)
        self.assertAlmostEqual(alert_scale(3000), 1.0)

    def test_fade_in_and_out(self):
        self.assertAlmostEqual(alert_opacity(0, 4000), 0)
        self.assertAlmostEqual(alert_opacity(75, 4000), 0.5)
        self.assertAlmostEqual(alert_opacity(2000, 4000), 1)
        self.assertAlmostEqual(alert_opacity(3800, 4000), 0.5)
        self.assertAlmostEqual(alert_opacity(4000, 4000), 0)


if __name__ == "__main__":
    unittest.main()
