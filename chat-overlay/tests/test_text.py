import unittest

from chatov.text import Color, color_for_nick, wrap_text


class WrapTextTest(unittest.TestCase):
    def test_short_text_stays_on_one_line(self):
        self.assertEqual(wrap_text("ㅋㅋㅋ", 10), ["ㅋㅋㅋ"])

    def test_long_text_is_cut_every_max_chars(self):
        self.assertEqual(wrap_text("가나다라마바사아", 4), ["가나다라", "마바사아"])

    def test_remainder_goes_to_last_line(self):
        self.assertEqual(wrap_text("가나다라마", 4), ["가나다라", "마"])

    def test_max_chars_never_below_four(self):
        self.assertEqual(wrap_text("가나다라마", 1), ["가나다라", "마"])

    def test_empty_text_gives_one_empty_line(self):
        self.assertEqual(wrap_text("", 10), [""])


class ColorTest(unittest.TestCase):
    def test_hex_is_converted_to_ass_bgr(self):
        self.assertEqual(Color.parse("#47b3ff").to_ass(), "&H00FFB347")

    def test_short_hex_is_expanded(self):
        self.assertEqual(Color.parse("#fa0").to_ass(), "&H0000AAFF")

    def test_ass_value_round_trips(self):
        self.assertEqual(Color.parse("&H00FFB347").to_ass(), "&H00FFB347")

    def test_invalid_value_falls_back_to_white(self):
        self.assertEqual(Color.parse("banana").to_ass(), "&H00FFFFFF")
        self.assertEqual(Color.parse(None).to_ass(), "&H00FFFFFF")

    def test_hex_output(self):
        self.assertEqual(Color.parse("&H00FFB347").to_hex(), "#47b3ff")


class ColorForNickTest(unittest.TestCase):
    def test_same_nick_always_gets_same_color(self):
        palette = ["#ff0000", "#00ff00", "#0000ff"]
        self.assertEqual(color_for_nick("ㅇㅇ", palette), color_for_nick("ㅇㅇ", palette))

    def test_color_is_picked_by_sum_of_code_points(self):
        palette = ["#000001", "#000002", "#000003"]
        # "ab" = 97 + 98 = 195, 195 % 3 = 0
        self.assertEqual(color_for_nick("ab", palette), "#000001")

    def test_empty_palette_gives_white(self):
        self.assertEqual(color_for_nick("x", []), "#ffffff")


if __name__ == "__main__":
    unittest.main()
