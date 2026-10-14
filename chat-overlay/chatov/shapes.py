# -*- coding: utf-8 -*-
"""ASS 벡터 드로잉(\\p3, 좌표 = 픽셀 × 4) 으로 둥근 사각형과 테두리 고리를 만든다.
web/js/core/shapes.js 가 같은 경로를 만들어 SVG 로 그린다."""
import math

UNIT = 4    # \p3 → 좌표를 4 로 나눠 읽는다 (0.25px 정밀도)
KAPPA = 0.5523  # 원호를 3차 베지어로 근사하는 상수


def _q(v: float) -> int:
    return math.floor(v * UNIT + 0.5)


def _pt(x: float, y: float) -> str:
    return f"{_q(x)} {_q(y)}"


def _radius(w: float, h: float, r: float) -> float:
    return max(0.0, min(r, w / 2, h / 2))


def rounded_rect_drawing(w: float, h: float, r: float, x0: float = 0, y0: float = 0) -> str:
    """(x0, y0) 에서 시작하는 w × h 둥근 사각형. 시계 방향."""
    r = _radius(w, h, r)
    p = lambda x, y: _pt(x0 + x, y0 + y)
    if r == 0:
        return f"m {p(0, 0)} l {p(w, 0)} l {p(w, h)} l {p(0, h)} l {p(0, 0)}"
    c = KAPPA * r
    return " ".join([
        f"m {p(r, 0)}", f"l {p(w - r, 0)}", f"b {p(w - r + c, 0)} {p(w, r - c)} {p(w, r)}",
        f"l {p(w, h - r)}", f"b {p(w, h - r + c)} {p(w - r + c, h)} {p(w - r, h)}",
        f"l {p(r, h)}", f"b {p(r - c, h)} {p(0, h - r + c)} {p(0, h - r)}",
        f"l {p(0, r)}", f"b {p(0, r - c)} {p(r - c, 0)} {p(r, 0)}",
    ])


def _reversed_rect(w: float, h: float, r: float, x0: float, y0: float) -> str:
    """같은 사각형을 반시계 방향으로. 바깥 경로와 합치면 가운데가 뚫린다."""
    r = _radius(w, h, r)
    p = lambda x, y: _pt(x0 + x, y0 + y)
    if r == 0:
        return f"m {p(0, 0)} l {p(0, h)} l {p(w, h)} l {p(w, 0)} l {p(0, 0)}"
    c = KAPPA * r
    return " ".join([
        f"m {p(r, 0)}", f"b {p(r - c, 0)} {p(0, r - c)} {p(0, r)}", f"l {p(0, h - r)}",
        f"b {p(0, h - r + c)} {p(r - c, h)} {p(r, h)}", f"l {p(w - r, h)}",
        f"b {p(w - r + c, h)} {p(w, h - r + c)} {p(w, h - r)}", f"l {p(w, r)}",
        f"b {p(w, r - c)} {p(w - r + c, 0)} {p(w - r, 0)}", f"l {p(r, 0)}",
    ])


def ring_drawing(w: float, h: float, r: float, border: float) -> str:
    """두께 border 인 둥근 테두리 고리. 너무 두꺼우면 꽉 찬 사각형."""
    if border * 2 >= min(w, h):
        return rounded_rect_drawing(w, h, r)
    return (rounded_rect_drawing(w, h, r) + " "
            + _reversed_rect(w - 2 * border, h - 2 * border, max(0.0, r - border), border, border))
