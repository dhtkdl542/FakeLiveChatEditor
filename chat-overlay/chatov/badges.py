# -*- coding: utf-8 -*-
"""닉네임 배지(매니저 · 열혈팬 · 구독자). 닉네임 해시로 정하므로 같은 닉은 영상 내내 같은 배지(또는 없음).
web/js/core/badges.js 와 같은 계산이다. 실제 플랫폼 배지 그림 대신 직접 그린 도형을 쓴다."""
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

from .icons import ICON_NAMES

FNV_OFFSET, FNV_PRIME = 0x811C9DC5, 16777619


@dataclass(frozen=True)
class Badge:
    key: str
    label: str
    icon: str      # chatov.icons.ICON_NAMES, "" 이면 그리지 않음
    color: str
    share: float   # 이 배지를 받는 닉네임 비율 0 ~ 1


DEFAULT_BADGES: Tuple[Badge, ...] = (
    Badge("manager", "매니저", "shield", "#22c55e", 0.08),
    Badge("fan", "열혈팬", "heart", "#ff4d6d", 0.12),
    Badge("sub", "구독자", "star", "#ffb300", 0.25),
)


def nick_hash(nick: str) -> int:
    """FNV-1a 32비트. 바이트 대신 코드 포인트를 넣어서 JS(for..of + codePointAt)와 같은 값이 나온다."""
    h = FNV_OFFSET
    for ch in nick:
        h = ((h ^ ord(ch)) * FNV_PRIME) & 0xFFFFFFFF
    return h


def badge_for(nick: str, badges: Sequence[Badge], overrides: Mapping[str, str]) -> Optional[Badge]:
    """직접 지정한 배지가 먼저(빈 값 = 없음), 아니면 해시 위치가 들어가는 비율 구간의 배지."""
    by_key = {b.key: b for b in badges}
    if nick in overrides and (overrides[nick] == "" or overrides[nick] in by_key):
        return by_key.get(overrides[nick])
    u = nick_hash(nick) / 2 ** 32
    edge = 0.0
    for b in badges:
        edge += b.share
        if u < edge:
            return b
    return None


def _share(v) -> float:
    try:
        return min(1.0, max(0.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def badges_from_settings(raw) -> Tuple[Badge, ...]:
    if raw is None:
        return DEFAULT_BADGES
    out = []
    for b in raw:
        if not isinstance(b, dict):
            continue
        icon = b.get("icon") or ""
        out.append(Badge(str(b.get("key") or ""), str(b.get("label") or ""), icon if icon in ICON_NAMES else "",
                         b.get("color") or "#ffffff", _share(b.get("share", 0))))
    return tuple(out)
