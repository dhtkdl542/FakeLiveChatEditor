// 채팅 줄 꾸미기: 닉네임 배지(같은 닉 = 같은 배지) · 둥근/알약 박스 · 테두리 · 결과 영상용 줄 폭
import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { DEFAULT_BADGES, badgeFor, badgeSummary, nickHash, parseBadgeOverrides } from "../js/core/badges.js";
import { ChatLayout, OverlayStyle, rowKey } from "../js/core/layout.js";
import { ICON_NAMES, iconShape } from "../js/core/icons.js";
import { Settings } from "../js/core/settings.js";
import { buildRenderRequest } from "../js/core/export.js";
import { CHAT_TEMPLATES } from "../js/core/presets.js";

const extra = { colors: [], phases: [0, 0, 0], sections: [] };
const MANAGER = { key: "manager", label: "매니저", icon: "shield", color: "#22c55e", share: 1 };

describe("badges", () => {
  test("FNV-1a 해시 (코드 포인트 기준)", () => {
    assert.equal(nickHash("a"), 0xE40C292C);
    assert.equal(nickHash("abc"), 0x1A47E90B);
  });

  test("배지 직접 지정: '닉네임 배지이름', 닉에 띄어쓰기가 있어도 마지막 낱말이 배지", () => {
    const got = parseBadgeOverrides("별빛여우 매니저\n감자 칩 구독자\n코코넛 없음\n구름빵 sub\n이상한줄 우주선\n\n혼자", DEFAULT_BADGES);
    assert.deepEqual(got, { "별빛여우": "manager", "감자 칩": "sub", "코코넛": "", "구름빵": "sub" });
  });

  test("지금 닉네임 목록에서 누가 어떤 배지인지 요약", () => {
    const s = badgeSummary(["가", "나", "다"], [MANAGER], { "다": "" });
    assert.deepEqual(s, { groups: [{ label: "매니저", nicks: ["가", "나"] }], none: ["다"] });
  });

  test("같은 닉은 언제나 같은 배지", () => {
    assert.equal(badgeFor("별빛여우", DEFAULT_BADGES, {}), badgeFor("별빛여우", DEFAULT_BADGES, {}));
  });
});

describe("OverlayStyle: 박스 모양 · 배지", () => {
  test("설정을 읽고, 모르는 모양은 각진 박스", () => {
    const s = OverlayStyle.fromSettings({ BOX_SHAPE: "pill", BOX_RADIUS: 10, BOX_BORDER: 2, BOX_BORDER_COLOR: "#ff0000",
      BADGES_ON: true, BADGES: [MANAGER], BADGE_OVERRIDES: { "닉": "" } });
    assert.deepEqual([s.boxShape, s.boxRadius, s.boxBorder, s.boxBorderColor, s.badgesOn], ["pill", 10, 2, "#ff0000", true]);
    assert.deepEqual(s.badges, [MANAGER]);
    assert.equal(OverlayStyle.fromSettings({ BOX_SHAPE: "별" }).boxShape, "square");
  });

  test("닉 앞 그림: 공통 아이콘 다음에 배지, 이어지는 줄에는 없음", () => {
    const s = OverlayStyle.fromSettings({ ICON: "circle", BADGES_ON: true, BADGES: [MANAGER] });
    assert.deepEqual(s.icons({ nick: "닉", color: "#ff0000" }), [["circle", "#ff0000"], ["shield", "#22c55e"]]);
    assert.deepEqual(s.icons({ nick: "", color: "#ff0000" }), []);
    const off = OverlayStyle.fromSettings({ BADGES_ON: false, BADGES: [MANAGER] });
    assert.deepEqual(off.icons({ nick: "닉", color: "#ff0000" }), []);
  });

  test("미리보기 박스: 알약은 높이의 절반, 둥근 박스는 모서리 값, 테두리는 글자처럼만 흐려짐", () => {
    const layout = new ChatLayout(OverlayStyle.fromSettings({ BOX: true, BOX_SHAPE: "pill", BOX_BORDER: 2,
      BOX_BORDER_COLOR: "#ff0000", NICK_SIZE: 20, MSG_SIZE: 18, BOX_PADDING: 6 }));
    const p = layout.paint({ alpha: 18, highlight: false });
    assert.equal(p.radius, 16);                      // (20 + 6×2) / 2
    assert.equal(p.border.width, 2);
    assert.equal(p.border.color, `rgba(255,0,0,${(255 - 18) / 255})`);
    const rounded = new ChatLayout(OverlayStyle.fromSettings({ BOX: true, BOX_SHAPE: "rounded", BOX_RADIUS: 40 }));
    assert.equal(rounded.paint({ alpha: 0, highlight: false }).radius, 16);   // 높이(32)의 절반을 넘지 않음
    assert.equal(new ChatLayout(OverlayStyle.fromSettings({ BOX: true })).paint({ alpha: 0, highlight: false }).radius, 0);
  });
});

describe("결과 영상용 줄 폭", () => {
  // 가짜 측정기: 글자 하나 = 글자 크기 × (굵으면 1.1), 띄어쓰기 = 크기 × 0.3
  const measure = (text, font, px, bold) => [...text].reduce((w, ch) => w + (ch === " " ? 0.3 : 1) * px * (bold ? 1.1 : 1), 0);

  test("줄 열쇠는 Python row_key 와 같다", () => {
    assert.equal(rowKey("닉", "안녕", true), "닉\u0001안녕\u00011");
  });

  test("아이콘 · 배지 · 닉 · 대사 폭을 더하고, 이어지는 줄은 대사만", () => {
    const style = OverlayStyle.fromSettings({ ICON: "circle", BADGES_ON: true, BADGES: [MANAGER], NICK_SIZE: 20, MSG_SIZE: 10,
      MAX_CHARS_PER_LINE: 4, NICK_BOLD: true });
    const widths = new ChatLayout(style).textWidths([{ t: 0, nick: "닉", msg: "가나다라마바", color: "#fff", highlight: false }], measure);
    const icon = name => iconShape(name).width * 16 / 100;
    const first = icon("circle") + 3 + icon("shield") + 3 + (20 + 6) * 1.1 + 4 * 10;
    assert.ok(Math.abs(widths[rowKey("닉", "가나다라", false)] - first) < 0.01);
    assert.equal(widths[rowKey("", "마바", false)], 20);
  });

  test("후원 줄의 대사는 굵게 잰다", () => {
    const widths = new ChatLayout(OverlayStyle.fromSettings({ MSG_SIZE: 10 }))
      .textWidths([{ t: 0, nick: "", msg: "가", color: "#fff", highlight: true }], measure);
    assert.equal(widths[rowKey("", "가", true)], 11);
  });

  test("미리보기가 영상과 맞을 때만 보낸다", () => {
    const base = { videoPath: "v", outputPath: "o", settings: {}, events: [], textWidths: { k: 1 } };
    assert.deepEqual(buildRenderRequest({ ...base, previewMatchesVideo: true }).settings.TEXT_WIDTHS, { k: 1 });
    assert.equal("TEXT_WIDTHS" in buildRenderRequest({ ...base, previewMatchesVideo: false }).settings, false);
  });
});

describe("Settings: 박스 모양 · 배지 칸", () => {
  test("입력칸을 설정으로", () => {
    const s = Settings.fromForm({ boxShape: "rounded", boxRadius: "12", boxBorder: "2", boxBorderColor: "#FF0000",
      badgesOn: "1", badgeManagerIcon: "crown", badgeManagerColor: "#123456", badgeManagerShare: "50",
      badgeOverrides: "별빛여우 열혈팬" }, extra);
    assert.deepEqual([s.BOX_SHAPE, s.BOX_RADIUS, s.BOX_BORDER, s.BOX_BORDER_COLOR, s.BADGES_ON], ["rounded", 12, 2, "#ff0000", true]);
    assert.deepEqual(s.BADGES[0], { key: "manager", label: "매니저", icon: "crown", color: "#123456", share: 0.5 });
    assert.deepEqual(s.BADGES.slice(1), DEFAULT_BADGES.slice(1).map(b => ({ ...b })));
    assert.deepEqual(s.BADGE_OVERRIDES, { "별빛여우": "fan" });
  });

  test("기본값은 예전 모양 (각진 박스, 테두리 없음)", () => {
    const s = Settings.fromForm({}, extra);
    assert.deepEqual([s.BOX_SHAPE, s.BOX_BORDER, s.BADGES_ON], ["square", 0, false]);
    for (const key of ["boxShape", "boxRadius", "boxBorder", "boxBorderColor", "badgesOn", "badgeOverrides",
      "badgeManagerIcon", "badgeFanShare", "badgeSubColor"]) assert.ok(Settings.FIELDS.includes(key), key);
  });

  test("방패(매니저) 모양이 아이콘 목록에 있다", () => {
    assert.ok(ICON_NAMES.includes("shield"));
  });
});

describe("CHAT_TEMPLATES: 둥근 박스", () => {
  test("팬더 풍은 둥근 박스 + 테두리, 알약 박스 템플릿이 있다", () => {
    assert.equal(CHAT_TEMPLATES.panda.fields.boxShape, "rounded");
    assert.notEqual(CHAT_TEMPLATES.panda.fields.boxBorder, "0");
    assert.equal(CHAT_TEMPLATES.pill.fields.boxShape, "pill");
    assert.equal(CHAT_TEMPLATES.outline.fields.boxShape, "square");
  });
});
