# -*- coding: utf-8 -*-
"""시간에 따른 채팅 속도 배율. web/js/core/speed.js 와 같은 식을 쓴다."""
import math
import random
from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple


@dataclass(frozen=True)
class SpeedSection:
    """특정 구간만 채팅을 빠르게(>1) 또는 느리게(<1) 한다."""
    start: float
    end: float
    speed: float

    RAMP = 0.6        # 경계에서 속도가 서서히 바뀌는 시간(초)
    MIN_SPEED = 0.05

    @classmethod
    def from_dict(cls, d: dict) -> Optional["SpeedSection"]:
        start, end = float(d["start"]), float(d["end"])
        if end <= start:
            return None
        return cls(start, end, max(cls.MIN_SPEED, float(d["speed"])))

    def weight(self, t: float) -> float:
        """구간 안에서 0→1→0 으로 부드럽게 변하는 가중치 (smoothstep)."""
        if t <= self.start or t >= self.end:
            return 0.0
        ramp = min(self.RAMP, (self.end - self.start) / 2)
        w = min(1.0, (t - self.start) / ramp, (self.end - t) / ramp)
        return w * w * (3 - 2 * w)


@dataclass(frozen=True)
class SpeedCurve:
    """여러 사인파를 섞은 출렁임 × 구간 배율."""
    amplitude: float                      # 0 ~ 1
    period: float                         # 초
    phases: Tuple[float, float, float]
    sections: Sequence[SpeedSection] = field(default_factory=tuple)

    RANGE = 4.0  # 출렁임 100%일 때 1/4배 ~ 4배

    @classmethod
    def from_settings(cls, cfg: dict, rnd: random.Random = random) -> "SpeedCurve":
        phases = cfg.get("SPEED_PHASES")
        if not (isinstance(phases, (list, tuple)) and len(phases) == 3):
            phases = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
        sections = [SpeedSection.from_dict(s) for s in cfg.get("SPEED_SECTIONS") or []]
        return cls(
            amplitude=min(1.0, max(0.0, float(cfg.get("SPEED_VAR", 0)))),
            period=max(1.0, float(cfg.get("SPEED_PERIOD", 8))),
            phases=tuple(float(p) for p in phases),
            sections=tuple(s for s in sections if s),
        )

    def wave(self, t: float) -> float:
        if self.amplitude <= 0:
            return 1.0
        p = self.phases
        x = 2 * math.pi * t / self.period
        n = (math.sin(x + p[0]) + 0.6 * math.sin(x * 1.87 + p[1]) + 0.3 * math.sin(x * 3.41 + p[2])) / 1.9
        return self.RANGE ** (self.amplitude * n)

    def __call__(self, t: float) -> float:
        s = self.wave(t)
        for sec in self.sections:
            w = sec.weight(t)
            if w > 0:
                s *= sec.speed ** w
        return s
