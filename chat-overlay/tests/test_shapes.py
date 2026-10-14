import re
import unittest

from chatov.shapes import ring_drawing, rounded_rect_drawing


def pairs(path):
    nums = [int(n) for n in re.findall(r"-?\d+", path)]
    return list(zip(nums[0::2], nums[1::2]))


class RoundedRectTest(unittest.TestCase):
    def test_box_spans_exactly_width_and_height_in_quarter_pixels(self):
        pts = pairs(rounded_rect_drawing(200, 80, 16))
        self.assertEqual((min(x for x, _ in pts), max(x for x, _ in pts)), (0, 800))
        self.assertEqual((min(y for _, y in pts), max(y for _, y in pts)), (0, 320))

    def test_starts_with_move_and_uses_curves_for_corners(self):
        path = rounded_rect_drawing(100, 50, 10)
        self.assertTrue(path.startswith("m 40 0 l 360 0 b "))
        self.assertEqual(path.count("b "), 4)

    def test_radius_is_clamped_to_half_the_short_side(self):
        self.assertEqual(rounded_rect_drawing(100, 20, 50), rounded_rect_drawing(100, 20, 10))

    def test_zero_radius_is_plain_rectangle(self):
        self.assertEqual(rounded_rect_drawing(10, 5, 0), "m 0 0 l 40 0 l 40 20 l 0 20 l 0 0")

    def test_decimal_sizes_round_to_quarter_pixels(self):
        pts = pairs(rounded_rect_drawing(10.3, 5.1, 0))
        self.assertEqual(max(x for x, _ in pts), 41)


class RingTest(unittest.TestCase):
    def test_ring_is_outer_path_plus_reversed_inner_path(self):
        ring = ring_drawing(200, 80, 16, 4)
        outer, inner = ring.split(" m ")
        self.assertEqual(outer, rounded_rect_drawing(200, 80, 16))
        self.assertTrue(inner.startswith("64 16 b "))  # 안쪽은 (4+12, 4)px = (64, 16) 에서 시작해 반대로 돈다

    def test_ring_bounding_box_is_the_outer_box(self):
        pts = pairs(ring_drawing(200, 80, 16, 4))
        self.assertEqual((max(x for x, _ in pts), max(y for _, y in pts)), (800, 320))

    def test_border_too_thick_gives_filled_box(self):
        self.assertEqual(ring_drawing(20, 10, 2, 6), rounded_rect_drawing(20, 10, 2))


if __name__ == "__main__":
    unittest.main()
