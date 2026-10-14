# -*- coding: utf-8 -*-
"""방송 화면 스티커(글자 스티커, 순위판, 목표 게이지, 배너, 후원 알림, 그림)를 기본 도형 목록으로 바꾼다.
같은 도형 목록을 결과 영상(ASS + ffmpeg)과 미리보기(web/js/core/stickers.js)가 각각 그린다.

위치는 화면 비율(x, y = 0~1, 스티커 가운데), 크기는 1080p 기준 px 에 scale 을 곱해서 영상 높이에 맞춘다."""
import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple, Union

from .donations import Donation, format_gift, is_money
from .text import wrap_text

REF_H = 1080
CHAT_LAYER = 10


def r2(v: float) -> float:
    return math.floor(v * 100 + 0.5) / 100


@dataclass(frozen=True)
class Run:
    text: str
    size: float
    color: str
    bold: bool
    font: str


@dataclass(frozen=True)
class TextPrim:
    x: float
    y: float           # 글자 줄(들)의 세로 가운데
    align: str         # left | center | right  (x 가 글자의 왼쪽 / 가운데 / 오른쪽)
    lines: Tuple[Tuple[Run, ...], ...]
    outline_w: float
    outline_color: str
    layer: int


@dataclass(frozen=True)
class RectPrim:
    cx: float
    cy: float
    w: float
    h: float
    r: float
    color: str
    opacity: float
    border_w: float
    border_color: str
    layer: int


@dataclass(frozen=True)
class ImagePrim:
    cx: float
    cy: float
    w: float
    h: float
    path: str
    url: str


Prim = Union[TextPrim, RectPrim, ImagePrim]


@dataclass(frozen=True)
class StickerState:
    """지금까지 들어온 후원 합계 (순위판 · 목표 게이지가 따라 움직인다)."""
    totals: Dict[str, int]
    total: int
    donations: Tuple[Donation, ...] = ()
    unit: str = "하트"        # 플랫폼 후원 단위 (스티커 단위가 비어 있으면 이걸 쓴다)
    platform: str = "panda"   # 후원창 모양을 고르는 기준

    @classmethod
    def at(cls, donations: Sequence[Donation], t: float, unit: str = "하트", platform: str = "panda") -> "StickerState":
        totals: Dict[str, int] = {}
        arrived = tuple(d for d in donations if d.t <= t)
        for d in arrived:
            totals[d.nick] = totals.get(d.nick, 0) + d.amount
        return cls(totals, sum(totals.values()), arrived, unit, platform)


def _text(x, y, align, runs, layer=2, outline_w=0.0, outline_color="", extra_lines=()) -> TextPrim:
    return TextPrim(r2(x), r2(y), align, (tuple(runs),) + tuple(tuple(l) for l in extra_lines),
                    r2(outline_w), outline_color, layer)


class Sticker:
    TYPES: Dict[str, type] = {}
    DEFAULTS: Dict[str, object] = {"x": 0.5, "y": 0.5, "scale": 1.0}

    def __init_subclass__(cls, kind: str = "", **kw):
        super().__init_subclass__(**kw)
        if kind:
            Sticker.TYPES[kind] = cls

    def __init__(self, d: dict):
        merged = {**Sticker.DEFAULTS, **self.DEFAULTS, **{k: v for k, v in d.items() if v is not None}}
        for key, default in {**Sticker.DEFAULTS, **self.DEFAULTS}.items():
            value = merged[key]
            if isinstance(default, bool):
                value = bool(value)
            elif isinstance(default, (int, float)) and not isinstance(default, bool):
                value = float(value)
            setattr(self, _snake(key), value)

    @classmethod
    def from_dict(cls, d: dict) -> "Sticker":
        kind = d.get("type", "")
        if kind not in Sticker.TYPES:
            raise ValueError(f"모르는 스티커 종류: {kind}")
        return Sticker.TYPES[kind](d)

    dynamic = False

    def k(self, height: float) -> float:
        return height / REF_H * self.scale

    def center(self, width: float, height: float):
        return self.x * width, self.y * height

    def layout(self, width: float, height: float, state: StickerState) -> List[Prim]:
        raise NotImplementedError


def _snake(name: str) -> str:
    return "".join("_" + c.lower() if c.isupper() else c for c in name)


class TextSticker(Sticker, kind="text"):
    """'별사♡' 같은 닉네임 스티커: 파스텔 글자 + 안쪽 흰 테두리 + 바깥 진한 테두리"""
    DEFAULTS = {"text": "별사", "heart": True, "font": "Malgun Gothic", "size": 56, "fill": "#b07cff",
                "inner": "#ffffff", "outer": "#6a3fb5", "innerWidth": 6, "outerWidth": 3, "heartColor": "#ff5fa2",
                "x": 0.1}
    HEART_EM = 0.7

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        runs = [Run(self.text, r2(self.size * k), self.fill, True, self.font)]
        if self.heart:
            runs.append(Run("♡", r2(self.size * k * self.HEART_EM), self.heart_color, True, self.font))
        return [
            _text(cx, cy, "center", runs, 2, (self.inner_width + self.outer_width) * k, self.outer),
            _text(cx, cy, "center", runs, 3, self.inner_width * k, self.inner),
        ]


PANEL = {"font": "Malgun Gothic", "bg": "#ffffff", "bgOpacity": 0.92, "borderWidth": 2, "borderColor": "#ff5fa2",
         "accent": "#ff5fa2", "textColor": "#333333", "radius": 14}


class PanelSticker(Sticker):
    def box(self, cx, cy, w, h, k, layer=0) -> RectPrim:
        return RectPrim(r2(cx), r2(cy), r2(w), r2(h), r2(self.radius * k), self.bg, self.bg_opacity,
                        r2(self.border_width * k), self.border_color, layer)

    def run(self, text, size, k, color=None, bold=False) -> Run:
        return Run(text, r2(size * k), color or self.text_color, bold, self.font)


class RankingSticker(PanelSticker, kind="ranking"):
    DEFAULTS = {**PANEL, "title": "오늘의 후원 순위", "rows": 5, "width": 300, "auto": True, "x": 0.86, "y": 0.35,
                "entries": [["별사", 6558], ["갓스", 5326], ["워린", 1452], ["소다", 1080], ["뭉치", 655]]}
    P, TH, RH, T, R, NICK_X = 14, 38, 30, 22, 18, 52

    @property
    def dynamic(self):
        return self.auto

    def standings(self, state: StickerState) -> List[Tuple[str, int]]:
        totals: Dict[str, int] = {}
        for nick, amount in self.entries:
            totals[str(nick)] = totals.get(str(nick), 0) + int(amount)
        if self.auto:
            for nick, amount in state.totals.items():
                totals[nick] = totals.get(nick, 0) + amount
        return sorted(totals.items(), key=lambda kv: -kv[1])[: int(self.rows)]

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        rows = self.standings(state)
        w, h = self.width * k, (2 * self.P + self.TH + len(rows) * self.RH) * k
        left, top, right = cx - w / 2, cy - h / 2, cx + w / 2
        prims: List[Prim] = [self.box(cx, cy, w, h, k),
                             _text(left + self.P * k, top + (self.P + self.TH / 2) * k, "left",
                                   [self.run(self.title, self.T, k, self.accent, True)])]
        for i, (nick, amount) in enumerate(rows):
            y = top + (self.P + self.TH + self.RH * i + self.RH / 2) * k
            prims += [_text(left + self.P * k, y, "left", [self.run(f"{i + 1}등", self.R, k, self.accent, True)]),
                      _text(left + (self.P + self.NICK_X) * k, y, "left", [self.run(nick, self.R, k)]),
                      _text(right - self.P * k, y, "right", [self.run(f"{amount:,}", self.R, k, bold=True)])]
        return prims


class GoalSticker(PanelSticker, kind="goal"):
    DEFAULTS = {**PANEL, "title": "오늘의 하트 목표", "current": 16719, "target": 38000, "width": 320, "auto": True,
                "track": "#f3d3e2", "x": 0.86, "y": 0.07}
    P, TR, G, B, T, V = 14, 30, 8, 16, 20, 16

    @property
    def dynamic(self):
        return self.auto

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        current = int(self.current) + (state.total if self.auto else 0)
        target = max(1, int(self.target))
        w, h = self.width * k, (2 * self.P + self.TR + self.G + self.B) * k
        left, top, right = cx - w / 2, cy - h / 2, cx + w / 2
        title_y = top + (self.P + self.TR / 2) * k
        bar_y = top + (self.P + self.TR + self.G + self.B / 2) * k
        track_w, bar_h = (self.width - 2 * self.P) * k, self.B * k
        prims: List[Prim] = [
            self.box(cx, cy, w, h, k),
            _text(left + self.P * k, title_y, "left", [self.run(self.title, self.T, k, self.accent, True)]),
            _text(right - self.P * k, title_y, "right",
                  [self.run(f"{current:,} / {target:,} ({math.floor(current / target * 100)}%)", self.V, k, bold=True)]),
            RectPrim(r2(cx), r2(bar_y), r2(track_w), r2(bar_h), r2(bar_h / 2), self.track, 1.0, 0.0, "", 1),
        ]
        fill_w = track_w * min(1.0, current / target)
        if fill_w > 0:
            prims.append(RectPrim(r2(left + self.P * k + fill_w / 2), r2(bar_y), r2(fill_w), r2(bar_h),
                                  r2(min(bar_h, fill_w) / 2), self.accent, 1.0, 0.0, "", 2))
        return prims


class BannerSticker(PanelSticker, kind="banner"):
    DEFAULTS = {**PANEL, "lines": ["방송시간", "오후 1시 ~ 5시", "BJ닉네임"], "width": 260, "x": 0.11, "y": 0.14}
    P, FIRST, OTHER, LH = 12, 30, 22, 1.35

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        lines = [str(l) for l in self.lines if str(l).strip()] or [" "]
        sizes = [self.FIRST if i == 0 else self.OTHER for i in range(len(lines))]
        h = (2 * self.P + sum(s * self.LH for s in sizes)) * k
        top = cy - h / 2
        prims: List[Prim] = [self.box(cx, cy, self.width * k, h, k)]
        y = top + self.P * k
        for i, (line, size) in enumerate(zip(lines, sizes)):
            lh = size * self.LH * k
            prims.append(_text(cx, y + lh / 2, "center",
                               [self.run(line, size, k, self.accent if i == 0 else None, i == 0)]))
            y += lh
        return prims


class TableSticker(PanelSticker, kind="table"):
    """엑셀방송의 '엑셀 표'. 후원이 오면 멤버 한 명의 점수가 오르고 다시 정렬된다."""
    DEFAULTS = {**PANEL, "title": "BJ 엑셀", "headers": ["BJ", "별풍점수", "기여도"], "rows": 10, "auto": True,
                "width": 360, "highlightRow": 1, "showTotal": True, "headerBg": "#f6c344", "headerText": "#222222",
                "titleBg": "#222222", "titleText": "#f6c344", "cellBg": "#ffffff", "cellText": "#222222",
                "grid": "#3a3a3a", "highlight": "#ffb6d9", "totalBg": "#fff3c4", "bgOpacity": 0.95,
                "x": 0.83, "y": 0.3,
                "entries": [["소야", 87399], ["요아정", 77239], ["미키", 50000], ["린린", 30196], ["선유", 20217],
                            ["하늘", 15410], ["다온", 9850], ["채리", 7300], ["루비", 4120], ["보라", 1900]]}
    TITLE, HDR, RH, F, HF, TF, PAD, GRID, BORDER, RADIUS = 30, 28, 26, 15, 15, 18, 8, 1, 1.5, 4
    COLS = (0.42, 0.30, 0.28)

    @property
    def dynamic(self):
        return self.auto

    @staticmethod
    def member_for(nick: str, amount: int, n: int) -> int:
        """후원받는 멤버: 후원자 닉 글자 코드 합 + 금액 으로 정한다 (미리보기와 결과 영상이 같게)."""
        return (sum(ord(c) for c in nick) + int(amount)) % n

    def standings(self, state: StickerState) -> Tuple[List[Tuple[str, int]], int]:
        scores: Dict[str, int] = {}
        for name, score in self.entries:
            scores[str(name)] = scores.get(str(name), 0) + int(score)
        names = [str(n) for n, _ in self.entries]
        if self.auto and names:
            for d in state.donations:
                name = names[self.member_for(d.nick, d.amount, len(names))]
                scores[name] += d.amount
        total = sum(scores.values())
        return sorted(scores.items(), key=lambda kv: -kv[1])[: int(self.rows)], total

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        rows, total = self.standings(state)
        n = len(rows) + (1 if self.show_total else 0)
        th = self.TITLE if self.title else 0
        w, h = self.width * k, (th + self.HDR + n * self.RH) * k
        left, top, right = cx - w / 2, cy - h / 2, cx + w / 2
        row_y = lambda i: top + (th + self.HDR + self.RH * i + self.RH / 2) * k
        band = lambda y, hh, color: RectPrim(r2(cx), r2(y), r2(w), r2(hh), 0.0, color, self.bg_opacity, 0.0, "", 1)
        line = lambda x, y, lw, lh: RectPrim(r2(x), r2(y), r2(lw), r2(lh), 0.0, self.grid, 1.0, 0.0, "", 2)
        cell = lambda text, x, y, align, color, size, bold: TextPrim(
            r2(x), r2(y), align, ((Run(text, r2(size * k), color, bold, self.font),),), 0.0, "", 3)

        prims: List[Prim] = [RectPrim(r2(cx), r2(cy), r2(w), r2(h), r2(self.RADIUS * k), self.cell_bg, self.bg_opacity,
                                      r2(self.BORDER * k), self.grid, 0)]
        if th:
            prims.append(band(top + th * k / 2, th * k, self.title_bg))
        prims.append(band(top + (th + self.HDR / 2) * k, self.HDR * k, self.header_bg))
        hr = int(self.highlight_row)
        if 1 <= hr <= len(rows):
            prims.append(band(row_y(hr - 1), self.RH * k, self.highlight))
        if self.show_total:
            prims.append(band(row_y(len(rows)), self.RH * k, self.total_bg))
        # 칸막이: 가로줄(제목 아래 · 머리줄 아래 · 줄 사이) + 세로줄(칸 사이)
        if th:
            prims.append(line(cx, top + th * k, w, self.GRID * k))
        for i in range(n):
            prims.append(line(cx, top + (th + self.HDR + self.RH * i) * k, w, self.GRID * k))
        body_h = (self.HDR + n * self.RH) * k
        edge = 0.0
        for frac in self.COLS[:-1]:
            edge += frac
            prims.append(line(left + w * edge, top + th * k + body_h / 2, self.GRID * k, body_h))

        if th:
            prims.append(cell(self.title, cx, top + th * k / 2, "center", self.title_text, self.TF, True))
        header_y = top + (th + self.HDR / 2) * k
        start = 0.0
        headers = (list(self.headers) + ["", "", ""])[:3]
        for frac, label in zip(self.COLS, headers):
            prims.append(cell(str(label), left + w * (start + frac / 2), header_y, "center", self.header_text, self.HF, True))
            start += frac
        score_x = left + w * (self.COLS[0] + self.COLS[1]) - self.PAD * k
        for i, (name, score) in enumerate(rows):
            share = math.floor(score * 1000 / total + 0.5) / 10 if total else 0.0
            y = row_y(i)
            prims += [cell(name, left + self.PAD * k, y, "left", self.cell_text, self.F, False),
                      cell(f"{score:,}", score_x, y, "right", self.cell_text, self.F, False),
                      cell(f"{share:.1f}%", right - self.PAD * k, y, "right", self.cell_text, self.F, False)]
        if self.show_total:
            y = row_y(len(rows))
            prims += [cell("총합", left + self.PAD * k, y, "left", self.cell_text, self.F, True),
                      cell(f"{total:,}", score_x, y, "right", self.cell_text, self.F, True),
                      cell("100%", right - self.PAD * k, y, "right", self.cell_text, self.F, True)]
        return prims


class HistorySticker(PanelSticker, kind="history"):
    """아프리카TV 식 후원 카드 더미. 큰 숫자 카드가 세로로 쌓이고 새 후원이 맨 위에 온다."""
    DEFAULTS = {**PANEL, "unit": "", "count": 4, "width": 200, "auto": True, "bgOpacity": 0.95,
                "borderWidth": 3, "x": 0.085, "y": 0.42,
                "entries": [["구릭", 4860], ["구릭", 1000], ["채원♥익", 2871], ["채원♥익", 2514]]}
    CH, GAP, NUM, NICK, CAP, NUM_Y, NICK_Y, CAP_Y, INNER, OUTER = 108, 10, 46, 15, 13, 41, 76, 94, 5, 2
    TIERS = ((1000, "#ff3b5c"), (500, "#ff8a00"), (100, "#2f80ff"), (0, "#20b26b"))

    @property
    def dynamic(self):
        return self.auto

    @classmethod
    def tier_color(cls, amount: int) -> str:
        return next(color for limit, color in cls.TIERS if amount >= limit)

    def cards(self, state: StickerState) -> List[Tuple[str, int]]:
        recent = [(d.nick, d.amount) for d in reversed(state.donations)] if self.auto else []
        base = [(str(n), int(a)) for n, a in self.entries]
        return (recent + base)[: int(self.count)]

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        cards = self.cards(state)
        unit = self.unit or state.unit
        caption = lambda amount: f"{format_gift(amount, unit)} {'후원' if is_money(unit) else '선물'}!"
        h = (len(cards) * self.CH + max(0, len(cards) - 1) * self.GAP) * k
        top = cy - h / 2
        prims: List[Prim] = []
        for i, (nick, amount) in enumerate(cards):
            card_top = top + i * (self.CH + self.GAP) * k
            color = self.tier_color(amount)
            num = [Run(str(amount), r2(self.NUM * k), color, True, self.font)]
            num_y = card_top + self.NUM_Y * k
            prims += [
                RectPrim(r2(cx), r2(card_top + self.CH * k / 2), r2(self.width * k), r2(self.CH * k),
                         r2(self.radius * k), self.bg, self.bg_opacity, r2(self.border_width * k), color, 0),
                _text(cx, num_y, "center", num, 2, (self.INNER + self.OUTER) * k, "#333333"),
                _text(cx, num_y, "center", num, 3, self.INNER * k, "#ffffff"),
                _text(cx, card_top + self.NICK_Y * k, "center", [self.run(nick, self.NICK, k, None, True)]),
                _text(cx, card_top + self.CAP_Y * k, "center", [self.run(caption(amount), self.CAP, k)]),
            ]
        return prims


class MvpSticker(Sticker, kind="mvp"):
    """'MVP 구릭 8,132개' 처럼 가장 많이 후원한 사람"""
    DEFAULTS = {"label": "MVP", "entries": [["구릭", 8132]], "auto": True, "size": 26, "font": "Malgun Gothic",
                "labelColor": "#ffd200", "nickColor": "#ffffff", "amountColor": "#ffd200", "outline": "#111111",
                "outlineWidth": 3, "x": 0.86, "y": 0.04}

    @property
    def dynamic(self):
        return self.auto

    def top(self, state: StickerState) -> Tuple[str, int]:
        totals: Dict[str, int] = {}
        for nick, amount in self.entries:
            totals[str(nick)] = totals.get(str(nick), 0) + int(amount)
        if self.auto:
            for nick, amount in state.totals.items():
                totals[nick] = totals.get(nick, 0) + amount
        return max(totals.items(), key=lambda kv: kv[1]) if totals else ("", 0)

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        nick, amount = self.top(state)
        size = r2(self.size * k)
        runs = [Run(f"{self.label} ", size, self.label_color, True, self.font),
                Run(nick, size, self.nick_color, True, self.font),
                Run(" " + (format_gift(amount, state.unit) if is_money(state.unit) else f"{amount:,}개"),
                    size, self.amount_color, True, self.font)]
        return [_text(cx, cy, "center", runs, 2, self.outline_width * k, self.outline)]


PLATFORM_ALERT = {"panda": "panda", "afreeca": "afreeca", "youtube": "youtube"}
YT_TIERS = (  # (최소 금액 ₩, 머리띠 색, 메시지 칸 색, 글자 색) — 유튜브 슈퍼챗 색 구간
    (100000, "#d00000", "#e62117", "#ffffff"), (50000, "#c2185b", "#e91e63", "#ffffff"),
    (20000, "#e65100", "#f57c00", "#ffffff"), (10000, "#ffb300", "#ffca28", "#000000"),
    (5000, "#00bfa5", "#1de9b6", "#000000"), (2000, "#00b8d4", "#00e5ff", "#000000"),
    (0, "#1565c0", "#1565c0", "#ffffff"))
AVATAR_COLORS = ("#e91e63", "#9c27b0", "#3f51b5", "#03a9f4", "#009688", "#8bc34a", "#ff9800", "#795548")


class AlertSticker(PanelSticker, kind="alert"):
    """후원 알림(후원창)의 자리와 모양. 단위 · 모양이 비어 있으면 플랫폼을 따라간다.
    panda: 분홍 띠 / afreeca: 큰 숫자 카드 / youtube: 슈퍼챗 카드"""
    DEFAULTS = {**PANEL, "unit": "", "style": "", "width": 520, "bgOpacity": 0.95, "borderWidth": 3, "radius": 18,
                "x": 0.42, "y": 0.86, "show": 4.0}
    P, A, M = 16, 28, 20
    RECT_LAYER, TEXT_LAYER = 20, 22

    def layout(self, width, height, state):
        return []

    def look(self, state: StickerState):
        style = self.style if self.style in PLATFORM_ALERT.values() else PLATFORM_ALERT.get(state.platform, "panda")
        return style, (self.unit or state.unit)

    def layout_alert(self, width, height, d: Donation, state: StickerState = None) -> List[Prim]:
        state = state or StickerState({}, 0)
        style, unit = self.look(state)
        return {"panda": self._panda, "afreeca": self._afreeca, "youtube": self._youtube}[style](width, height, d, unit)

    def _verb(self, unit):
        return " 후원!" if is_money(unit) else " 선물!"

    def _panda(self, width, height, d, unit):
        k = self.k(height)
        cx, cy = self.center(width, height)
        h = (2 * self.P + self.A + (self.M if d.msg else 0)) * k
        a = lambda text, accent: self.run(text, self.A, k, self.accent if accent else None, True)
        first = [a("♥ ", True), a(d.nick, True), a("님 ", False), a(format_gift(d.amount, unit), True),
                 a(self._verb(unit), False)]
        extra = [[self.run(d.msg, self.M, k)]] if d.msg else []
        return [self.box(cx, cy, self.width * k, h, k, self.RECT_LAYER),
                _text(cx, cy, "center", first, self.TEXT_LAYER, extra_lines=extra)]

    AF_P, AF_NUM, AF_NUM_H, AF_LINE, AF_LINE_H, AF_MSG, AF_MSG_H = 14, 56, 66, 22, 30, 18, 24

    def _afreeca(self, width, height, d, unit):
        """아프리카TV 식: 큰 숫자 + '닉님 별풍선 N개 선물!'"""
        k = self.k(height)
        cx, cy = self.center(width, height)
        h = (2 * self.AF_P + self.AF_NUM_H + self.AF_LINE_H + (self.AF_MSG_H if d.msg else 0)) * k
        top = cy - h / 2
        color = HistorySticker.tier_color(d.amount)
        num = [Run(str(d.amount), r2(self.AF_NUM * k), color, True, self.font)]
        num_y = top + (self.AF_P + self.AF_NUM_H / 2) * k
        line_y = top + (self.AF_P + self.AF_NUM_H + self.AF_LINE_H / 2) * k
        line = [self.run(d.nick, self.AF_LINE, k, self.accent, True), self.run("님 ", self.AF_LINE, k),
                self.run(format_gift(d.amount, unit), self.AF_LINE, k, color, True),
                self.run(self._verb(unit), self.AF_LINE, k)]
        prims: List[Prim] = [
            RectPrim(r2(cx), r2(cy), r2(self.width * k), r2(h), r2(self.radius * k), self.bg, self.bg_opacity,
                     r2(self.border_width * k), color, self.RECT_LAYER),
            _text(cx, num_y, "center", num, self.TEXT_LAYER, (HistorySticker.INNER + HistorySticker.OUTER) * k, "#333333"),
            _text(cx, num_y, "center", num, self.TEXT_LAYER + 1, HistorySticker.INNER * k, "#ffffff"),
            _text(cx, line_y, "center", line, self.TEXT_LAYER + 1),
        ]
        if d.msg:
            msg_y = top + (self.AF_P + self.AF_NUM_H + self.AF_LINE_H + self.AF_MSG_H / 2) * k
            prims.append(_text(cx, msg_y, "center", [self.run(d.msg, self.AF_MSG, k)], self.TEXT_LAYER + 1))
        return prims

    YT_P, YT_AV, YT_HH, YT_NAME, YT_AMT, YT_MSG, YT_LH, YT_MAXC, YT_R, YT_NAME_Y, YT_AMT_Y, YT_PAD = \
        14, 40, 64, 17, 20, 18, 24, 22, 10, 22, 44, 12

    @staticmethod
    def youtube_tier(amount: int):
        return next((head, body, text) for limit, head, body, text in YT_TIERS if amount >= limit)

    def _youtube(self, width, height, d, unit):
        """유튜브 슈퍼챗: 금액대 색 머리띠(아바타 · 이름 · 금액) + 메시지 칸"""
        k = self.k(height)
        cx, cy = self.center(width, height)
        head, body, ink = self.youtube_tier(d.amount)
        lines = wrap_text(d.msg, self.YT_MAXC)[:3] if d.msg else []
        body_h = len(lines) * self.YT_LH + 2 * self.YT_PAD if lines else 0
        w, h = self.width * k, (self.YT_HH + body_h) * k
        left, top = cx - w / 2, cy - h / 2
        rect = lambda x, y, rw, rh, r, color, layer: RectPrim(r2(x), r2(y), r2(rw), r2(rh), r2(r), color, 1.0, 0.0, "", layer)
        text = lambda x, y, align, t, size, bold: _text(x, y, align, [Run(t, r2(size * k), ink, bold, self.font)],
                                                        self.TEXT_LAYER + 1)
        prims: List[Prim] = [rect(cx, cy, w, h, self.YT_R * k, body if lines else head, self.RECT_LAYER)]
        if lines:
            prims += [rect(cx, top + self.YT_HH * k / 2, w, self.YT_HH * k, self.YT_R * k, head, self.RECT_LAYER + 1),
                      rect(cx, top + (self.YT_HH - self.YT_R / 2) * k, w, self.YT_R * k, 0, head, self.RECT_LAYER + 1)]
        av_x, av_y = left + (self.YT_P + self.YT_AV / 2) * k, top + self.YT_HH * k / 2
        avatar = AVATAR_COLORS[sum(ord(c) for c in d.nick) % len(AVATAR_COLORS)]
        prims.append(rect(av_x, av_y, self.YT_AV * k, self.YT_AV * k, self.YT_AV / 2 * k, avatar, self.TEXT_LAYER))
        prims.append(_text(av_x, av_y, "center", [Run(d.nick[:1] or " ", r2(20 * k), "#ffffff", True, self.font)],
                           self.TEXT_LAYER + 1))
        text_x = left + (self.YT_P + self.YT_AV + 12) * k
        prims += [text(text_x, top + self.YT_NAME_Y * k, "left", d.nick, self.YT_NAME, False),
                  text(text_x, top + self.YT_AMT_Y * k, "left", format_gift(d.amount, unit), self.YT_AMT, True)]
        for i, line in enumerate(lines):
            prims.append(text(left + self.YT_P * k, top + (self.YT_HH + self.YT_PAD + self.YT_LH * i + self.YT_LH / 2) * k,
                              "left", line, self.YT_MSG, False))
        return prims


class ImageSticker(Sticker, kind="image"):
    DEFAULTS = {"path": "", "url": "", "height": 240, "aspect": 1.0}

    def layout(self, width, height, state):
        k = self.k(height)
        cx, cy = self.center(width, height)
        h = self.height * k
        return [ImagePrim(r2(cx), r2(cy), r2(h * self.aspect), r2(h), self.path, self.url)]
