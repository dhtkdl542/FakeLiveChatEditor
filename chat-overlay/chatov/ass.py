# -*- coding: utf-8 -*-
"""채팅 타임라인을 ASS 자막으로 바꾼다. 줄 배치 규칙은 web/js/core/layout.js 와 같다."""
import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from .icons import icon_drawing
from .text import Color, wrap_text
from .timeline import ChatEvent

MAX_ALPHA = 200      # 아무리 오래된 줄도 완전히 투명해지지는 않게
ICON_EM = 0.8        # 아이콘 높이 = 닉네임 글자 크기 × 0.8 × 아이콘 배율 (한글 높이와 비슷)
ALIGNS = ("right", "left")
CHAT_LAYER = 10      # 스티커(0~3) 위, 후원 알림(20~) 아래
STICKER_STYLE = ("Style: Sticker,Malgun Gothic,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
                 "0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1")


def _round(v: float) -> int:
    # JS Math.round 와 같은 반올림 (파이썬 round 는 .5 를 짝수로 보냄)
    return math.floor(v + 0.5)


def _bool(v) -> bool:
    return v is True or str(v).lower() in ("1", "true", "on", "yes")


@dataclass(frozen=True)
class OverlayStyle:
    align: str            # "right" (오른쪽 아래 구석) | "left"
    side_margin: int      # 화면 옆 가장자리와의 거리 (px)
    bottom_margin: int    # 화면 아래 가장자리와의 거리 (px)
    line_h: int           # 줄과 줄 사이 (px)
    visible: int
    fade_in_ms: int
    fade_out_ms: int
    fade_up: int
    max_chars: int
    nick_font: str
    nick_size: int
    nick_bold: bool
    msg_font: str
    msg_size: int
    msg_color: str
    outline: int          # 박스가 없을 때 글자 테두리 두께
    box: bool             # 채팅마다 배경 박스
    box_color: str
    box_opacity: float    # 0 ~ 1
    box_padding: int
    icon: str             # "" 이면 없음. chatov.icons.ICON_NAMES
    icon_color: str       # "" 이면 닉네임 색을 따라감
    icon_scale: float
    highlight_color: str     # 후원 줄 박스 색
    highlight_opacity: float

    @classmethod
    def from_settings(cls, cfg: dict) -> "OverlayStyle":
        align = cfg.get("ALIGN", "right")
        return cls(
            align=align if align in ALIGNS else "right",
            side_margin=int(cfg.get("SIDE_MARGIN", 24)),
            bottom_margin=int(cfg.get("BOTTOM_MARGIN", 24)),
            line_h=int(cfg.get("LINE_H", 36)),
            visible=max(1, int(cfg.get("VISIBLE", 8))),
            fade_in_ms=int(cfg.get("FADE_IN_MS", 180)),
            fade_out_ms=int(cfg.get("FADE_OUT_MS", 450)),
            fade_up=int(cfg.get("FADE_UP_STRENGTH", 18)),
            max_chars=int(cfg.get("MAX_CHARS_PER_LINE", 22)),
            nick_font=cfg.get("NICK_FONT") or "Malgun Gothic",
            nick_size=int(cfg.get("NICK_SIZE", 20)),
            nick_bold=_bool(cfg.get("NICK_BOLD", False)),
            msg_font=cfg.get("MSG_FONT") or "Malgun Gothic",
            msg_size=int(cfg.get("MSG_SIZE", 18)),
            msg_color=cfg.get("MSG_COLOR") or "#ffffff",
            outline=int(cfg.get("OUTLINE", 2)),
            box=_bool(cfg.get("BOX", False)),
            box_color=cfg.get("BOX_COLOR") or "#000000",
            box_opacity=min(1.0, max(0.0, float(cfg.get("BOX_OPACITY", 0.45)))),
            box_padding=int(cfg.get("BOX_PADDING", 6)),
            icon=cfg.get("ICON") or "",
            icon_color=cfg.get("ICON_COLOR") or "",
            icon_scale=float(cfg.get("ICON_SCALE", 1.0)),
            highlight_color=cfg.get("HIGHLIGHT_COLOR") or "#ff5fa2",
            highlight_opacity=min(1.0, max(0.0, float(cfg.get("HIGHLIGHT_OPACITY", 0.85)))),
        )

    def padding(self, row: "Row") -> int:
        """박스가 있는 줄(박스 모드이거나 후원 줄)은 박스 여백만큼 안쪽에 놓는다."""
        return self.box_padding if self.box or row.highlight else 0


@dataclass(frozen=True)
class Row:
    nick: str      # 대사 첫 줄에만 닉이 붙는다
    msg: str
    color: str
    age: int       # 0 = 맨 아래(가장 최근) 줄
    alpha: int     # ASS 투명도 0(불투명) ~ 255
    is_newest: bool
    is_oldest: bool  # 화면이 꽉 찼을 때 맨 위 줄 (다음 채팅에서 사라짐)
    highlight: bool = False  # 후원 줄


class ChatLayout:
    def __init__(self, style: OverlayStyle):
        self.style = style

    def rows_at(self, events: Sequence[ChatEvent], index: int) -> List[Row]:
        """index 번째 채팅이 막 올라온 순간 화면에 보이는 줄들 (위→아래)."""
        s = self.style
        pieces = []
        for e in events[max(0, index - s.visible + 1): index + 1]:
            for i, piece in enumerate(wrap_text(e.msg, s.max_chars)):
                pieces.append((e.nick if i == 0 else "", piece, e.color, e.highlight))
        pieces = pieces[-s.visible:]
        n = len(pieces)
        return [Row(nick, msg, color, n - 1 - row, min(MAX_ALPHA, (n - 1 - row) * s.fade_up),
                    is_newest=(row == n - 1), is_oldest=(row == 0 and n >= s.visible), highlight=hl)
                for row, (nick, msg, color, hl) in enumerate(pieces)]

    def position(self, row: Row, width: int, height: int) -> Tuple[int, int, str]:
        """글자 줄의 아래쪽 모서리 (right 면 오른쪽 아래, left 면 왼쪽 아래). 박스 바깥선이 여백에 닿게 안쪽으로 들인다."""
        s = self.style
        pad = s.padding(row)
        inset_x = s.side_margin + pad
        x = width - inset_x if s.align == "right" else inset_x
        y = height - s.bottom_margin - pad - row.age * s.line_h
        return x, y, s.align


def ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    return f"{h}:{m:02d}:{sec % 60:05.2f}"


def escape_ass(text: str) -> str:
    """중괄호와 역슬래시는 ASS 특수 문자라서 전각 문자로 바꿔 그대로 보이게 한다."""
    return (text.replace("\\", "＼").replace("{", "｛").replace("}", "｝")
            .replace("\r", " ").replace("\n", " "))


def _bgr(color: str) -> str:
    return Color.parse(color).to_ass()[4:]


def box_alpha(opacity: float, text_alpha: int) -> int:
    """박스도 글자처럼 위로 갈수록 흐려지게: 박스 불투명도 × 글자 불투명도."""
    base = _round(255 * (1 - opacity))
    return 255 - _round((255 - base) * (255 - text_alpha) / 255)


class AssWriter:
    def __init__(self, width: int, height: int, style: OverlayStyle):
        self.width = width
        self.height = height
        self.style = style
        self.layout = ChatLayout(style)

    def header(self) -> str:
        s = self.style
        fmt = "&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0"
        return (
            "[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {self.width}\nPlayResY: {self.height}\n"
            "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            # 박스 없는 채팅: 글자 테두리 / 박스 채팅: BorderStyle 4 = 줄 전체를 감싸는 박스 하나 (libass)
            f"Style: Chat,{s.msg_font},{s.msg_size},{fmt},1,{s.outline},0,3,0,0,0,1\n"
            f"Style: ChatBox,{s.msg_font},{s.msg_size},{fmt},4,0,0,3,0,0,0,1\n"
            f"{STICKER_STYLE}\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

    def _fade(self, row: Row) -> str:
        s = self.style
        if row.is_newest and s.fade_in_ms > 0:
            return rf"\fad({s.fade_in_ms},0)"
        if row.is_oldest and s.fade_out_ms > 0:
            return rf"\fad(0,{s.fade_out_ms})"
        return ""

    def _box_alpha(self, row: Row, duration_ms: int) -> str:
        """libass 의 \\fad 는 BorderStyle 4 박스에 안 먹는다. 박스 투명도를 \\t 로 같은 타이밍에 움직인다."""
        s = self.style
        ba = box_alpha(s.highlight_opacity if row.highlight else s.box_opacity, row.alpha)
        if row.is_newest and s.fade_in_ms > 0:
            return rf"\4a&HFF&\t(0,{s.fade_in_ms},\4a&H{ba:02X}&)"
        if row.is_oldest and s.fade_out_ms > 0:
            return rf"\4a&H{ba:02X}&\t({max(0, duration_ms - s.fade_out_ms)},{duration_ms},\4a&HFF&)"
        return rf"\4a&H{ba:02X}&"

    def _look(self, row: Row, duration_ms: int) -> str:
        s, a = self.style, row.alpha
        if s.box or row.highlight:
            color = s.highlight_color if row.highlight else s.box_color
            return (rf"\bord{s.box_padding}\shad0\1a&H{a:02X}&\3a&HFF&"
                    rf"\4c&H{_bgr(color)}&" + self._box_alpha(row, duration_ms))
        return rf"\bord{s.outline}\shad0\1a&H{a:02X}&\3c&H000000&\3a&H{a:02X}&"

    def _row_text(self, row: Row, duration_ms: int) -> str:
        s = self.style
        x, y, align = self.layout.position(row, self.width, self.height)
        an = 3 if align == "right" else 1
        body = ""
        if row.nick:
            drawing = icon_drawing(s.icon, s.nick_size * ICON_EM * s.icon_scale)
            if drawing:
                body += rf"{{\c&H{_bgr(s.icon_color or row.color)}&\p3}}{drawing}{{\p0}} "
            body += (rf"{{\fn{s.nick_font}\fs{s.nick_size}\b{1 if s.nick_bold else 0}\c&H{_bgr(row.color)}&}}"
                     + escape_ass(row.nick) + " ")
        msg_bold, msg_color = (1, "#ffffff") if row.highlight else (0, s.msg_color)
        body += rf"{{\fn{s.msg_font}\fs{s.msg_size}\b{msg_bold}\c&H{_bgr(msg_color)}&}}" + escape_ass(row.msg)
        return rf"{{\an{an}\pos({x},{y}){self._fade(row)}{self._look(row, duration_ms)}}}{body}"

    def build(self, events: Sequence[ChatEvent], duration: float, extra: Sequence[str] = ()) -> str:
        """채팅 대사 줄 + (스티커 · 알림처럼) 따로 만든 대사 줄."""
        out = [self.header()]
        for i, e in enumerate(events):
            end = events[i + 1].t if i + 1 < len(events) else duration
            duration_ms = _round((end - e.t) * 1000)
            for row in self.layout.rows_at(events, i):
                style_name = "ChatBox" if self.style.box or row.highlight else "Chat"
                text = self._row_text(row, duration_ms)
                out.append(f"Dialogue: {CHAT_LAYER},{ass_time(e.t)},{ass_time(end)},{style_name},,0,0,0,,{text}\n")
        out.extend(line + "\n" for line in extra)
        return "".join(out)
