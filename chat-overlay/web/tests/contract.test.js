// shared/contract.json (Python 이 만든 기준값) 과 브라우저 계산이 같은지 확인한다.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { Mulberry32 } from "../js/core/rng.js";
import { wrapText, Color, colorForNick } from "../js/core/text.js";
import { SpeedCurve } from "../js/core/speed.js";
import { EventGenerator } from "../js/core/events.js";
import { ChatLayout, OverlayStyle, boxAlpha } from "../js/core/layout.js";
import { ICON_NAMES, iconShape } from "../js/core/icons.js";
import { badgeFor, nickHash } from "../js/core/badges.js";

const contract = JSON.parse(readFileSync(new URL("../../shared/contract.json", import.meta.url), "utf-8"));
const close = (a, b, eps = 1e-9) => Math.abs(a - b) <= eps;

test("rng: Python 과 같은 수열", () => {
  for (const { seed, values } of contract.rng) {
    const r = new Mulberry32(seed);
    assert.deepEqual(values.map(() => r.next()), values);
  }
});

test("wrap: 같은 줄바꿈", () => {
  for (const { text, max, lines } of contract.wrap) assert.deepEqual(wrapText(text, max), lines);
});

test("color: 같은 색 해석", () => {
  for (const c of contract.color) assert.equal(Color.parse(c.in).toHex(), c.hex);
});

test("nick color: 이모지 닉도 Python 과 같은 색", () => {
  for (const c of contract.nickColor) assert.equal(colorForNick(c.nick, c.palette), c.color);
});

test("speed: 같은 속도 곡선", () => {
  for (const { cfg, points } of contract.speed) {
    const curve = SpeedCurve.fromSettings(cfg);
    for (const [t, v] of points) assert.ok(close(curve.at(t), v, 1e-9), `t=${t}: ${curve.at(t)} != ${v}`);
  }
});

test("events: 같은 시드면 같은 채팅 타임라인", () => {
  for (const { seed, duration, cfg, events } of contract.events) {
    const got = EventGenerator.fromSettings(cfg, seed).generate(duration);
    assert.equal(got.length, events.length);
    got.forEach((e, i) => {
      assert.equal(e.nick, events[i].nick);
      assert.equal(e.msg, events[i].msg);
      assert.equal(e.color, events[i].color);
      assert.ok(close(e.t, events[i].t, 1e-6), `#${i}: ${e.t} != ${events[i].t}`);
    });
  }
});

test("layout: 같은 줄 배치", () => {
  const { style, events, frames } = contract.layout;
  const layout = new ChatLayout(OverlayStyle.fromSettings(style));
  frames.forEach((rows, i) => {
    const got = layout.rowsAt(events, i).map(r => ({
      nick: r.nick, msg: r.msg, color: r.color, age: r.age, alpha: r.alpha,
      is_newest: r.isNewest, is_oldest: r.isOldest, highlight: r.highlight,
    }));
    assert.deepEqual(got, rows);
  });
});

const camel = s => s.replace(/_([a-z])/g, (_, c) => c.toUpperCase());

test("style: 기본값이 Python 과 같다 (오른쪽 아래 구석)", () => {
  const js = OverlayStyle.fromSettings({});
  for (const [key, value] of Object.entries(contract.styleDefaults)) {
    assert.deepEqual(js[camel(key)], value, key);
  }
});

test("position: 같은 자리에 줄을 놓는다", () => {
  for (const { cfg, width, height, points } of contract.positions) {
    const layout = new ChatLayout(OverlayStyle.fromSettings(cfg));
    for (const [age, [x, y, align]] of points) {
      assert.deepEqual(layout.position({ age }, width, height), { x, y, align }, JSON.stringify(cfg));
    }
  }
});

test("box alpha: 박스 흐림 계산이 같다", () => {
  for (const [opacity, alpha, expected] of contract.boxAlpha) assert.equal(boxAlpha(opacity, alpha), expected);
});

test("icons: 같은 모양과 폭", () => {
  assert.deepEqual(ICON_NAMES, Object.keys(contract.icons));
  const nums = p => (p.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);
  for (const [name, { path, width }] of Object.entries(contract.icons)) {
    const shape = iconShape(name);
    assert.ok(close(shape.width, width, 1e-6), name);
    const a = nums(shape.path), b = nums(path);
    assert.equal(a.length, b.length, name);
    a.forEach((v, i) => assert.ok(close(v, b[i], 0.011), `${name} #${i}: ${v} != ${b[i]}`));
  }
});

import { roundedRectDrawing, ringDrawing } from "../js/core/shapes.js";
import { Sticker, StickerState } from "../js/core/stickers.js";
import { DonationGenerator, Donation, mergeIntoChat, scheduleAlerts, alertScale, alertOpacity, formatGift, donationChatText } from "../js/core/donations.js";

test("shapes: 같은 둥근 사각형 · 테두리 경로", () => {
  for (const { args, rect, ring } of contract.shapes) {
    assert.equal(roundedRectDrawing(...args), rect, JSON.stringify(args));
    assert.equal(ringDrawing(...args, 3), ring, JSON.stringify(args));
  }
});

// JS 도형(camelCase) 을 Python 도형(snake_case) 모양으로
function toPy(p) {
  if (p.kind === "text") {
    return { kind: "text", x: p.x, y: p.y, align: p.align, lines: p.lines.map(l => l.map(r => ({ ...r }))),
      outline_w: p.outlineW, outline_color: p.outlineColor, layer: p.layer };
  }
  if (p.kind === "rect") {
    return { kind: "rect", cx: p.cx, cy: p.cy, w: p.w, h: p.h, r: p.r, color: p.color, opacity: p.opacity,
      border_w: p.borderW, border_color: p.borderColor, layer: p.layer };
  }
  return { kind: "image", cx: p.cx, cy: p.cy, w: p.w, h: p.h, path: p.path, url: p.url };
}

test("stickers: 같은 도형 목록 (위치 · 크기 · 글자)", () => {
  for (const { sticker, width, height, state, prims } of contract.stickers) {
    const ds = (state.donations || []).map(d => new Donation(d.t, d.nick, d.amount, d.msg));
    const got = Sticker.fromObject(sticker).layout(width, height, new StickerState(new Map(Object.entries(state.totals)), state.total, ds, state.unit, state.platform));
    assert.deepEqual(got.map(toPy), prims, `${JSON.stringify(sticker)} @${width}x${height} ${JSON.stringify(state)}`);
  }
});

test("alerts: 같은 후원 알림 도형", () => {
  for (const { sticker, donation, width, height, state, prims } of contract.alerts) {
    const d = new Donation(donation.t, donation.nick, donation.amount, donation.msg);
    const st = new StickerState(new Map(), 0, [], state.unit, state.platform);
    assert.deepEqual(Sticker.fromObject(sticker).layoutAlert(width, height, d, st).map(toPy), prims,
      `${JSON.stringify(sticker)} ${state.platform}`);
  }
});

test("donations: 같은 시드면 같은 후원", () => {
  for (const { seed, duration, cfg, donations } of contract.donations) {
    const got = DonationGenerator.fromSettings(cfg, seed).generate(duration);
    assert.deepEqual(got.map(d => ({ ...d })), donations);
  }
});

test("merged: 후원 줄을 같은 자리에 끼워 넣는다", () => {
  const chat = [{ t: 1.0, nick: "x", msg: "ㅋㅋ", color: "#111111", highlight: false },
    { t: 3.0, nick: "y", msg: "와", color: "#222222", highlight: false }];
  const got = mergeIntoChat(chat, [new Donation(3.0, "별사", 1550, "화이팅"), new Donation(0.5, "갓스", 10, "")],
    ["#ff0000", "#00ff00"], "하트");
  assert.deepEqual(got.map(e => ({ t: e.t, nick: e.nick, msg: e.msg, color: e.color, highlight: e.highlight })), contract.merged);
});

test("alert schedule · animation: 같은 일정과 움직임", () => {
  const ds = [["a", 1.0], ["b", 2.0], ["c", 20.0], ["d", 58.5]].map(([n, t]) => new Donation(t, n, 1, ""));
  assert.deepEqual(scheduleAlerts(ds, 60, 4.0, 0.3).map(s => [s.start, s.end, s.donation.nick]), contract.alertSchedule);
  for (const [ms, scale, opacity] of contract.alertAnim) {
    assert.ok(close(alertScale(ms), scale, 1e-9), `scale ${ms}`);
    assert.ok(close(alertOpacity(ms, 4000), opacity, 1e-9), `opacity ${ms}`);
  }
});

test("badges: 같은 닉 해시 · 같은 배지", () => {
  for (const [nick, h] of contract.badges.hashes) assert.equal(nickHash(nick), h, nick);
  for (const { badges, overrides, picks } of contract.badges.cases) {
    for (const [nick, key] of picks) assert.equal(badgeFor(nick, badges, overrides)?.key ?? "", key, nick);
  }
});

test("gifts: 같은 후원 금액 표기 (개수 · 돈)", () => {
  for (const [amount, unit, gift, chat] of contract.gifts) {
    assert.equal(formatGift(amount, unit), gift);
    const msg = chat.includes("! ") ? chat.split("! ").slice(1).join("! ") : "";
    assert.equal(donationChatText(new Donation(0, "x", amount, msg), unit), chat);
  }
});
