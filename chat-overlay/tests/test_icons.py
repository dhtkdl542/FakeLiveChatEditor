import re
import unittest

from chatov.icons import ICON_NAMES, icon_drawing, icon_shape, icon_width


def numbers(path):
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path)]


class IconShapeTest(unittest.TestCase):
    def test_available_icons(self):
        self.assertEqual(ICON_NAMES, ("circle", "rounded", "heart", "star", "crown", "diamond"))

    def test_every_shape_fills_height_and_starts_at_left(self):
        # libass 는 드로잉의 아래쪽을 글자 기준선에 맞추므로, 모든 모양이 세로 0~100 을 꽉 채워야 미리보기와 같다
        for name in ICON_NAMES:
            nums = numbers(icon_shape(name).path)
            xs, ys = nums[0::2], nums[1::2]
            self.assertAlmostEqual(min(ys), 0, places=1, msg=name)
            self.assertAlmostEqual(max(ys), 100, places=1, msg=name)
            self.assertAlmostEqual(min(xs), 0, places=1, msg=name)
            self.assertAlmostEqual(max(xs), icon_shape(name).width, places=1, msg=name)

    def test_drawing_is_scaled_to_pixels_with_quarter_pixel_precision(self):
        drawing = icon_drawing("diamond", 20)
        self.assertTrue(drawing.startswith("m "))
        nums = numbers(drawing)
        self.assertTrue(all(n == int(n) for n in nums))
        self.assertEqual(max(nums[1::2]), 80)  # 20px × 4 (\p3)

    def test_width_in_pixels(self):
        self.assertAlmostEqual(icon_width("circle", 20), 20)
        self.assertGreater(icon_width("heart", 20), 0)

    def test_unknown_icon_draws_nothing(self):
        self.assertEqual(icon_drawing("", 20), "")
        self.assertEqual(icon_drawing("banana", 20), "")
        self.assertEqual(icon_width("banana", 20), 0)


if __name__ == "__main__":
    unittest.main()
