import unittest

from chatov.badges import DEFAULT_BADGES, Badge, badge_for, badges_from_settings, nick_hash
from chatov.icons import ICON_NAMES


class NickHashTest(unittest.TestCase):
    def test_fnv1a_32_over_code_points(self):
        # ASCII 는 코드 포인트 = 바이트라서 표준 FNV-1a 값과 같다
        self.assertEqual(nick_hash("a"), 0xE40C292C)
        self.assertEqual(nick_hash("abc"), 0x1A47E90B)
        self.assertEqual(nick_hash(""), 0x811C9DC5)

    def test_korean_and_emoji_are_stable(self):
        self.assertEqual(nick_hash("별빛여우"), nick_hash("별빛여우"))
        self.assertNotEqual(nick_hash("별빛여우"), nick_hash("별빛여후"))
        self.assertTrue(0 <= nick_hash("😀a") < 2 ** 32)


class BadgeForTest(unittest.TestCase):
    def test_same_nick_always_gets_the_same_badge(self):
        nicks = [f"닉{i}" for i in range(50)]
        first = [badge_for(n, DEFAULT_BADGES, {}) for n in nicks]
        self.assertEqual(first, [badge_for(n, DEFAULT_BADGES, {}) for n in nicks])

    def test_share_decides_how_many_nicks_get_each_badge(self):
        nicks = [f"시청자{i}" for i in range(4000)]
        got = [badge_for(n, DEFAULT_BADGES, {}) for n in nicks]
        for b in DEFAULT_BADGES:
            share = sum(1 for g in got if g == b) / len(nicks)
            self.assertAlmostEqual(share, b.share, delta=0.03, msg=b.key)
        none = sum(1 for g in got if g is None) / len(nicks)
        self.assertAlmostEqual(none, 1 - sum(b.share for b in DEFAULT_BADGES), delta=0.03)

    def test_zero_share_means_nobody_and_full_share_means_everybody(self):
        only = (Badge("manager", "매니저", "shield", "#22c55e", 1.0),)
        self.assertTrue(all(badge_for(f"n{i}", only, {}) == only[0] for i in range(30)))
        nobody = (Badge("manager", "매니저", "shield", "#22c55e", 0.0),)
        self.assertTrue(all(badge_for(f"n{i}", nobody, {}) is None for i in range(30)))

    def test_shares_over_100_percent_are_cut(self):
        big = (Badge("manager", "매니저", "shield", "#000", 0.8), Badge("fan", "열혈팬", "heart", "#111", 0.8))
        got = {badge_for(f"n{i}", big, {}) for i in range(300)}
        self.assertNotIn(None, got)

    def test_manual_badge_wins_and_blank_means_no_badge(self):
        only = (Badge("manager", "매니저", "shield", "#22c55e", 1.0), Badge("sub", "구독자", "star", "#ffb300", 0.0))
        self.assertEqual(badge_for("코코넛", only, {"코코넛": "sub"}).key, "sub")
        self.assertIsNone(badge_for("코코넛", only, {"코코넛": ""}))
        self.assertEqual(badge_for("코코넛", only, {"코코넛": "모르는배지"}).key, "manager")


class BadgeSettingsTest(unittest.TestCase):
    def test_default_badges_use_known_icons(self):
        self.assertEqual([b.key for b in DEFAULT_BADGES], ["manager", "fan", "sub"])
        for b in DEFAULT_BADGES:
            self.assertIn(b.icon, ICON_NAMES)
        self.assertIn("shield", ICON_NAMES)

    def test_reads_badges_from_settings_and_ignores_broken_ones(self):
        got = badges_from_settings([{"key": "manager", "label": "매니저", "icon": "crown", "color": "#123456", "share": 0.5},
                                    {"key": "x", "icon": "우주선", "share": "abc"}, "깨짐"])
        self.assertEqual(got[0], Badge("manager", "매니저", "crown", "#123456", 0.5))
        self.assertEqual(got[1].icon, "")
        self.assertEqual(got[1].share, 0.0)
        self.assertEqual(len(got), 2)

    def test_missing_setting_means_default_badges(self):
        self.assertEqual(badges_from_settings(None), DEFAULT_BADGES)


if __name__ == "__main__":
    unittest.main()
