// 플랫폼(후원 단위 · 금액 · 후원창) / 방송 템플릿(스티커) / 채팅창 템플릿(채팅 모양) 은 따로 고른다
import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { PLATFORMS, DEFAULT_PLATFORM, platformOf, platformFields } from "../js/core/platforms.js";
import { TEMPLATES } from "../js/core/templates.js";
import { CHAT_TEMPLATES } from "../js/core/presets.js";
import { STICKER_FIELDS } from "../js/core/stickerFields.js";
import { AlertSticker, Sticker, StickerState } from "../js/core/stickers.js";
import { Donation } from "../js/core/donations.js";
import { Settings } from "../js/core/settings.js";
import { ICON_NAMES } from "../js/core/icons.js";

const extra = { colors: [], phases: [0, 0, 0], sections: [] };

describe("PLATFORMS", () => {
  test("팬더티비는 하트, 아프리카TV 는 별풍선, 유튜브는 원화(₩)", () => {
    assert.deepEqual(Object.keys(PLATFORMS), ["panda", "afreeca", "youtube"]);
    assert.equal(PLATFORMS.panda.unit, "하트");
    assert.equal(PLATFORMS.afreeca.unit, "별풍선");
    assert.equal(PLATFORMS.youtube.unit, "₩");
    assert.equal(DEFAULT_PLATFORM, "panda");
  });

  test("플랫폼마다 이름 · 금액 목록 · 후원창 모양이 있다", () => {
    for (const [key, p] of Object.entries(PLATFORMS)) {
      assert.ok(p.label, key);
      assert.ok(p.amounts.length >= 5 && p.amounts.every(a => Number.isInteger(a) && a > 0), key);
      assert.ok(p.alert in AlertSticker.STYLES && p.alert !== "", key);
    }
    for (const n of [486, 4860]) assert.ok(PLATFORMS.afreeca.amounts.includes(n), String(n));
    assert.ok(PLATFORMS.youtube.amounts.every(a => a >= 1000), "슈퍼챗은 천 원부터");
  });

  test("모르는 플랫폼은 기본(팬더)으로", () => {
    assert.equal(platformOf("twitch"), PLATFORMS.panda);
    assert.equal(platformOf("youtube"), PLATFORMS.youtube);
  });

  test("플랫폼을 바꾸면 단위 · 금액 칸이 그 플랫폼 기본값으로", () => {
    assert.deepEqual(platformFields("youtube"), {
      platform: "youtube", donationUnit: "₩", donationAmounts: PLATFORMS.youtube.amounts.join(", ") });
    assert.equal(platformFields("뭐지").platform, "panda");
  });
});

describe("Settings: 플랫폼", () => {
  test("플랫폼 칸을 설정으로, 모르는 값은 팬더", () => {
    assert.ok(Settings.FIELDS.includes("platform"));
    assert.equal(Settings.fromForm({ platform: "afreeca" }, extra).PLATFORM, "afreeca");
    assert.equal(Settings.fromForm({ platform: "x" }, extra).PLATFORM, "panda");
    assert.equal(Settings.fromForm({}, extra).PLATFORM, "panda");
  });

  test("단위 · 금액을 비우면 플랫폼 기본값, 적으면 사용자가 적은 값", () => {
    const yt = Settings.fromForm({ platform: "youtube" }, extra);
    assert.equal(yt.DONATION_UNIT, "₩");
    assert.deepEqual(yt.DONATION_AMOUNTS, PLATFORMS.youtube.amounts);
    const mine = Settings.fromForm({ platform: "youtube", donationUnit: "달러", donationAmounts: "5, 7" }, extra);
    assert.equal(mine.DONATION_UNIT, "달러");
    assert.deepEqual(mine.DONATION_AMOUNTS, [5, 7]);
  });
});

describe("TEMPLATES (방송 템플릿)", () => {
  test("템플릿마다 기본 플랫폼이 있다 (엑셀방송은 아프리카 기본, 유튜브로 바꿀 수 있다)", () => {
    assert.equal(TEMPLATES.panda.platform, "panda");
    assert.equal(TEMPLATES.excel.platform, "afreeca");
    assert.equal(TEMPLATES.afreeca.platform, "afreeca");
    for (const t of Object.values(TEMPLATES)) assert.ok(t.platform in PLATFORMS);
  });

  test("단위 · 금액은 템플릿이 아니라 플랫폼이 정한다", () => {
    for (const [key, t] of Object.entries(TEMPLATES)) {
      assert.equal("unit" in t.donation, false, key);
      assert.equal("amounts" in t.donation, false, key);
      for (const s of t.stickers) assert.ok(!s.unit, `${key}: ${s.type} 는 플랫폼 단위를 따라간다`);
      for (const s of t.stickers) assert.ok(!s.style, `${key}: ${s.type} 는 플랫폼 후원창을 따라간다`);
    }
  });

  test("엑셀방송 + 유튜브: 알림이 슈퍼챗 모양에 ₩ 금액", () => {
    const alert = Sticker.fromObject(TEMPLATES.excel.stickers.find(s => s.type === "alert"));
    const state = StickerState.at([], 0, PLATFORMS.youtube.unit, "youtube");
    const prims = alert.layoutAlert(1920, 1080, new Donation(1, "소다", 10000, "축하해요"), state);
    const texts = prims.filter(p => p.kind === "text").flatMap(p => p.lines.flat().map(r => r.text));
    assert.ok(texts.includes("₩10,000"), texts.join("|"));
    assert.equal(prims[0].color, "#ffca28");  // 1만 원대 노랑 슈퍼챗
  });
});

describe("CHAT_TEMPLATES (채팅창 템플릿)", () => {
  test("팬더 · 아프리카 · 유튜브 풍 채팅창이 있고, 예전 빠른 모양도 그대로 앞에 있다", () => {
    const keys = Object.keys(CHAT_TEMPLATES);
    assert.deepEqual(keys.slice(0, 4), ["outline", "box", "boxIcon", "heart"]);
    for (const k of ["panda", "afreeca", "youtube"]) assert.ok(keys.includes(k), k);
  });

  test("아는 입력칸만, 모두 같은 칸을 바꾼다 (차례로 골라도 앞 템플릿이 남지 않는다)", () => {
    const first = Object.keys(Object.values(CHAT_TEMPLATES)[0].fields).sort();
    for (const [name, t] of Object.entries(CHAT_TEMPLATES)) {
      assert.ok(t.label, name);
      for (const key of Object.keys(t.fields)) assert.ok(Settings.FIELDS.includes(key), `${name}: ${key}`);
      assert.deepEqual(Object.keys(t.fields).sort(), first, name);
      assert.ok(t.fields.icon === "" || ICON_NAMES.includes(t.fields.icon), name);
    }
  });

  test("채팅창 템플릿은 대사 · 후원 · 플랫폼을 건드리지 않는다", () => {
    for (const t of Object.values(CHAT_TEMPLATES)) {
      for (const key of ["nicks", "msgs", "platform", "donationUnit", "donationAmounts", "donationsOn"]) {
        assert.equal(key in t.fields, false, key);
      }
    }
  });

  test("유튜브 풍은 닉 색 동그라미 아이콘 + 박스", () => {
    const s = Settings.fromForm(CHAT_TEMPLATES.youtube.fields, extra);
    assert.equal(s.ICON, "circle");
    assert.equal(s.ICON_COLOR, "");
    assert.equal(s.BOX, true);
  });
});

describe("STICKER_FIELDS: 후원창 모양 고르기", () => {
  test("알림 스티커는 모양을 고르는 칸이 있고, 보기는 AlertSticker.STYLES", () => {
    const style = STICKER_FIELDS.alert.find(f => f.key === "style");
    assert.equal(style.input, "select");
    assert.deepEqual(style.options, AlertSticker.STYLES);
  });

  test("단위 칸은 비우면 플랫폼 단위를 쓴다고 알려준다", () => {
    for (const type of ["alert", "history"]) {
      assert.match(STICKER_FIELDS[type].find(f => f.key === "unit").label, /비우면 플랫폼/);
    }
  });
});
