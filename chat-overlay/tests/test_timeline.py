import unittest

from chatov.rng import Mulberry32
from chatov.speed import SpeedCurve, SpeedSection
from chatov.timeline import ChatEvent, EventGenerator, ShuffledCycle, events_from_payload

FLAT = SpeedCurve(amplitude=0, period=8, phases=(0, 0, 0))


def make_gen(seed=1, curve=FLAT, nicks=("a", "b", "c"), msgs=("x", "y"), lo=0.25, hi=0.7, start=0.5):
    return EventGenerator(curve=curve, nicks=list(nicks), msgs=list(msgs), palette=["#ff0000", "#00ff00"],
                          start=start, interval_min=lo, interval_max=hi, rng=Mulberry32(seed))


class ShuffledCycleTest(unittest.TestCase):
    def test_every_item_appears_once_per_round(self):
        cyc = ShuffledCycle(["a", "b", "c"], Mulberry32(5))
        first, second = [cyc.next() for _ in range(3)], [cyc.next() for _ in range(3)]
        self.assertEqual(sorted(first), ["a", "b", "c"])
        self.assertEqual(sorted(second), ["a", "b", "c"])

    def test_empty_items_rejected(self):
        with self.assertRaises(ValueError):
            ShuffledCycle([], Mulberry32(1))


class EventGeneratorTest(unittest.TestCase):
    def test_ordered_messages_repeat_with_random_gaps(self):
        for seed in (1, 42):
            events = EventGenerator(curve=FLAT, nicks=["a", "b"], msgs=["첫째", "둘째", "셋째"],
                                    palette=["#ff0000"], start=0.5, interval_min=0.25,
                                    interval_max=0.7, rng=Mulberry32(seed), msgs_in_order=True).generate(10)
            self.assertGreater(len(events), 6)
            self.assertEqual([e.msg for e in events],
                             [["첫째", "둘째", "셋째"][i % 3] for i in range(len(events))])
            gaps = [round(b.t - a.t, 3) for a, b in zip(events, events[1:])]
            self.assertGreater(len(set(gaps)), 1)
            self.assertTrue(all(0.25 <= gap <= 0.72 for gap in gaps))

    def test_same_seed_same_timeline(self):
        self.assertEqual(make_gen(9).generate(30), make_gen(9).generate(30))

    def test_first_event_at_start_time(self):
        self.assertEqual(make_gen(start=1.5).generate(10)[0].t, 1.5)

    def test_times_increase_and_stay_before_end(self):
        events = make_gen().generate(20)
        times = [e.t for e in events]
        self.assertEqual(times, sorted(times))
        self.assertLess(times[-1], 20 - 0.2)

    def test_gaps_follow_interval_range_without_variation(self):
        events = make_gen(lo=0.4, hi=0.6).generate(60)
        gaps = [b.t - a.t for a, b in zip(events, events[1:])]
        self.assertGreaterEqual(min(gaps), 0.4 - 1e-6)
        self.assertLessEqual(max(gaps), 0.6 + 0.02 + 1e-6)

    def test_fast_section_packs_more_chats(self):
        fast = SpeedCurve(amplitude=0, period=8, phases=(0, 0, 0), sections=(SpeedSection(10, 20, 3),))
        count = lambda evs, a, b: sum(1 for e in evs if a <= e.t < b)
        normal, boosted = make_gen(curve=FLAT).generate(30), make_gen(curve=fast).generate(30)
        self.assertGreater(count(boosted, 11, 19), count(normal, 11, 19) * 2.4)

    def test_slow_section_spreads_chats(self):
        slow = SpeedCurve(amplitude=0, period=8, phases=(0, 0, 0), sections=(SpeedSection(10, 20, 0.25),))
        count = lambda evs, a, b: sum(1 for e in evs if a <= e.t < b)
        self.assertLess(count(make_gen(curve=slow).generate(30), 11, 19),
                        count(make_gen(curve=FLAT).generate(30), 11, 19) / 2.5)

    def test_events_use_lists_and_nick_colors(self):
        for e in make_gen().generate(10):
            self.assertIn(e.nick, ("a", "b", "c"))
            self.assertIn(e.msg, ("x", "y"))
            self.assertEqual(e.color, "#ff0000" if (ord(e.nick) % 2 == 0) else "#00ff00")

    def test_times_are_rounded_to_milliseconds(self):
        for e in make_gen().generate(10):
            self.assertAlmostEqual(e.t * 1000, round(e.t * 1000), places=6)


class EventsFromPayloadTest(unittest.TestCase):
    def test_parses_sorts_and_drops_late_events(self):
        events = events_from_payload([
            {"t": 2, "nick": "b", "msg": "2", "color": "#00ff00"},
            {"t": 1, "nick": "a", "msg": "1", "color": "&H000000FF"},
            {"t": 9.99, "nick": "c", "msg": "late", "color": "#fff"},
        ], duration=10)
        self.assertEqual(events, [ChatEvent(1.0, "a", "1", "#ff0000"), ChatEvent(2.0, "b", "2", "#00ff00")])

    def test_bad_items_raise_value_error(self):
        with self.assertRaises(ValueError):
            events_from_payload([{"t": "soon"}], duration=10)


if __name__ == "__main__":
    unittest.main()
