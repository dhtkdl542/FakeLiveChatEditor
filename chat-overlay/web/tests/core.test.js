// 계약 파일에 없는 브라우저 전용 동작 테스트
import { test } from "node:test";
import assert from "node:assert/strict";

import { Mulberry32 } from "../js/core/rng.js";
import { normalizeHex, randomColor } from "../js/core/text.js";
import { SpeedCurve, SpeedSection } from "../js/core/speed.js";
import { EventCache, EventGenerator } from "../js/core/events.js";
import { ChatLayout, OverlayStyle } from "../js/core/layout.js";

test("normalizeHex: 3자리 확장, 잘못된 값은 null", () => {
  assert.equal(normalizeHex("FA0"), "#ffaa00");
  assert.equal(normalizeHex(" #47B3FF "), "#47b3ff");
  assert.equal(normalizeHex("zz"), null);
});

test("randomColor: 시드 난수로 밝은 색", () => {
  const c = randomColor(new Mulberry32(1));
  assert.match(c, /^#[0-9a-f]{6}$/);
  assert.equal(c, randomColor(new Mulberry32(1)));
});

test("SpeedSection.fromObject: 빈 구간은 버린다", () => {
  assert.equal(SpeedSection.fromObject({ start: 2, end: 2, speed: 3 }), null);
  assert.equal(SpeedSection.fromObject({ start: 1, end: 2, speed: 0 }).speed, SpeedSection.MIN_SPEED);
});

test("SpeedCurve: 구간이 출렁임에 곱해진다", () => {
  const curve = new SpeedCurve({ amplitude: 0, period: 8, phases: [0, 0, 0], sections: [new SpeedSection(2, 6, 3)] });
  assert.equal(curve.at(4), 3);
  assert.equal(curve.at(1), 1);
});

const cfg = { NICKS: ["a", "b"], MSGS: ["x", "y"], COLORS: ["#ff0000"], CHAT_START: 0.5, INTERVAL_MIN: 0.25,
  INTERVAL_MAX: 0.7, SPEED_VAR: 0, SPEED_PERIOD: 8, SPEED_PHASES: [0, 0, 0], SPEED_SECTIONS: [] };

test("EventGenerator: 목록이 비면 빈 타임라인", () => {
  assert.deepEqual(EventGenerator.fromSettings({ ...cfg, MSGS: [] }, 1).generate(10), []);
});

test("EventCache: 입력이 같으면 다시 만들지 않는다", () => {
  let built = 0;
  const cache = new EventCache((c, seed, len) => { built++; return EventGenerator.fromSettings(c, seed).generate(len); });
  const a = cache.get(cfg, 1, 10);
  assert.equal(cache.get({ ...cfg }, 1, 10), a);
  assert.equal(built, 1);
  cache.get(cfg, 2, 10);
  cache.get({ ...cfg, SPEED_SECTIONS: [{ start: 1, end: 3, speed: 2 }] }, 2, 10);
  assert.equal(built, 3);
});

test("ChatLayout.frameAt: 지금 시각의 줄과 다음 채팅 시각", () => {
  const layout = new ChatLayout(OverlayStyle.fromSettings({ VISIBLE: 3 }));
  const events = [0, 1, 2].map(t => ({ t, nick: "n", msg: "m" + t, color: "#fff" }));
  assert.deepEqual(layout.frameAt(events, -1, 10), { index: -1, rows: [], startT: null, nextT: null });
  const f = layout.frameAt(events, 1.5, 10);
  assert.equal(f.index, 1);
  assert.deepEqual(f.rows.map(r => r.msg), ["m0", "m1"]);
  assert.equal(f.startT, 1);
  assert.equal(f.nextT, 2);
  assert.equal(layout.frameAt(events, 5, 10).nextT, 10);
});

test("ChatLayout.fade: 새 줄은 서서히 나타나고 꽉 찼을 때 맨 윗줄은 사라진다 (ASS \fad)", () => {
  const layout = new ChatLayout(OverlayStyle.fromSettings({ VISIBLE: 2, FADE_IN_MS: 200, FADE_OUT_MS: 400 }));
  assert.ok(Math.abs(layout.fade({ isNewest: true, isOldest: false }, 1.1, 1.0, 3.0) - 0.5) < 1e-9);
  assert.ok(Math.abs(layout.fade({ isNewest: false, isOldest: true }, 2.8, 1.0, 3.0) - 0.5) < 1e-9);
  assert.equal(layout.fade({ isNewest: false, isOldest: false }, 2.8, 1.0, 3.0), 1);
});

test("ChatLayout.paint: 글자 흐림과 박스 배경색", () => {
  const plain = new ChatLayout(OverlayStyle.fromSettings({}));
  assert.deepEqual(plain.paint({ alpha: 51 }), { textOpacity: 0.8, background: null, radius: 0, border: null });
  const boxed = new ChatLayout(OverlayStyle.fromSettings({ BOX: true, BOX_COLOR: "#102030", BOX_OPACITY: 0.5 }));
  const p = boxed.paint({ alpha: 0 });
  assert.equal(p.textOpacity, 1);
  assert.equal(p.background, `rgba(16,32,48,${(255 - 128) / 255})`);
});

test("ChatLayout.position: 오른쪽 아래 모서리 기준 (ASS \an3 와 같은 자리)", () => {
  const layout = new ChatLayout(OverlayStyle.fromSettings({ SIDE_MARGIN: 24, BOTTOM_MARGIN: 24, LINE_H: 30 }));
  assert.deepEqual(layout.position({ age: 1 }, 1000, 600), { x: 976, y: 546, align: "right" });
});

test("ChatLayout.iconSize: 닉네임 크기 × 0.8 × 배율", () => {
  const layout = new ChatLayout(OverlayStyle.fromSettings({ NICK_SIZE: 20, ICON_SCALE: 1.5 }));
  assert.ok(Math.abs(layout.iconSize() - 24) < 1e-9);
});

import { iconSvgPath } from "../js/core/icons.js";
import { cssFontPx } from "../js/core/fontmetrics.js";

test("iconSvgPath: ASS 드로잉 명령을 SVG 경로로", () => {
  assert.equal(iconSvgPath("diamond"), "M 50 0 L 100 50 L 50 100 L 0 50 Z");
  assert.match(iconSvgPath("circle"), /^M 50 0 C 77\.6 0 100 22\.4 100 50 C /);
  assert.equal(iconSvgPath("banana"), "");
});

test("cssFontPx: libass 글자 크기(윗선~아랫선 높이)를 CSS 글자 크기로", () => {
  assert.ok(Math.abs(cssFontPx(18, 1.33) - 18 / 1.33) < 1e-9);
  assert.equal(cssFontPx(18, 0), 18);
});
