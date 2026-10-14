// 채팅 글자 줄바꿈과 색. chatov/text.py 와 같은 규칙.
export const MIN_CHARS_PER_LINE = 4;

export function wrapText(text, maxChars) {
  const size = Math.max(MIN_CHARS_PER_LINE, Math.trunc(maxChars) || 0);
  const lines = [];
  for (let i = 0; i < text.length; i += size) lines.push(text.slice(i, i + size));
  return lines.length ? lines : [""];
}

const HEX6 = /^#?([0-9a-fA-F]{6})$/;
const HEX3 = /^#?([0-9a-fA-F]{3})$/;
const ASS = /^&H([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})&?$/;

export class Color {
  constructor(r, g, b) {
    Object.assign(this, { r, g, b });
    Object.freeze(this);
  }

  static parse(value) {
    const v = (value || "").trim();
    let m = v.match(HEX6);
    if (m) return Color.#fromHex(m[1]);
    m = v.match(HEX3);
    if (m) return Color.#fromHex([...m[1]].map(ch => ch + ch).join(""));
    m = v.match(ASS);
    if (m) return new Color(parseInt(m[4], 16), parseInt(m[3], 16), parseInt(m[2], 16));
    return new Color(255, 255, 255);
  }

  static #fromHex(h) {
    return new Color(parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16));
  }

  toHex() {
    return "#" + [this.r, this.g, this.b].map(v => v.toString(16).padStart(2, "0")).join("");
  }
}

/** 3자리·대문자·# 없는 값을 #rrggbb 로. 잘못된 값이면 null. */
export function normalizeHex(value) {
  const v = (value || "").trim();
  return HEX6.test(v) || HEX3.test(v) ? Color.parse(v).toHex() : null;
}

/** 닉네임 글자 코드 합으로 색을 고른다. Python ord() 와 같도록 코드 포인트 단위로 센다. */
export function colorForNick(nick, palette) {
  if (!palette.length) return "#ffffff";
  let sum = 0;
  for (const ch of nick) sum += ch.codePointAt(0);
  return palette[sum % palette.length];
}

/** 채팅창에서 잘 보이는 밝은 색 하나 */
export function randomColor(rng) {
  const h = Math.floor(rng.next() * 360);
  const s = (70 + Math.floor(rng.next() * 30)) / 100;
  const l = (55 + Math.floor(rng.next() * 25)) / 100;
  const k = n => {
    const p = (n + h / 30) % 12;
    const m = s * Math.min(l, 1 - l);
    return Math.round(255 * (l - m * Math.max(-1, Math.min(p - 3, 9 - p, 1))));
  };
  return new Color(k(0), k(8), k(4)).toHex();
}
