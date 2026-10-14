# -*- coding: utf-8 -*-
"""Python 구현을 기준으로 shared/contract.json 을 만든다.
브라우저(web/js/core)도 같은 파일로 테스트해서 미리보기와 실제 영상이 같게 나오는지 확인한다.

    python tools/gen_contract.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dataclasses  # noqa: E402

from chatov.ass import ChatLayout, OverlayStyle, box_alpha  # noqa: E402
from chatov.badges import DEFAULT_BADGES, Badge, badge_for, nick_hash  # noqa: E402
from chatov.donations import (Donation, DonationGenerator, alert_opacity, alert_scale, merge_into_chat,  # noqa: E402
                              schedule_alerts, format_gift, donation_chat_text)
from chatov.shapes import ring_drawing, rounded_rect_drawing  # noqa: E402
from chatov.stickers import ImagePrim, RectPrim, Sticker, StickerState, TextPrim  # noqa: E402
from chatov.icons import ICON_NAMES, icon_drawing, icon_shape  # noqa: E402
from chatov.rng import Mulberry32  # noqa: E402
from chatov.speed import SpeedCurve  # noqa: E402
from chatov.text import Color, color_for_nick, wrap_text  # noqa: E402
from chatov.timeline import ChatEvent, EventGenerator  # noqa: E402

OUT = ROOT / "shared" / "contract.json"

SPEED_CASES = [
    {"SPEED_VAR": 0, "SPEED_PERIOD": 8, "SPEED_PHASES": [0, 0, 0], "SPEED_SECTIONS": []},
    {"SPEED_VAR": 0.5, "SPEED_PERIOD": 8, "SPEED_PHASES": [0.1, 1.2, 2.3], "SPEED_SECTIONS": []},
    {"SPEED_VAR": 1, "SPEED_PERIOD": 3, "SPEED_PHASES": [5.0, 0.4, 3.3],
     "SPEED_SECTIONS": [{"start": 2, "end": 6, "speed": 3}, {"start": 5, "end": 9, "speed": 0.3},
                        {"start": 12, "end": 12.4, "speed": 4}]},
]
TIMES = [0, 0.25, 1, 2.1, 2.3, 3.7, 5.5, 6.9, 8.75, 12.2, 30]

GEN_CASES = [
    {"seed": 1, "duration": 20, "cfg": {
        "NICKS": ["쎾써", "ㅇㅇ", "뷰럴러버", "a😀"], "MSGS": ["ㅋㅋ", "실화냐", "5000원 무시하나", "초심잃었네", "와"],
        "COLORS": ["#47b3ff", "#ffff00", "#ffffff"], "CHAT_START": 0.5, "INTERVAL_MIN": 0.25, "INTERVAL_MAX": 0.7,
        **SPEED_CASES[2]}},
    {"seed": 4242, "duration": 15, "cfg": {
        "NICKS": ["x"], "MSGS": ["1", "2", "3"], "COLORS": ["#ff0000"], "CHAT_START": 0, "INTERVAL_MIN": 0.7,
        "INTERVAL_MAX": 0.3, **SPEED_CASES[1]}},
]

BADGE_NICKS = ["a", "abc", "", "별빛여우", "감자칩", "새벽산책", "a😀", "코코넛", "구름빵", "오늘도출근"] +     [f"시청자{i}" for i in range(30)]
BADGE_CASES = [
    (DEFAULT_BADGES, {}),
    ((Badge("manager", "매니저", "crown", "#123456", 0.3), Badge("vip", "VIP", "diamond", "#abcdef", 0.5)),
     {"별빛여우": "vip", "감자칩": "", "코코넛": "없는배지"}),
]

LAYOUT_STYLE = {"VISIBLE": 4, "FADE_UP_STRENGTH": 70, "MAX_CHARS_PER_LINE": 5}
LAYOUT_EVENTS = [ChatEvent(i * 0.5, f"n{i}", msg, "#ff0000")
                 for i, msg in enumerate(["짧음", "가나다라마바사아", "ok", "1234567890123", "끝"])]


def build() -> dict:
    return {
        "_note": "tools/gen_contract.py 로 만든 파일입니다. 직접 고치지 마세요.",
        "rng": [{"seed": s, "values": [r.next() for r in [Mulberry32(s)] for _ in range(6)]}
                for s in (0, 1, 42, 4294967295)],
        "wrap": [{"text": t, "max": m, "lines": wrap_text(t, m)}
                 for t, m in [("ㅋㅋ", 22), ("가나다라마바사", 3), ("", 5), ("abcdefghij", 4)]],
        "color": [{"in": c, "hex": Color.parse(c).to_hex()} for c in ["#47b3ff", "#fa0", "&H00FFB347", "x"]],
        "nickColor": [{"nick": n, "palette": ["#000001", "#000002", "#000003"],
                       "color": color_for_nick(n, ["#000001", "#000002", "#000003"])}
                      for n in ["ab", "ㅇㅇ", "a😀", "뷰럴러버"]],
        "speed": [{"cfg": cfg, "points": [[t, SpeedCurve.from_settings(cfg)(t)] for t in TIMES]}
                  for cfg in SPEED_CASES],
        "events": [{**case, "events": [e.__dict__ for e in EventGenerator(
            curve=SpeedCurve.from_settings(case["cfg"]), nicks=case["cfg"]["NICKS"], msgs=case["cfg"]["MSGS"],
            palette=case["cfg"]["COLORS"], start=case["cfg"]["CHAT_START"],
            interval_min=case["cfg"]["INTERVAL_MIN"], interval_max=case["cfg"]["INTERVAL_MAX"],
            rng=Mulberry32(case["seed"])).generate(case["duration"])]} for case in GEN_CASES],
        "layout": {
            "style": LAYOUT_STYLE,
            "events": [e.__dict__ for e in LAYOUT_EVENTS],
            "frames": [[r.__dict__ for r in ChatLayout(OverlayStyle.from_settings(LAYOUT_STYLE)).rows_at(LAYOUT_EVENTS, i)]
                       for i in range(len(LAYOUT_EVENTS))],
        },
        "styleDefaults": dataclasses.asdict(OverlayStyle.from_settings({})),
        "badges": {
            "hashes": [[n, nick_hash(n)] for n in BADGE_NICKS],
            "cases": [{"badges": [dataclasses.asdict(b) for b in badges], "overrides": overrides,
                       "picks": [[n, (badge_for(n, badges, overrides) or Badge("", "", "", "", 0)).key]
                                 for n in BADGE_NICKS]}
                      for badges, overrides in BADGE_CASES],
        },
        "positions": [
            {"cfg": cfg, "width": 1280, "height": 720, "points": [
                [age, list(ChatLayout(OverlayStyle.from_settings(cfg)).position(_row(age), 1280, 720))]
                for age in (0, 1, 5)]}
            for cfg in POSITION_CASES
        ],
        "icons": {name: {"path": icon_shape(name).path, "width": icon_shape(name).width,
                         "drawing16": icon_drawing(name, 16)} for name in ICON_NAMES},
        "boxAlpha": [[o, a, box_alpha(o, a)] for o in (0, 0.25, 0.45, 0.5, 1) for a in (0, 18, 36, 200)],
        "shapes": [{"args": list(a), "rect": rounded_rect_drawing(*a), "ring": ring_drawing(*a, 3)}
                   for a in [(200, 80, 16), (100, 20, 50), (10.3, 5.1, 0), (321.5, 64.25, 18.75)]],
        "stickers": [{"sticker": s, "width": w, "height": h,
                      "state": {"totals": st.totals, "total": st.total, "donations": [d.__dict__ for d in st.donations],
                                "unit": st.unit, "platform": st.platform},
                      "prims": [_prim(p) for p in Sticker.from_dict(s).layout(w, h, st)]}
                     for s in STICKER_CASES for (w, h) in ((1920, 1080), (1280, 720))
                     for st in (StickerState({}, 0), StickerState({"워린": 6000, "새닉": 777}, 6777, (
                         Donation(1, "워린", 6000, ""), Donation(2, "새닉", 777, "")), "₩", "youtube"))],
        "alerts": [{"sticker": s, "donation": d.__dict__, "width": 1280, "height": 720,
                    "state": {"unit": unit, "platform": platform},
                    "prims": [_prim(p) for p in Sticker.from_dict(s).layout_alert(
                        1280, 720, d, StickerState({}, 0, (), unit, platform))]}
                   for s in ({"type": "alert"}, {"type": "alert", "unit": "별풍선", "scale": 1.3, "x": 0.3},
                             {"type": "alert", "style": "afreeca", "width": 380},
                             {"type": "alert", "style": "youtube", "width": 420, "scale": 0.9})
                   for d in (Donation(1, "소다", 550, ""), Donation(2, "뭉치", 12345, "사랑해요 " * 6),
                             Donation(3, "😀a", 100000, "최고"))
                   for unit, platform in (("하트", "panda"), ("별풍선", "afreeca"), ("₩", "youtube"))],
        "gifts": [[a, u, format_gift(a, u), donation_chat_text(Donation(0, "x", a, m), u)]
                  for a, u, m in ((550, "하트", ""), (4860, "별풍선", "고마워"), (10000, "₩", ""), (5, "$", "hi"),
                                  (3000, "원", ""), (7, "", ""), (1234567, "치즈", ""))],
        "donations": [{**case, "donations": [d.__dict__ for d in DonationGenerator.from_settings(case["cfg"], case["seed"])
                                             .generate(case["duration"])]} for case in DONATION_CASES],
        "merged": [e.__dict__ for e in merge_into_chat(
            [ChatEvent(1.0, "x", "ㅋㅋ", "#111111"), ChatEvent(3.0, "y", "와", "#222222")],
            [Donation(3.0, "별사", 1550, "화이팅"), Donation(0.5, "갓스", 10, "")], ["#ff0000", "#00ff00"], "하트")],
        "alertSchedule": [[s.start, s.end, s.donation.nick] for s in schedule_alerts(
            [Donation(1.0, "a", 1, ""), Donation(2.0, "b", 1, ""), Donation(20.0, "c", 1, ""), Donation(58.5, "d", 1, "")],
            60, 4.0, 0.3)],
        "alertAnim": [[ms, alert_scale(ms), alert_opacity(ms, 4000)] for ms in (-10, 0, 40, 75, 149, 150, 200, 250, 1000, 3700, 3999, 4000)],
    }


def _prim(p):
    kind = {TextPrim: "text", RectPrim: "rect", ImagePrim: "image"}[type(p)]
    d = dataclasses.asdict(p)
    return {"kind": kind, **d}


STICKER_CASES = [
    {"type": "text", "text": "별사", "x": 0.1, "y": 0.55},
    {"type": "text", "text": "갓스", "heart": False, "scale": 1.4, "fill": "#ffd24a", "outer": "#b07a00"},
    {"type": "ranking"},
    {"type": "ranking", "rows": 3, "auto": False, "width": 260, "scale": 0.8, "borderWidth": 0},
    {"type": "goal"},
    {"type": "goal", "current": 0, "target": 500, "auto": False},
    {"type": "banner"},
    {"type": "banner", "lines": ["한 줄만"], "scale": 1.2},
    {"type": "image", "path": "C:/a.png", "url": "/media/a.png", "height": 200, "aspect": 0.75},
    {"type": "table"},
    {"type": "table", "title": "", "rows": 3, "showTotal": False, "highlightRow": 2, "scale": 0.9, "width": 300,
     "headers": ["멤버", "점수"], "entries": [["가", 30], ["나", 20], ["다", 10], ["라", 0]]},
    {"type": "table", "auto": False, "entries": [["혼자", 5]]},
    {"type": "history"},
    {"type": "history", "count": 2, "width": 180, "scale": 1.2, "unit": "하트", "entries": [["a", 99], ["b", 500]]},
    {"type": "history", "auto": False, "count": 6},
    {"type": "history", "unit": "", "count": 2},
    {"type": "mvp"},
    {"type": "mvp", "label": "★", "entries": [], "auto": False, "scale": 1.5},
    {"type": "mvp", "entries": [["워린", 6000], ["구릭", 6000]]},
]

DONATION_CASES = [
    {"seed": 11, "duration": 300, "cfg": {"NICKS": ["별사", "갓스", "워린", "소다"], "MSGS": ["화이팅", "이쁘다", "ㅋㅋ"],
                                          "CHAT_START": 0.5, "DONATION_EVERY": 12,
                                          "DONATION_AMOUNTS": [10, 50, 100, 550, 1000], "DONATION_MSG_CHANCE": 0.4}},
    {"seed": 4242, "duration": 120, "cfg": {"NICKS": ["a"], "MSGS": [], "DONATION_EVERY": 5}},
]


POSITION_CASES = [
    {},
    {"BOX": True, "BOX_PADDING": 8, "SIDE_MARGIN": 10, "BOTTOM_MARGIN": 30, "LINE_H": 40},
    {"ALIGN": "left", "BOX": True, "BOX_PADDING": 5},
    {"ALIGN": "left", "BOX": False, "SIDE_MARGIN": 0, "BOTTOM_MARGIN": 0},
]


def _row(age):
    from chatov.ass import Row
    return Row("n", "m", "#fff", age, 0, age == 0, False)


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
