// 화면에 보이는 채팅 줄 배치와 모양. chatov/ass.py 의 ChatLayout / AssWriter 와 같은 규칙.
import { Color, wrapText } from "./text.js";

const MAX_ALPHA = 200;
export const ICON_EM = 0.8;
const ALIGNS = ["right", "left"];

const round = v => Math.floor(v + 0.5);
const clamp01 = v => Math.min(1, Math.max(0, v));
const bool = v => v === true || ["1", "true", "on", "yes"].includes(String(v).toLowerCase());

/** 박스도 글자처럼 위로 갈수록 흐려지게: 박스 불투명도 × 글자 불투명도 (ASS 투명도 0~255) */
export function boxAlpha(opacity, textAlpha) {
  const base = round(255 * (1 - opacity));
  return 255 - round(((255 - base) * (255 - textAlpha)) / 255);
}

export class OverlayStyle {
  constructor(fields) {
    Object.assign(this, fields);
    Object.freeze(this);
  }

  static fromSettings(cfg) {
    const num = (k, d) => (cfg[k] === undefined || cfg[k] === "" ? d : Number(cfg[k]));
    const int = (k, d) => Math.trunc(num(k, d));
    const align = cfg.ALIGN ?? "right";
    return new OverlayStyle({
      align: ALIGNS.includes(align) ? align : "right",
      sideMargin: int("SIDE_MARGIN", 24),
      bottomMargin: int("BOTTOM_MARGIN", 24),
      lineH: int("LINE_H", 36),
      visible: Math.max(1, int("VISIBLE", 8)),
      fadeInMs: int("FADE_IN_MS", 180),
      fadeOutMs: int("FADE_OUT_MS", 450),
      fadeUp: int("FADE_UP_STRENGTH", 18),
      maxChars: int("MAX_CHARS_PER_LINE", 22),
      nickFont: cfg.NICK_FONT || "Malgun Gothic",
      nickSize: int("NICK_SIZE", 20),
      nickBold: bool(cfg.NICK_BOLD ?? false),
      msgFont: cfg.MSG_FONT || "Malgun Gothic",
      msgSize: int("MSG_SIZE", 18),
      msgColor: cfg.MSG_COLOR || "#ffffff",
      outline: int("OUTLINE", 2),
      box: bool(cfg.BOX ?? false),
      boxColor: cfg.BOX_COLOR || "#000000",
      boxOpacity: clamp01(num("BOX_OPACITY", 0.45)),
      boxPadding: int("BOX_PADDING", 6),
      icon: cfg.ICON || "",
      iconColor: cfg.ICON_COLOR || "",
      iconScale: num("ICON_SCALE", 1.0),
      highlightColor: cfg.HIGHLIGHT_COLOR || "#ff5fa2",
      highlightOpacity: clamp01(num("HIGHLIGHT_OPACITY", 0.85)),
    });
  }

  /** 박스가 있는 줄(박스 모드이거나 후원 줄)은 박스 여백만큼 안쪽에 놓는다 */
  padding(row) {
    return this.box || row.highlight ? this.boxPadding : 0;
  }
}

export class ChatLayout {
  constructor(style) {
    this.style = style;
  }

  /** index 번째 채팅이 막 올라온 순간 보이는 줄들 (위→아래) */
  rowsAt(events, index) {
    const s = this.style;
    const pieces = [];
    for (const e of events.slice(Math.max(0, index - s.visible + 1), index + 1)) {
      wrapText(e.msg, s.maxChars).forEach((piece, i) =>
        pieces.push([i === 0 ? e.nick : "", piece, e.color, Boolean(e.highlight)]));
    }
    const shown = pieces.slice(-s.visible);
    const n = shown.length;
    return shown.map(([nick, msg, color, highlight], row) => {
      const age = n - 1 - row;
      return Object.freeze({
        nick, msg, color, age,
        alpha: Math.min(MAX_ALPHA, age * s.fadeUp),
        isNewest: age === 0,
        isOldest: row === 0 && n >= s.visible,
        highlight,
      });
    });
  }

  static lastArrived(events, now) {
    let lo = 0, hi = events.length - 1, ans = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (events[mid].t <= now) { ans = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return ans;
  }

  /** now 시각에 화면에 떠 있는 줄. startT = 이 화면이 시작된 시각, nextT = 다음 채팅(또는 끝) 시각 */
  frameAt(events, now, duration) {
    const index = ChatLayout.lastArrived(events, now);
    if (index < 0) return { index, rows: [], startT: null, nextT: null };
    return {
      index,
      rows: this.rowsAt(events, index),
      startT: events[index].t,
      nextT: index + 1 < events.length ? events[index + 1].t : duration,
    };
  }

  /** ASS \fad 를 흉내 낸 배율 (0~1): 새 줄은 나타나고, 꽉 찼을 때 맨 윗줄은 사라진다 */
  fade(row, now, startT, nextT) {
    const s = this.style;
    if (row.isNewest && s.fadeInMs > 0) return clamp01(((now - startT) * 1000) / s.fadeInMs);
    if (row.isOldest && s.fadeOutMs > 0) return clamp01(((nextT - now) * 1000) / s.fadeOutMs);
    return 1;
  }

  /** 위쪽 흐림을 반영한 글자 불투명도와 박스 배경색 (ASS \1a / \4c\4a 와 같은 값) */
  paint(row) {
    const s = this.style;
    const textOpacity = 1 - row.alpha / 255;
    if (!s.box && !row.highlight) return { textOpacity, background: null };
    const c = Color.parse(row.highlight ? s.highlightColor : s.boxColor);
    const opacity = row.highlight ? s.highlightOpacity : s.boxOpacity;
    return { textOpacity, background: `rgba(${c.r},${c.g},${c.b},${(255 - boxAlpha(opacity, row.alpha)) / 255})` };
  }

  /** 글자 줄의 아래쪽 모서리 (right 면 오른쪽 아래, left 면 왼쪽 아래). 박스 바깥선이 여백에 닿게 안쪽으로 들인다. */
  position(row, videoW, videoH) {
    const s = this.style;
    const pad = s.padding(row);
    const inset = s.sideMargin + pad;
    return {
      x: s.align === "right" ? videoW - inset : inset,
      y: videoH - s.bottomMargin - pad - row.age * s.lineH,
      align: s.align,
    };
  }

  iconSize() {
    return this.style.nickSize * ICON_EM * this.style.iconScale;
  }
}
