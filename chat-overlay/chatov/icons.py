# -*- coding: utf-8 -*-
"""닉네임 앞에 붙는 아이콘 모양. ASS 벡터 드로잉(m/l/b) 문법으로 정의하고 web/js/core/icons.js 와 같은 모양을 쓴다.

libass 는 줄 안의 드로잉 아래쪽을 글자 기준선에 맞춘다. 그래서 모든 모양을 세로 0~100 을 꽉 채우게
정규화해서, 미리보기(SVG)와 결과 영상의 위치가 같아지게 한다."""
import math
import re
from dataclasses import dataclass
from typing import Optional

ICON_NAMES = ("circle", "rounded", "heart", "star", "crown", "diamond")

_RAW = {
    "circle": "m 50 0 b 77.6 0 100 22.4 100 50 b 100 77.6 77.6 100 50 100 b 22.4 100 0 77.6 0 50 b 0 22.4 22.4 0 50 0",
    "rounded": "m 20 0 l 80 0 b 91 0 100 9 100 20 l 100 80 b 100 91 91 100 80 100 l 20 100 b 9 100 0 91 0 80 "
               "l 0 20 b 0 9 9 0 20 0",
    "heart": "m 50 92 b 20 70 0 52 0 30 b 0 13 13 2 28 2 b 38 2 46 8 50 16 b 54 8 62 2 72 2 b 87 2 100 13 100 30 "
             "b 100 52 80 70 50 92",
    "star": "m 50 0 l 61.8 35.4 99 35.4 69.1 57.3 80.3 92.7 50 70.8 19.7 92.7 30.9 57.3 1 35.4 38.2 35.4",
    "crown": "m 0 85 l 0 25 27 50 50 10 73 50 100 25 100 85",
    "diamond": "m 50 0 l 100 50 50 100 0 50",
}

_TOKEN = re.compile(r"[mlb]|-?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class IconShape:
    path: str     # 세로 0~100, 왼쪽 0 에서 시작
    width: float  # 정규화된 폭 (세로 100 기준)


def _fmt(v: float) -> str:
    s = f"{math.floor(v * 100 + 0.5) / 100:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _transform(path: str, fn) -> str:
    """경로의 숫자 쌍 (x, y) 에 fn 을 적용한다. 글자 명령(m/l/b)은 그대로 둔다."""
    out, pending = [], None
    for tok in _TOKEN.findall(path):
        if tok in "mlb":
            out.append(tok)
        elif pending is None:
            pending = float(tok)
        else:
            x, y = fn(pending, float(tok))
            out.extend([x, y])
            pending = None
    return " ".join(out)


def _bounds(path: str):
    nums = [float(t) for t in _TOKEN.findall(path) if t not in "mlb"]
    xs, ys = nums[0::2], nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _normalize(path: str) -> IconShape:
    x0, y0, x1, y1 = _bounds(path)
    k = 100 / (y1 - y0)
    return IconShape(_transform(path, lambda x, y: (_fmt((x - x0) * k), _fmt((y - y0) * k))), (x1 - x0) * k)


_SHAPES = {name: _normalize(_RAW[name]) for name in ICON_NAMES}


def icon_shape(name: str) -> Optional[IconShape]:
    return _SHAPES.get(name)


def icon_width(name: str, size_px: float) -> float:
    shape = icon_shape(name)
    return shape.width * size_px / 100 if shape else 0


def icon_drawing(name: str, size_px: float) -> str:
    """ASS \\p3 드로잉 문자열 (좌표 = 픽셀 × 4, 0.25px 정밀도)."""
    shape = icon_shape(name)
    if not shape:
        return ""
    k = size_px / 100 * 4
    return _transform(shape.path, lambda x, y: (str(math.floor(x * k + 0.5)), str(math.floor(y * k + 0.5))))
