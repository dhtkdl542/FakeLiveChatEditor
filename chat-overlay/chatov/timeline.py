# -*- coding: utf-8 -*-
"""언제 누가 무슨 채팅을 치는지 정하는 타임라인. web/js/core/events.js 와 같은 순서로 난수를 쓴다."""
import math
from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence

from .rng import Mulberry32
from .text import Color, color_for_nick

END_MARGIN = 0.2       # 영상 끝 이 시간 안쪽까지만 채팅을 만든다
PAYLOAD_MARGIN = 0.05  # 브라우저에서 받은 타임라인을 자를 때 여유


@dataclass(frozen=True)
class ChatEvent:
    t: float
    nick: str
    msg: str
    color: str  # #rrggbb
    highlight: bool = False  # 후원처럼 눈에 띄게 그리는 줄


class ShuffledCycle:
    """목록을 섞어서 한 바퀴 다 쓰면 다시 섞는다. 같은 대사가 연달아 나오지 않게."""

    def __init__(self, items: Sequence[str], rng: Mulberry32):
        if not items:
            raise ValueError("목록이 비었습니다.")
        self._items = list(items)
        self._rng = rng
        self._bag: List[str] = []

    def next(self) -> str:
        if not self._bag:
            bag = list(self._items)
            for i in range(len(bag) - 1, 0, -1):
                j = self._rng.below(i + 1)
                bag[i], bag[j] = bag[j], bag[i]
            self._bag = bag
        return self._bag.pop()


def round_ms(t: float) -> float:
    # JS Math.round 과 같은 반올림
    return math.floor(t * 1000 + 0.5) / 1000


class EventGenerator:
    STEP = 0.02  # 속도 곡선을 적분하는 시간 간격(초)

    def __init__(self, curve: Callable[[float], float], nicks: Sequence[str], msgs: Sequence[str],
                 palette: Sequence[str], start: float, interval_min: float, interval_max: float,
                 rng: Mulberry32, msgs_in_order: bool = False):
        self._curve = curve
        self._nicks = ShuffledCycle(nicks, rng)
        self._msgs = ShuffledCycle(msgs, rng)
        self._ordered_msgs = list(msgs) if msgs_in_order else None
        self._palette = list(palette)
        self._start = float(start)
        self._lo = float(interval_min)
        self._hi = max(self._lo, float(interval_max))
        self._rng = rng

    def generate(self, duration: float) -> List[ChatEvent]:
        """다음 채팅까지 '속도 × 시간' 이 랜덤 간격만큼 쌓이면 채팅 하나. 빠른 구간일수록 빨리 쌓인다."""
        events = []
        t = self._start
        while t < duration - END_MARGIN:
            nick = self._nicks.next()
            msg = (self._ordered_msgs[len(events) % len(self._ordered_msgs)]
                   if self._ordered_msgs is not None else self._msgs.next())
            events.append(ChatEvent(round_ms(t), nick, msg, color_for_nick(nick, self._palette)))
            need = self._rng.uniform(self._lo, self._hi)
            while need > 0 and t < duration:
                need -= self._curve(t) * self.STEP
                t += self.STEP
        return events


def events_from_payload(items: Iterable[dict], duration: float) -> List[ChatEvent]:
    try:
        events = [
            ChatEvent(float(d["t"]), str(d["nick"]), str(d["msg"]), Color.parse(d.get("color")).to_hex(),
                      bool(d.get("highlight", False)))
            for d in items
        ]
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"채팅 타임라인 형식이 잘못됐습니다: {e}")
    return sorted((e for e in events if e.t < duration - PAYLOAD_MARGIN), key=lambda e: e.t)
