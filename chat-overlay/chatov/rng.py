# -*- coding: utf-8 -*-
"""브라우저(web/js/core/rng.js)와 똑같은 수열을 내는 시드 난수."""

_MASK = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return (a * b) & _MASK


class Mulberry32:
    def __init__(self, seed: int):
        self._state = int(seed) & _MASK

    def next(self) -> float:
        self._state = (self._state + 0x6D2B79F5) & _MASK
        t = self._state
        t = _imul(t ^ (t >> 15), t | 1)
        t = (((t + _imul(t ^ (t >> 7), t | 61)) & _MASK) ^ t) & _MASK
        return ((t ^ (t >> 14)) & _MASK) / 4294967296

    def uniform(self, lo: float, hi: float) -> float:
        return lo + self.next() * (hi - lo)

    def below(self, n: int) -> int:
        return int(self.next() * n)
