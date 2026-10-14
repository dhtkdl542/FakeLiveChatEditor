import math
import unittest

from chatov.rng import Mulberry32
from chatov.speed import SpeedCurve, SpeedSection


class Mulberry32Test(unittest.TestCase):
    def test_same_seed_gives_same_sequence(self):
        a, b = Mulberry32(42), Mulberry32(42)
        self.assertEqual([a.next() for _ in range(5)], [b.next() for _ in range(5)])

    def test_different_seeds_differ(self):
        self.assertNotEqual(Mulberry32(1).next(), Mulberry32(2).next())

    def test_values_are_in_unit_interval(self):
        r = Mulberry32(7)
        for _ in range(1000):
            v = r.next()
            self.assertGreaterEqual(v, 0.0)
            self.assertLess(v, 1.0)

    def test_matches_reference_algorithm_first_value(self):
        # 표준 mulberry32(seed=1) 의 첫 값
        self.assertAlmostEqual(Mulberry32(1).next(), 0.6270739405881613, places=12)

    def test_uniform_and_randint_helpers(self):
        r = Mulberry32(3)
        self.assertTrue(2.0 <= r.uniform(2.0, 3.0) < 3.0)
        self.assertIn(r.below(4), range(4))


class SpeedSectionTest(unittest.TestCase):
    def test_weight_is_zero_outside(self):
        s = SpeedSection(2.0, 6.0, 3.0)
        self.assertEqual(s.weight(1.9), 0.0)
        self.assertEqual(s.weight(2.0), 0.0)
        self.assertEqual(s.weight(6.0), 0.0)
        self.assertEqual(s.weight(7.0), 0.0)

    def test_weight_is_full_in_the_middle(self):
        self.assertEqual(SpeedSection(2.0, 6.0, 3.0).weight(4.0), 1.0)

    def test_weight_ramps_smoothly_at_edges(self):
        s = SpeedSection(2.0, 6.0, 3.0)
        # 경계에서 램프(0.6초) 절반 지점은 smoothstep(0.5) = 0.5
        self.assertAlmostEqual(s.weight(2.3), 0.5)
        self.assertAlmostEqual(s.weight(5.7), 0.5)

    def test_short_section_ramp_is_half_its_length(self):
        s = SpeedSection(0.0, 0.4, 2.0)
        self.assertAlmostEqual(s.weight(0.2), 1.0)

    def test_from_dict_rejects_empty_and_clamps_speed(self):
        self.assertIsNone(SpeedSection.from_dict({"start": 3, "end": 3, "speed": 2}))
        s = SpeedSection.from_dict({"start": 1, "end": 2, "speed": 0})
        self.assertEqual(s.speed, SpeedSection.MIN_SPEED)


class SpeedCurveTest(unittest.TestCase):
    PHASES = (0.1, 1.2, 2.3)

    def test_flat_when_no_variation_and_no_sections(self):
        curve = SpeedCurve(amplitude=0, period=8, phases=self.PHASES)
        self.assertEqual([curve(t) for t in (0, 3.3, 100)], [1.0, 1.0, 1.0])

    def test_full_variation_stays_within_quarter_and_four(self):
        curve = SpeedCurve(amplitude=1, period=8, phases=self.PHASES)
        values = [curve(t / 10) for t in range(0, 600)]
        self.assertGreaterEqual(min(values), 0.25 - 1e-9)
        self.assertLessEqual(max(values), 4.0 + 1e-9)
        self.assertGreater(max(values) / min(values), 4)

    def test_wave_formula(self):
        curve = SpeedCurve(amplitude=0.5, period=8, phases=self.PHASES)
        x = 2 * math.pi * 1.0 / 8
        n = (math.sin(x + 0.1) + 0.6 * math.sin(x * 1.87 + 1.2) + 0.3 * math.sin(x * 3.41 + 2.3)) / 1.9
        self.assertAlmostEqual(curve(1.0), 4 ** (0.5 * n))

    def test_section_multiplies_the_wave(self):
        base = SpeedCurve(amplitude=0.5, period=8, phases=self.PHASES)
        fast = SpeedCurve(amplitude=0.5, period=8, phases=self.PHASES, sections=[SpeedSection(2, 6, 3)])
        self.assertAlmostEqual(fast(4.0), base(4.0) * 3)
        self.assertAlmostEqual(fast(10.0), base(10.0))

    def test_from_settings_reads_percentages_and_sections(self):
        curve = SpeedCurve.from_settings({
            "SPEED_VAR": 0, "SPEED_PERIOD": 8, "SPEED_PHASES": [0, 0, 0],
            "SPEED_SECTIONS": [{"start": 1, "end": 3, "speed": 2}, {"start": 5, "end": 5, "speed": 9}],
        })
        self.assertEqual(len(curve.sections), 1)
        self.assertAlmostEqual(curve(2.0), 2.0)

    def test_from_settings_without_phases_picks_random_ones(self):
        curve = SpeedCurve.from_settings({"SPEED_VAR": 0.5})
        self.assertEqual(len(curve.phases), 3)


if __name__ == "__main__":
    unittest.main()
