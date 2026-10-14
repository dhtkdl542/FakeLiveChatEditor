# -*- coding: utf-8 -*-
"""가짜 후원: 언제 누가 얼마를 보내는지 만들고, 채팅창에 강조 줄로 넣고, 알림 띠의 일정과 움직임을 정한다.
web/js/core/donations.js 와 같은 순서로 난수를 쓴다."""
import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .rng import Mulberry32
from .text import color_for_nick
from .timeline import ChatEvent, ShuffledCycle, round_ms

DEFAULT_AMOUNTS = (10, 30, 50, 100, 300, 550, 1000)
SEED_MIX = 0x9E3779B9


@dataclass(frozen=True)
class Donation:
    t: float
    nick: str
    amount: int
    msg: str


class DonationGenerator:
    def __init__(self, nicks: Sequence[str], msgs: Sequence[str], every: float, amounts: Sequence[int],
                 msg_chance: float, start: float, rng: Mulberry32):
        self._nicks, self._msgs = list(nicks), list(msgs)
        self._every = max(1.0, float(every))
        self._amounts = [int(a) for a in amounts] or list(DEFAULT_AMOUNTS)
        self._chance = float(msg_chance)
        self._start = float(start)
        self._rng = rng

    @staticmethod
    def donation_seed(seed: int) -> int:
        return (int(seed) ^ SEED_MIX) & 0xFFFFFFFF

    @classmethod
    def from_settings(cls, cfg: dict, seed: int) -> "DonationGenerator":
        return cls(cfg.get("NICKS") or [], cfg.get("MSGS") or [], cfg.get("DONATION_EVERY", 15),
                   cfg.get("DONATION_AMOUNTS") or DEFAULT_AMOUNTS, cfg.get("DONATION_MSG_CHANCE", 0.4),
                   cfg.get("CHAT_START", 0.5), Mulberry32(cls.donation_seed(seed)))

    def _gap(self) -> float:
        return self._every * self._rng.uniform(0.5, 1.5)

    def generate(self, duration: float) -> List[Donation]:
        if not self._nicks:
            return []
        nicks = ShuffledCycle(self._nicks, self._rng)
        msgs = ShuffledCycle(self._msgs, self._rng) if self._msgs else None
        out = []
        t = self._start + self._gap()
        while t < duration - 1:
            nick = nicks.next()
            # 제곱해서 작은 금액이 더 자주 나오게
            amount = self._amounts[min(len(self._amounts) - 1, int(self._rng.next() ** 2 * len(self._amounts)))]
            msg = msgs.next() if msgs and self._rng.next() < self._chance else ""
            out.append(Donation(round_ms(t), nick, amount, msg))
            t += self._gap()
        return out


def donations_from_payload(items: Iterable[dict], duration: float) -> List[Donation]:
    try:
        ds = [Donation(float(d["t"]), str(d["nick"]), int(d["amount"]), str(d.get("msg") or "")) for d in items]
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"후원 목록 형식이 잘못됐습니다: {e}")
    return sorted((d for d in ds if d.t < duration), key=lambda d: d.t)


CURRENCY_PREFIX = ("₩", "$", "¥", "€", "£")


def is_money(unit: str) -> bool:
    u = (unit or "").strip()
    return u in CURRENCY_PREFIX or u == "원"


def format_gift(amount: int, unit: str) -> str:
    """'하트 550개' · '별풍선 4,860개' 처럼 개수로, 또는 '₩10,000' · '3,000원' 처럼 돈으로."""
    u = (unit or "").strip()
    if u in CURRENCY_PREFIX:
        return f"{u}{amount:,}"
    if u == "원":
        return f"{amount:,}원"
    return f"{u} {amount:,}개" if u else f"{amount:,}개"


def donation_chat_text(d: Donation, unit: str) -> str:
    text = f"♥ {format_gift(d.amount, unit)} {'후원' if is_money(unit) else '선물'}!"
    return f"{text} {d.msg}" if d.msg else text


def merge_into_chat(events: Sequence[ChatEvent], donations: Sequence[Donation], palette: Sequence[str],
                    unit: str) -> List[ChatEvent]:
    """후원을 채팅창에 강조 줄로 끼워 넣는다. 같은 시각이면 일반 채팅 다음."""
    rows = [(e.t, 0, e) for e in events] + [
        (d.t, 1, ChatEvent(d.t, d.nick, donation_chat_text(d, unit), color_for_nick(d.nick, palette), True))
        for d in donations]
    return [e for _, _, e in sorted(rows, key=lambda r: (r[0], r[1]))]


@dataclass(frozen=True)
class AlertSlot:
    start: float
    end: float
    donation: Donation


def schedule_alerts(donations: Sequence[Donation], duration: float, show: float = 4.0,
                    gap: float = 0.3) -> List[AlertSlot]:
    """알림 띠는 한 번에 하나. 앞 알림이 끝나기 전에 후원이 오면 줄을 서서 기다린다."""
    slots, free_at = [], -math.inf
    for d in donations:
        start = round_ms(max(d.t, free_at + gap))
        if start >= duration:
            break
        end = round_ms(min(start + show, duration))
        slots.append(AlertSlot(start, end, d))
        free_at = end
    return slots


POP_MS, SETTLE_MS = 150, 250
POP_FROM, POP_PEAK = 0.7, 1.08
FADE_IN_MS, FADE_OUT_MS = 150, 400


def alert_scale(ms: float) -> float:
    """튀어나오는 크기: 70% → 108% (0~150ms) → 100% (150~250ms). ASS \\t 와 같은 직선 보간."""
    if ms <= 0:
        return POP_FROM
    if ms < POP_MS:
        return POP_FROM + (POP_PEAK - POP_FROM) * ms / POP_MS
    if ms < SETTLE_MS:
        return POP_PEAK + (1 - POP_PEAK) * (ms - POP_MS) / (SETTLE_MS - POP_MS)
    return 1.0


def alert_opacity(ms: float, dur_ms: float) -> float:
    return max(0.0, min(1.0, ms / FADE_IN_MS, (dur_ms - ms) / FADE_OUT_MS))
