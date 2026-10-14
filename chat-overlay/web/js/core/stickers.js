// 방송 화면 스티커를 기본 도형 목록으로. chatov/stickers.py 와 같은 계산 (계산 순서까지 맞춰야 소수점이 같다).
import { formatCount, formatGift, isMoney } from "./donations.js";
import { wrapText } from "./text.js";

export const REF_H = 1080;
export const r2 = v => Math.floor(v * 100 + 0.5) / 100;

const run = (text, size, color, bold, font) => Object.freeze({ text, size, color, bold, font });

function textPrim(x, y, align, runs, layer = 2, outlineW = 0, outlineColor = "", extraLines = []) {
  return Object.freeze({ kind: "text", x: r2(x), y: r2(y), align, lines: [runs, ...extraLines],
    outlineW: r2(outlineW), outlineColor, layer });
}

function rectPrim(cx, cy, w, h, r, color, opacity, borderW, borderColor, layer) {
  return Object.freeze({ kind: "rect", cx, cy, w, h, r, color, opacity, borderW, borderColor, layer });
}

/** 지금까지 들어온 후원 합계 + 플랫폼 (단위 · 후원창 모양) */
export class StickerState {
  constructor(totals = new Map(), total = 0, donations = [], unit = "하트", platform = "panda") {
    this.totals = totals;
    this.total = total;
    this.donations = donations;
    this.unit = unit;          // 스티커 단위가 비어 있으면 이걸 쓴다
    this.platform = platform;  // 후원창 모양이 비어 있으면 이걸 따라간다
  }

  static at(donations, t, unit = "하트", platform = "panda") {
    const totals = new Map();
    const arrived = donations.filter(d => d.t <= t);
    for (const d of arrived) totals.set(d.nick, (totals.get(d.nick) || 0) + d.amount);
    let total = 0;
    for (const v of totals.values()) total += v;
    return new StickerState(totals, total, arrived, unit, platform);
  }

  static EMPTY = new StickerState();
}

const TYPES = {};

export class Sticker {
  static BASE = { x: 0.5, y: 0.5, scale: 1 };
  static DEFAULTS = {};
  static LABEL = "스티커";

  constructor(o) {
    const defaults = { ...Sticker.BASE, ...this.constructor.DEFAULTS };
    for (const [key, def] of Object.entries(defaults)) {
      let v = o[key] ?? def;
      if (typeof def === "boolean") v = Boolean(v);
      else if (typeof def === "number") v = Number(v);
      this[key] = v;
    }
    this.type = this.constructor.TYPE;
    this.id = o.id || null;
  }

  static register(cls) {
    TYPES[cls.TYPE] = cls;
  }

  static fromObject(o) {
    const cls = TYPES[o.type];
    if (!cls) throw new Error(`모르는 스티커 종류: ${o.type}`);
    return new cls(o);
  }

  static types() {
    return Object.values(TYPES);
  }

  get dynamic() {
    return false;
  }

  k(height) {
    return height / REF_H * this.scale;
  }

  center(width, height) {
    return [this.x * width, this.y * height];
  }

  layout() {
    return [];
  }

  toObject() {
    const out = { type: this.type };
    if (this.id) out.id = this.id;
    for (const key of Object.keys({ ...Sticker.BASE, ...this.constructor.DEFAULTS })) out[key] = this[key];
    return out;
  }
}

export class TextSticker extends Sticker {
  static TYPE = "text";
  static LABEL = "글자 스티커";
  static DEFAULTS = { text: "별사", heart: true, font: "Malgun Gothic", size: 56, fill: "#b07cff", inner: "#ffffff",
    outer: "#6a3fb5", innerWidth: 6, outerWidth: 3, heartColor: "#ff5fa2", x: 0.1 };
  static HEART_EM = 0.7;

  layout(width, height) {
    const k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const runs = [run(this.text, r2(this.size * k), this.fill, true, this.font)];
    if (this.heart) runs.push(run("♡", r2(this.size * k * TextSticker.HEART_EM), this.heartColor, true, this.font));
    return [
      textPrim(cx, cy, "center", runs, 2, (this.innerWidth + this.outerWidth) * k, this.outer),
      textPrim(cx, cy, "center", runs, 3, this.innerWidth * k, this.inner),
    ];
  }
}

const PANEL = { font: "Malgun Gothic", bg: "#ffffff", bgOpacity: 0.92, borderWidth: 2, borderColor: "#ff5fa2",
  accent: "#ff5fa2", textColor: "#333333", radius: 14 };

class PanelSticker extends Sticker {
  box(cx, cy, w, h, k, layer = 0) {
    return rectPrim(r2(cx), r2(cy), r2(w), r2(h), r2(this.radius * k), this.bg, this.bgOpacity,
      r2(this.borderWidth * k), this.borderColor, layer);
  }

  run(text, size, k, color = null, bold = false) {
    return run(text, r2(size * k), color || this.textColor, bold, this.font);
  }
}

export class RankingSticker extends PanelSticker {
  static TYPE = "ranking";
  static LABEL = "후원 순위판";
  static DEFAULTS = { ...PANEL, title: "오늘의 후원 순위", rows: 5, width: 300, auto: true, x: 0.86, y: 0.35,
    entries: [["별사", 6558], ["갓스", 5326], ["워린", 1452], ["소다", 1080], ["뭉치", 655]] };
  static P = 14; static TH = 38; static RH = 30; static T = 22; static R = 18; static NICK_X = 52;

  get dynamic() {
    return this.auto;
  }

  standings(state) {
    const totals = new Map();
    for (const [nick, amount] of this.entries) totals.set(String(nick), (totals.get(String(nick)) || 0) + Math.trunc(Number(amount)));
    if (this.auto) for (const [nick, amount] of state.totals) totals.set(nick, (totals.get(nick) || 0) + amount);
    return [...totals].sort((a, b) => b[1] - a[1]).slice(0, Math.trunc(this.rows));
  }

  layout(width, height, state = StickerState.EMPTY) {
    const C = RankingSticker, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const rows = this.standings(state);
    const w = this.width * k, h = (2 * C.P + C.TH + rows.length * C.RH) * k;
    const left = cx - w / 2, top = cy - h / 2, right = cx + w / 2;
    const prims = [this.box(cx, cy, w, h, k),
      textPrim(left + C.P * k, top + (C.P + C.TH / 2) * k, "left", [this.run(this.title, C.T, k, this.accent, true)])];
    rows.forEach(([nick, amount], i) => {
      const y = top + (C.P + C.TH + C.RH * i + C.RH / 2) * k;
      prims.push(
        textPrim(left + C.P * k, y, "left", [this.run(`${i + 1}등`, C.R, k, this.accent, true)]),
        textPrim(left + (C.P + C.NICK_X) * k, y, "left", [this.run(nick, C.R, k)]),
        textPrim(right - C.P * k, y, "right", [this.run(formatCount(amount), C.R, k, null, true)]));
    });
    return prims;
  }
}

export class GoalSticker extends PanelSticker {
  static TYPE = "goal";
  static LABEL = "목표 게이지";
  static DEFAULTS = { ...PANEL, title: "오늘의 하트 목표", current: 16719, target: 38000, width: 320, auto: true,
    track: "#f3d3e2", x: 0.86, y: 0.07 };
  static P = 14; static TR = 30; static G = 8; static B = 16; static T = 20; static V = 16;

  get dynamic() {
    return this.auto;
  }

  layout(width, height, state = StickerState.EMPTY) {
    const C = GoalSticker, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const current = Math.trunc(this.current) + (this.auto ? state.total : 0);
    const target = Math.max(1, Math.trunc(this.target));
    const w = this.width * k, h = (2 * C.P + C.TR + C.G + C.B) * k;
    const left = cx - w / 2, top = cy - h / 2, right = cx + w / 2;
    const titleY = top + (C.P + C.TR / 2) * k;
    const barY = top + (C.P + C.TR + C.G + C.B / 2) * k;
    const trackW = (this.width - 2 * C.P) * k, barH = C.B * k;
    const prims = [
      this.box(cx, cy, w, h, k),
      textPrim(left + C.P * k, titleY, "left", [this.run(this.title, C.T, k, this.accent, true)]),
      textPrim(right - C.P * k, titleY, "right", [this.run(
        `${formatCount(current)} / ${formatCount(target)} (${Math.floor(current / target * 100)}%)`, C.V, k, null, true)]),
      rectPrim(r2(cx), r2(barY), r2(trackW), r2(barH), r2(barH / 2), this.track, 1, 0, "", 1),
    ];
    const fillW = trackW * Math.min(1, current / target);
    if (fillW > 0) {
      prims.push(rectPrim(r2(left + C.P * k + fillW / 2), r2(barY), r2(fillW), r2(barH), r2(Math.min(barH, fillW) / 2),
        this.accent, 1, 0, "", 2));
    }
    return prims;
  }
}

export class BannerSticker extends PanelSticker {
  static TYPE = "banner";
  static LABEL = "배너";
  static DEFAULTS = { ...PANEL, lines: ["방송시간", "오후 1시 ~ 5시", "BJ닉네임"], width: 260, x: 0.11, y: 0.14 };
  static P = 12; static FIRST = 30; static OTHER = 22; static LH = 1.35;

  layout(width, height) {
    const C = BannerSticker, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    let lines = this.lines.map(String).filter(l => l.trim());
    if (!lines.length) lines = [" "];
    const sizes = lines.map((_, i) => (i === 0 ? C.FIRST : C.OTHER));
    const h = (2 * C.P + sizes.reduce((acc, s) => acc + s * C.LH, 0)) * k;
    const top = cy - h / 2;
    const prims = [this.box(cx, cy, this.width * k, h, k)];
    let y = top + C.P * k;
    lines.forEach((line, i) => {
      const lh = sizes[i] * C.LH * k;
      prims.push(textPrim(cx, y + lh / 2, "center", [this.run(line, sizes[i], k, i === 0 ? this.accent : null, i === 0)]));
      y += lh;
    });
    return prims;
  }
}

export class TableSticker extends PanelSticker {
  static TYPE = "table";
  static LABEL = "엑셀 표";
  static DEFAULTS = { ...PANEL, title: "BJ 엑셀", headers: ["BJ", "별풍점수", "기여도"], rows: 10, auto: true,
    width: 360, highlightRow: 1, showTotal: true, headerBg: "#f6c344", headerText: "#222222",
    titleBg: "#222222", titleText: "#f6c344", cellBg: "#ffffff", cellText: "#222222",
    grid: "#3a3a3a", highlight: "#ffb6d9", totalBg: "#fff3c4", bgOpacity: 0.95, x: 0.83, y: 0.3,
    entries: [["소야", 87399], ["요아정", 77239], ["미키", 50000], ["린린", 30196], ["선유", 20217],
      ["하늘", 15410], ["다온", 9850], ["채리", 7300], ["루비", 4120], ["보라", 1900]] };
  static TITLE = 30; static HDR = 28; static RH = 26; static F = 15; static HF = 15; static TF = 18; static PAD = 8;
  static GRID = 1; static BORDER = 1.5; static RADIUS = 4;
  static COLS = [0.42, 0.30, 0.28];

  get dynamic() {
    return this.auto;
  }

  /** 후원받는 멤버: 후원자 닉 글자 코드 합 + 금액 (Python ord 와 같도록 코드 포인트로 센다) */
  static memberFor(nick, amount, n) {
    let sum = 0;
    for (const ch of nick) sum += ch.codePointAt(0);
    return (sum + Math.trunc(amount)) % n;
  }

  standings(state) {
    const scores = new Map();
    for (const [name, score] of this.entries) scores.set(String(name), (scores.get(String(name)) || 0) + Math.trunc(Number(score)));
    const names = this.entries.map(([n]) => String(n));
    if (this.auto && names.length) {
      for (const d of state.donations) {
        const name = names[TableSticker.memberFor(d.nick, d.amount, names.length)];
        scores.set(name, scores.get(name) + d.amount);
      }
    }
    let total = 0;
    for (const v of scores.values()) total += v;
    return [[...scores].sort((a, b) => b[1] - a[1]).slice(0, Math.trunc(this.rows)), total];
  }

  layout(width, height, state = StickerState.EMPTY) {
    const C = TableSticker, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const [rows, total] = this.standings(state);
    const n = rows.length + (this.showTotal ? 1 : 0);
    const th = this.title ? C.TITLE : 0;
    const w = this.width * k, h = (th + C.HDR + n * C.RH) * k;
    const left = cx - w / 2, top = cy - h / 2, right = cx + w / 2;
    const rowY = i => top + (th + C.HDR + C.RH * i + C.RH / 2) * k;
    const band = (y, hh, color) => rectPrim(r2(cx), r2(y), r2(w), r2(hh), 0, color, this.bgOpacity, 0, "", 1);
    const line = (x, y, lw, lh) => rectPrim(r2(x), r2(y), r2(lw), r2(lh), 0, this.grid, 1, 0, "", 2);
    const cell = (text, x, y, align, color, size, bold) => textPrim(x, y, align, [run(text, r2(size * k), color, bold, this.font)], 3);

    const prims = [rectPrim(r2(cx), r2(cy), r2(w), r2(h), r2(C.RADIUS * k), this.cellBg, this.bgOpacity,
      r2(C.BORDER * k), this.grid, 0)];
    if (th) prims.push(band(top + th * k / 2, th * k, this.titleBg));
    prims.push(band(top + (th + C.HDR / 2) * k, C.HDR * k, this.headerBg));
    const hr = Math.trunc(this.highlightRow);
    if (hr >= 1 && hr <= rows.length) prims.push(band(rowY(hr - 1), C.RH * k, this.highlight));
    if (this.showTotal) prims.push(band(rowY(rows.length), C.RH * k, this.totalBg));
    if (th) prims.push(line(cx, top + th * k, w, C.GRID * k));
    for (let i = 0; i < n; i++) prims.push(line(cx, top + (th + C.HDR + C.RH * i) * k, w, C.GRID * k));
    const bodyH = (C.HDR + n * C.RH) * k;
    let edge = 0;
    for (const frac of C.COLS.slice(0, -1)) {
      edge += frac;
      prims.push(line(left + w * edge, top + th * k + bodyH / 2, C.GRID * k, bodyH));
    }

    if (th) prims.push(cell(this.title, cx, top + th * k / 2, "center", this.titleText, C.TF, true));
    const headerY = top + (th + C.HDR / 2) * k;
    const headers = [...this.headers, "", "", ""].slice(0, 3);
    let start = 0;
    C.COLS.forEach((frac, j) => {
      prims.push(cell(String(headers[j]), left + w * (start + frac / 2), headerY, "center", this.headerText, C.HF, true));
      start += frac;
    });
    const scoreX = left + w * (C.COLS[0] + C.COLS[1]) - C.PAD * k;
    rows.forEach(([name, score], i) => {
      const share = total ? Math.floor(score * 1000 / total + 0.5) / 10 : 0;
      const y = rowY(i);
      prims.push(cell(name, left + C.PAD * k, y, "left", this.cellText, C.F, false),
        cell(formatCount(score), scoreX, y, "right", this.cellText, C.F, false),
        cell(share.toFixed(1) + "%", right - C.PAD * k, y, "right", this.cellText, C.F, false));
    });
    if (this.showTotal) {
      const y = rowY(rows.length);
      prims.push(cell("총합", left + C.PAD * k, y, "left", this.cellText, C.F, true),
        cell(formatCount(total), scoreX, y, "right", this.cellText, C.F, true),
        cell("100%", right - C.PAD * k, y, "right", this.cellText, C.F, true));
    }
    return prims;
  }
}

export class HistorySticker extends PanelSticker {
  static TYPE = "history";
  static LABEL = "후원 카드 더미";
  static DEFAULTS = { ...PANEL, unit: "", count: 4, width: 200, auto: true, bgOpacity: 0.95, borderWidth: 3,
    x: 0.085, y: 0.42, entries: [["구릭", 4860], ["구릭", 1000], ["채원♥익", 2871], ["채원♥익", 2514]] };
  static CH = 108; static GAP = 10; static NUM = 46; static NICK = 15; static CAP = 13;
  static NUM_Y = 41; static NICK_Y = 76; static CAP_Y = 94; static INNER = 5; static OUTER = 2;
  static TIERS = [[1000, "#ff3b5c"], [500, "#ff8a00"], [100, "#2f80ff"], [0, "#20b26b"]];

  get dynamic() {
    return this.auto;
  }

  static tierColor(amount) {
    return HistorySticker.TIERS.find(([limit]) => amount >= limit)[1];
  }

  cards(state) {
    const recent = this.auto ? [...state.donations].reverse().map(d => [d.nick, d.amount]) : [];
    const base = this.entries.map(([n, a]) => [String(n), Math.trunc(Number(a))]);
    return [...recent, ...base].slice(0, Math.trunc(this.count));
  }

  layout(width, height, state = StickerState.EMPTY) {
    const C = HistorySticker, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const cards = this.cards(state);
    const unit = this.unit || state.unit;
    const caption = amount => `${formatGift(amount, unit)} ${isMoney(unit) ? "후원" : "선물"}!`;
    const h = (cards.length * C.CH + Math.max(0, cards.length - 1) * C.GAP) * k;
    const top = cy - h / 2;
    const prims = [];
    cards.forEach(([nick, amount], i) => {
      const cardTop = top + i * (C.CH + C.GAP) * k;
      const color = C.tierColor(amount);
      const num = [run(String(amount), r2(C.NUM * k), color, true, this.font)];
      const numY = cardTop + C.NUM_Y * k;
      prims.push(
        rectPrim(r2(cx), r2(cardTop + C.CH * k / 2), r2(this.width * k), r2(C.CH * k), r2(this.radius * k), this.bg,
          this.bgOpacity, r2(this.borderWidth * k), color, 0),
        textPrim(cx, numY, "center", num, 2, (C.INNER + C.OUTER) * k, "#333333"),
        textPrim(cx, numY, "center", num, 3, C.INNER * k, "#ffffff"),
        textPrim(cx, cardTop + C.NICK_Y * k, "center", [this.run(nick, C.NICK, k, null, true)]),
        textPrim(cx, cardTop + C.CAP_Y * k, "center", [this.run(caption(amount), C.CAP, k)]));
    });
    return prims;
  }
}

export class MvpSticker extends Sticker {
  static TYPE = "mvp";
  static LABEL = "MVP";
  static DEFAULTS = { label: "MVP", entries: [["구릭", 8132]], auto: true, size: 26, font: "Malgun Gothic",
    labelColor: "#ffd200", nickColor: "#ffffff", amountColor: "#ffd200", outline: "#111111", outlineWidth: 3,
    x: 0.86, y: 0.04 };

  get dynamic() {
    return this.auto;
  }

  top(state) {
    const totals = new Map();
    for (const [nick, amount] of this.entries) totals.set(String(nick), (totals.get(String(nick)) || 0) + Math.trunc(Number(amount)));
    if (this.auto) for (const [nick, amount] of state.totals) totals.set(nick, (totals.get(nick) || 0) + amount);
    let best = ["", 0], found = false;
    for (const [nick, amount] of totals) if (!found || amount > best[1]) { best = [nick, amount]; found = true; }
    return best;
  }

  layout(width, height, state = StickerState.EMPTY) {
    const k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const [nick, amount] = this.top(state);
    const size = r2(this.size * k);
    const runs = [run(`${this.label} `, size, this.labelColor, true, this.font), run(nick, size, this.nickColor, true, this.font),
      run(" " + (isMoney(state.unit) ? formatGift(amount, state.unit) : `${formatCount(amount)}개`), size, this.amountColor, true, this.font)];
    return [textPrim(cx, cy, "center", runs, 2, this.outlineWidth * k, this.outline)];
  }
}

const PLATFORM_ALERT = { panda: "panda", afreeca: "afreeca", youtube: "youtube" };
const YT_TIERS = [  // [최소 금액 ₩, 머리띠 색, 메시지 칸 색, 글자 색] — 유튜브 슈퍼챗 색 구간
  [100000, "#d00000", "#e62117", "#ffffff"], [50000, "#c2185b", "#e91e63", "#ffffff"],
  [20000, "#e65100", "#f57c00", "#ffffff"], [10000, "#ffb300", "#ffca28", "#000000"],
  [5000, "#00bfa5", "#1de9b6", "#000000"], [2000, "#00b8d4", "#00e5ff", "#000000"],
  [0, "#1565c0", "#1565c0", "#ffffff"]];
const AVATAR_COLORS = ["#e91e63", "#9c27b0", "#3f51b5", "#03a9f4", "#009688", "#8bc34a", "#ff9800", "#795548"];

/** 후원 알림(후원창)의 자리와 모양. 단위 · 모양이 비어 있으면 플랫폼을 따라간다.
 *  panda: 분홍 띠 / afreeca: 큰 숫자 카드 / youtube: 슈퍼챗 카드 */
export class AlertSticker extends PanelSticker {
  static TYPE = "alert";
  static LABEL = "후원 알림 자리";
  static STYLES = { "": "플랫폼 따라가기", panda: "팬더티비 (분홍 띠)", afreeca: "아프리카 (큰 숫자 카드)", youtube: "유튜브 (슈퍼챗)" };
  static DEFAULTS = { ...PANEL, unit: "", style: "", width: 520, bgOpacity: 0.95, borderWidth: 3, radius: 18,
    x: 0.42, y: 0.86, show: 4.0 };
  static P = 16; static A = 28; static M = 20; static RECT_LAYER = 20; static TEXT_LAYER = 22;
  static AF = { P: 14, NUM: 56, NUM_H: 66, LINE: 22, LINE_H: 30, MSG: 18, MSG_H: 24 };
  static YT = { P: 14, AV: 40, HH: 64, NAME: 17, AMT: 20, MSG: 18, LH: 24, MAXC: 22, R: 10, NAME_Y: 22, AMT_Y: 44, PAD: 12 };

  static youtubeTier(amount) {
    const [, head, body, ink] = YT_TIERS.find(([limit]) => amount >= limit);
    return [head, body, ink];
  }

  look(state) {
    const style = Object.values(PLATFORM_ALERT).includes(this.style) ? this.style : (PLATFORM_ALERT[state.platform] || "panda");
    return [style, this.unit || state.unit];
  }

  layoutAlert(width, height, d, state = StickerState.EMPTY) {
    const [style, unit] = this.look(state);
    if (style === "afreeca") return this.#afreeca(width, height, d, unit);
    if (style === "youtube") return this.#youtube(width, height, d, unit);
    return this.#panda(width, height, d, unit);
  }

  #verb(unit) {
    return isMoney(unit) ? " 후원!" : " 선물!";
  }

  #panda(width, height, d, unit) {
    const C = AlertSticker, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const h = (2 * C.P + C.A + (d.msg ? C.M : 0)) * k;
    const a = (text, accent) => this.run(text, C.A, k, accent ? this.accent : null, true);
    const first = [a("♥ ", true), a(d.nick, true), a("님 ", false), a(formatGift(d.amount, unit), true),
      a(this.#verb(unit), false)];
    const extra = d.msg ? [[this.run(d.msg, C.M, k)]] : [];
    return [this.box(cx, cy, this.width * k, h, k, C.RECT_LAYER),
      textPrim(cx, cy, "center", first, C.TEXT_LAYER, 0, "", extra)];
  }

  /** 아프리카TV 식: 큰 숫자 + '닉님 별풍선 N개 선물!' */
  #afreeca(width, height, d, unit) {
    const C = AlertSticker, F = C.AF, H = HistorySticker, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const h = (2 * F.P + F.NUM_H + F.LINE_H + (d.msg ? F.MSG_H : 0)) * k;
    const top = cy - h / 2;
    const color = H.tierColor(d.amount);
    const num = [run(String(d.amount), r2(F.NUM * k), color, true, this.font)];
    const numY = top + (F.P + F.NUM_H / 2) * k;
    const lineY = top + (F.P + F.NUM_H + F.LINE_H / 2) * k;
    const line = [this.run(d.nick, F.LINE, k, this.accent, true), this.run("님 ", F.LINE, k),
      this.run(formatGift(d.amount, unit), F.LINE, k, color, true), this.run(this.#verb(unit), F.LINE, k)];
    const prims = [
      rectPrim(r2(cx), r2(cy), r2(this.width * k), r2(h), r2(this.radius * k), this.bg, this.bgOpacity,
        r2(this.borderWidth * k), color, C.RECT_LAYER),
      textPrim(cx, numY, "center", num, C.TEXT_LAYER, (H.INNER + H.OUTER) * k, "#333333"),
      textPrim(cx, numY, "center", num, C.TEXT_LAYER + 1, H.INNER * k, "#ffffff"),
      textPrim(cx, lineY, "center", line, C.TEXT_LAYER + 1),
    ];
    if (d.msg) {
      const msgY = top + (F.P + F.NUM_H + F.LINE_H + F.MSG_H / 2) * k;
      prims.push(textPrim(cx, msgY, "center", [this.run(d.msg, F.MSG, k)], C.TEXT_LAYER + 1));
    }
    return prims;
  }

  /** 유튜브 슈퍼챗: 금액대 색 머리띠(아바타 · 이름 · 금액) + 메시지 칸 */
  #youtube(width, height, d, unit) {
    const C = AlertSticker, Y = C.YT, k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const [head, body, ink] = C.youtubeTier(d.amount);
    const lines = d.msg ? wrapText(d.msg, Y.MAXC).slice(0, 3) : [];
    const bodyH = lines.length ? lines.length * Y.LH + 2 * Y.PAD : 0;
    const w = this.width * k, h = (Y.HH + bodyH) * k;
    const left = cx - w / 2, top = cy - h / 2;
    const rect = (x, y, rw, rh, r, color, layer) => rectPrim(r2(x), r2(y), r2(rw), r2(rh), r2(r), color, 1, 0, "", layer);
    const text = (x, y, align, t, size, bold) =>
      textPrim(x, y, align, [run(t, r2(size * k), ink, bold, this.font)], C.TEXT_LAYER + 1);
    const prims = [rect(cx, cy, w, h, Y.R * k, lines.length ? body : head, C.RECT_LAYER)];
    if (lines.length) {
      prims.push(rect(cx, top + Y.HH * k / 2, w, Y.HH * k, Y.R * k, head, C.RECT_LAYER + 1),
        rect(cx, top + (Y.HH - Y.R / 2) * k, w, Y.R * k, 0, head, C.RECT_LAYER + 1));
    }
    const avX = left + (Y.P + Y.AV / 2) * k, avY = top + Y.HH * k / 2;
    let sum = 0;
    for (const ch of d.nick) sum += ch.codePointAt(0);
    prims.push(rect(avX, avY, Y.AV * k, Y.AV * k, Y.AV / 2 * k, AVATAR_COLORS[sum % AVATAR_COLORS.length], C.TEXT_LAYER));
    prims.push(textPrim(avX, avY, "center", [run(Array.from(d.nick)[0] || " ", r2(20 * k), "#ffffff", true, this.font)],
      C.TEXT_LAYER + 1));
    const textX = left + (Y.P + Y.AV + 12) * k;
    prims.push(text(textX, top + Y.NAME_Y * k, "left", d.nick, Y.NAME, false),
      text(textX, top + Y.AMT_Y * k, "left", formatGift(d.amount, unit), Y.AMT, true));
    lines.forEach((line, i) => {
      prims.push(text(left + Y.P * k, top + (Y.HH + Y.PAD + Y.LH * i + Y.LH / 2) * k, "left", line, Y.MSG, false));
    });
    return prims;
  }
}

export class ImageSticker extends Sticker {
  static TYPE = "image";
  static LABEL = "그림 스티커";
  static DEFAULTS = { path: "", url: "", height: 240, aspect: 1 };

  layout(width, height) {
    const k = this.k(height);
    const [cx, cy] = this.center(width, height);
    const h = this.height * k;
    return [Object.freeze({ kind: "image", cx: r2(cx), cy: r2(cy), w: r2(h * this.aspect), h: r2(h), path: this.path, url: this.url })];
  }
}

for (const cls of [TextSticker, RankingSticker, GoalSticker, BannerSticker, TableSticker, HistorySticker, MvpSticker,
  AlertSticker, ImageSticker]) {
  Sticker.register(cls);
}
