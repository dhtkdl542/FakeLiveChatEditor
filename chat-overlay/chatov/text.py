# -*- coding: utf-8 -*-
"""채팅 글자 줄바꿈과 색 변환. web/js/core/text.js 와 같은 규칙을 지킨다."""
import re
from dataclasses import dataclass
from typing import Optional, Sequence

MIN_CHARS_PER_LINE = 4

_HEX6 = re.compile(r"^#?([0-9a-fA-F]{6})$")
_HEX3 = re.compile(r"^#?([0-9a-fA-F]{3})$")
_ASS = re.compile(r"^&H([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})&?$")


def wrap_text(text: str, max_chars: int) -> list:
    """글자 수 기준으로 자른다. 띄어쓰기를 따지지 않는 채팅창 방식."""
    size = max(MIN_CHARS_PER_LINE, int(max_chars))
    lines = [text[i:i + size] for i in range(0, len(text), size)]
    return lines or [""]


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

    WHITE_HEX = "#ffffff"

    @classmethod
    def parse(cls, value: Optional[str]) -> "Color":
        v = (value or "").strip()
        m = _HEX6.match(v)
        if m:
            h = m.group(1)
            return cls(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        m = _HEX3.match(v)
        if m:
            h = "".join(ch * 2 for ch in m.group(1))
            return cls(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        m = _ASS.match(v)
        if m:
            return cls(int(m.group(4), 16), int(m.group(3), 16), int(m.group(2), 16))
        return cls(255, 255, 255)

    def to_ass(self) -> str:
        return f"&H00{self.b:02X}{self.g:02X}{self.r:02X}"

    def to_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


def color_for_nick(nick: str, palette: Sequence[str]) -> str:
    """닉네임 글자 코드 합으로 색을 고른다. 같은 닉은 항상 같은 색."""
    if not palette:
        return Color.WHITE_HEX
    return palette[sum(ord(ch) for ch in nick) % len(palette)]
