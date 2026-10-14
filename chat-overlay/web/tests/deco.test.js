// 방송 꾸미기: 템플릿 · 스티커 목록 · 편집 칸 · 후원 설정
import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { TEMPLATES } from "../js/core/templates.js";
import { StickerList } from "../js/core/stickerList.js";
import { STICKER_FIELDS, formatEntries, parseEntries } from "../js/core/stickerFields.js";
import { Sticker } from "../js/core/stickers.js";
import { Settings } from "../js/core/settings.js";
import { buildRenderRequest } from "../js/core/export.js";

describe("TEMPLATES", () => {
  test("팬더티비 템플릿: 스티커가 모두 올바르고 알림 자리 · 순위판 · 게이지 · 배너 · 글자 스티커가 있다", () => {
    const panda = TEMPLATES.panda;
    assert.equal(panda.label, "팬더티비 방송");
    const types = panda.stickers.map(s => Sticker.fromObject(s).type);
    for (const t of ["alert", "ranking", "goal", "banner", "text"]) assert.ok(types.includes(t), t);
    assert.ok(panda.donation.on);
  });

  test("스티커가 화면 안에 있다", () => {
    for (const t of Object.values(TEMPLATES)) {
      for (const s of t.stickers) assert.ok(s.x > 0 && s.x < 1 && s.y > 0 && s.y < 1, JSON.stringify(s));
    }
  });

  test("엑셀방송 템플릿: 엑셀 표 · 별풍선 목표 · 순위 · 이벤트 공지 · 알림", () => {
    const excel = TEMPLATES.excel;
    assert.equal(excel.label, "엑셀방송");
    const types = excel.stickers.map(s => Sticker.fromObject(s).type);
    for (const t of ["table", "goal", "ranking", "banner", "alert", "text"]) assert.ok(types.includes(t), t);
    assert.match(excel.stickers.find(s => s.type === "goal").title, /별풍선/);
  });

  test("엑셀방송 템플릿의 스티커는 오른쪽 아래 채팅 자리를 가리지 않는다", () => {
    // 채팅은 기본으로 오른쪽 아래 (가로 0.6~1, 세로 0.7~1) 에 쌓인다
    for (const s of TEMPLATES.excel.stickers) {
      if (s.type === "alert") continue;
      assert.ok(!(s.x > 0.6 && s.y > 0.7), JSON.stringify(s));
    }
  });

  test("아프리카TV 템플릿: 후원 카드 더미 · MVP · BJ 배너 · 알림", () => {
    const af = TEMPLATES.afreeca;
    assert.equal(af.label, "아프리카TV 방송");
    const types = af.stickers.map(s => Sticker.fromObject(s).type);
    for (const t of ["history", "mvp", "banner", "alert"]) assert.ok(types.includes(t), t);
  });

  test("아프리카TV 템플릿의 스티커도 오른쪽 아래 채팅 자리를 가리지 않는다", () => {
    for (const s of TEMPLATES.afreeca.stickers) {
      if (s.type === "alert") continue;
      assert.ok(!(s.x > 0.6 && s.y > 0.7), JSON.stringify(s));
    }
  });

  test("템플릿마다 고른 스티커가 모두 올바르다", () => {
    for (const t of Object.values(TEMPLATES)) for (const s of t.stickers) Sticker.fromObject(s);
  });
});

describe("StickerList", () => {
  test("추가하면 id 가 붙고 선택된다", () => {
    const list = new StickerList();
    const id = list.add({ type: "text", text: "별사" });
    assert.ok(id);
    assert.equal(list.selectedId, id);
    assert.equal(list.items[0].text, "별사");
  });

  test("이동은 화면 안으로, 크기는 허용 범위로", () => {
    const list = new StickerList();
    const id = list.add({ type: "text" });
    list.moveTo(id, 1.4, -0.2);
    assert.deepEqual([list.get(id).x, list.get(id).y], [1, 0]);
    list.scaleBy(id, 100);
    assert.equal(list.get(id).scale, StickerList.MAX_SCALE);
    list.scaleBy(id, 0.0001);
    assert.equal(list.get(id).scale, StickerList.MIN_SCALE);
  });

  test("수정 · 삭제 · 알림", () => {
    const list = new StickerList();
    let n = 0;
    list.subscribe(() => n++);
    const id = list.add({ type: "goal" });
    list.update(id, { title: "목표!" });
    list.update(id, { current: 5 }, { notify: false });
    assert.equal(list.get(id).current, 5);
    list.remove(id);
    assert.equal(list.items.length, 0);
    assert.equal(list.selectedId, null);
    assert.equal(n, 3);
  });

  test("템플릿으로 통째로 바꾸고, JSON 으로 저장 · 복원", () => {
    const list = new StickerList();
    list.replaceAll(TEMPLATES.panda.stickers);
    assert.equal(list.items.length, TEMPLATES.panda.stickers.length);
    const copy = new StickerList();
    copy.load(JSON.parse(JSON.stringify(list.toJSON())));
    assert.deepEqual(copy.toJSON(), list.toJSON());
  });

  test("깨진 저장값은 건너뛴다", () => {
    const list = new StickerList();
    list.load([{ type: "text" }, { type: "우주선" }, null, "x"]);
    assert.equal(list.items.length, 1);
  });

  test("알림 자리는 하나만", () => {
    const list = new StickerList();
    list.add({ type: "alert" });
    list.add({ type: "alert" });
    assert.equal(list.items.filter(s => s.type === "alert").length, 1);
  });
});

describe("STICKER_FIELDS", () => {
  test("모든 편집 칸은 그 스티커의 실제 속성이다", () => {
    for (const cls of Sticker.types()) {
      const fields = STICKER_FIELDS[cls.TYPE];
      assert.ok(fields && fields.length, cls.TYPE);
      for (const f of fields) assert.ok(f.key in { ...Sticker.BASE, ...cls.DEFAULTS }, `${cls.TYPE}.${f.key}`);
    }
  });

  test("순위 목록 글 ↔ 배열", () => {
    assert.deepEqual(parseEntries("별사 6558\n갓스 5,326\n\n이름 띄어 쓴 닉 10\n숫자없음"),
      [["별사", 6558], ["갓스", 5326], ["이름 띄어 쓴 닉", 10], ["숫자없음", 0]]);
    assert.equal(formatEntries([["별사", 6558], ["갓스", 5]]), "별사 6558\n갓스 5");
  });
});

describe("Settings: 후원 설정", () => {
  const extra = { colors: [], phases: [0, 0, 0], sections: [] };

  test("후원 칸을 설정으로", () => {
    const s = Settings.fromForm({ donationsOn: "1", donationEvery: "12", donationAmounts: "10, 50,100 ,abc, 550",
      donationMsgChance: "40", donationUnit: " 별풍선 " }, extra);
    assert.deepEqual([s.DONATIONS_ON, s.DONATION_EVERY, s.DONATION_MSG_CHANCE, s.DONATION_UNIT], [true, 12, 0.4, "별풍선"]);
    assert.deepEqual(s.DONATION_AMOUNTS, [10, 50, 100, 550]);
  });

  test("기본값", () => {
    const s = Settings.fromForm({}, extra);
    assert.equal(s.DONATIONS_ON, false);
    assert.equal(s.DONATION_UNIT, "하트");
    assert.ok(s.DONATION_AMOUNTS.length > 0);
  });
});

describe("export: 스티커 · 후원", () => {
  test("스티커는 항상, 후원 목록은 미리보기가 영상 길이일 때만 보낸다", () => {
    const base = { videoPath: "v", outputPath: "o", settings: {}, events: [], stickers: [{ type: "text" }],
      donations: [{ t: 1, nick: "a", amount: 10, msg: "" }] };
    const matched = buildRenderRequest({ ...base, previewMatchesVideo: true }).settings;
    assert.deepEqual(matched.STICKERS, [{ type: "text" }]);
    assert.deepEqual(matched.DONATIONS, [{ t: 1, nick: "a", amount: 10, msg: "" }]);
    const fallback = buildRenderRequest({ ...base, previewMatchesVideo: false }).settings;
    assert.deepEqual(fallback.STICKERS, [{ type: "text" }]);
    assert.equal("DONATIONS" in fallback, false);
  });
});
