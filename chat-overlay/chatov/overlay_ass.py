# -*- coding: utf-8 -*-
"""스티커 도형 목록과 후원 알림을 ASS 대사 줄로 쓴다. 채팅(10층) 아래에 스티커, 위에 알림."""
import math
from typing import List, Sequence

from .ass import ass_time, escape_ass
from .donations import Donation, schedule_alerts
from .shapes import ring_drawing, rounded_rect_drawing
from .stickers import AlertSticker, ImagePrim, RectPrim, Sticker, StickerState, TextPrim
from .text import Color

from .ass import STICKER_STYLE as STYLE_LINE  # noqa: E402,F401
ALIGN_TAG = {"left": 4, "center": 5, "right": 6}
# 튀어나오는 알림: donations.alert_scale / alert_opacity 와 같은 움직임
ALERT_ANIMATION = r"\fscx70\fscy70\t(0,150,\fscx108\fscy108)\t(150,250,\fscx100\fscy100)\fad(150,400)"


def _num(v: float) -> str:
    v = math.floor(v * 100 + 0.5) / 100
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0")


def _bgr(color: str) -> str:
    return Color.parse(color).to_ass()[4:]


def _alpha(opacity: float) -> str:
    return f"&H{math.floor(255 * (1 - opacity) + 0.5):02X}&"


def _dialogue(layer: int, start: float, end: float, text: str) -> str:
    return f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},Sticker,,0,0,0,,{text}"


class PrimAssWriter:
    @staticmethod
    def text(p: TextPrim, start: float, end: float, extra: str = "") -> str:
        head = (rf"{{\an{ALIGN_TAG[p.align]}\pos({_num(p.x)},{_num(p.y)})\bord{_num(p.outline_w)}\shad0"
                rf"\3c&H{_bgr(p.outline_color or '#000000')}&{extra}}}")
        body = r"\N".join("".join(rf"{{\fn{r.font}\fs{_num(r.size)}\b{1 if r.bold else 0}\c&H{_bgr(r.color)}&}}"
                                  + escape_ass(r.text) for r in line) for line in p.lines)
        return _dialogue(p.layer, start, end, head + body)

    @staticmethod
    def rect(p: RectPrim, start: float, end: float, extra: str = "") -> List[str]:
        """바탕(테두리 안쪽) + 테두리 고리. 둘 다 가운데 기준(\\an5)이라 확대해도 같이 움직인다."""
        b = p.border_w
        tag = lambda color: (rf"{{\an5\pos({_num(p.cx)},{_num(p.cy)})\bord0\shad0\c&H{_bgr(color)}&"
                             rf"\1a{_alpha(p.opacity)}{extra}\p3}}")
        fill = rounded_rect_drawing(max(0.0, p.w - 2 * b), max(0.0, p.h - 2 * b), max(0.0, p.r - b))
        out = [_dialogue(p.layer, start, end, tag(p.color) + fill + r"{\p0}")]
        if b > 0:
            out.append(_dialogue(p.layer + 1, start, end, tag(p.border_color) + ring_drawing(p.w, p.h, p.r, b) + r"{\p0}"))
        return out

    @classmethod
    def prims(cls, prims, start: float, end: float, extra: str = "") -> List[str]:
        out: List[str] = []
        for p in prims:
            if isinstance(p, TextPrim):
                out.append(cls.text(p, start, end, extra))
            elif isinstance(p, RectPrim):
                out.extend(cls.rect(p, start, end, extra))
        return out


class StickerTrack:
    """영상 전체의 스티커 · 알림 대사 줄. 그림 스티커는 ffmpeg overlay 로 따로 넘긴다."""

    def __init__(self, width: int, height: int, stickers: Sequence[Sticker], donations: Sequence[Donation],
                 duration: float, unit: str = "하트", platform: str = "panda"):
        self.width, self.height = width, height
        self.stickers = list(stickers)
        self.donations = list(donations)
        self.duration = duration
        self.unit, self.platform = unit, platform

    def _state(self, t: float) -> StickerState:
        return StickerState.at(self.donations, t, self.unit, self.platform)

    def _segments(self, sticker: Sticker):
        """후원을 따라 움직이는 스티커는 후원이 올 때마다 새 구간."""
        cuts = sorted({d.t for d in self.donations if 0 < d.t < self.duration}) if sticker.dynamic else []
        edges = [0.0] + cuts + [self.duration]
        return list(zip(edges, edges[1:]))

    def dialogues(self) -> List[str]:
        out: List[str] = []
        for s in self.stickers:
            if isinstance(s, AlertSticker):
                for slot in schedule_alerts(self.donations, self.duration, s.show):
                    out += PrimAssWriter.prims(s.layout_alert(self.width, self.height, slot.donation, self._state(slot.start)),
                                               slot.start, slot.end, ALERT_ANIMATION)
                continue
            for start, end in self._segments(s):
                state = self._state(start)
                out += PrimAssWriter.prims(s.layout(self.width, self.height, state), start, end)
        return out

    def images(self) -> List[ImagePrim]:
        return [p for s in self.stickers for p in s.layout(self.width, self.height, StickerState({}, 0))
                if isinstance(p, ImagePrim) and p.path]
