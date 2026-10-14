// 입력칸 값(문자열)을 렌더링·미리보기에 쓰는 설정으로 정리한다. 키 이름은 서버(chatov)와 같다.
import { ICON_NAMES } from "./icons.js";
import { linesOf } from "./lines.js";
import { normalizeHex } from "./text.js";
import { platformKey, PLATFORMS } from "./platforms.js";
import { DEFAULT_BADGES, parseBadgeOverrides } from "./badges.js";

const BOX_SHAPES = ["square", "rounded", "pill"];
const cap = s => s[0].toUpperCase() + s.slice(1);

const DEFAULT_FONT = "Malgun Gothic";
const bool = v => v === true || v === "1" || v === "on";

export class Settings {
  static DEFAULTS = Object.freeze({
    sideMargin: 24, bottomMargin: 24, lineH: 36, visible: 8, maxChars: 22,
    chatStart: 0.5, intMin: 0.25, intMax: 0.7, fadeIn: 180, fadeOut: 450, fadeUp: 18,
    speedVar: 50, speedPeriod: 8, nickSize: 20, msgSize: 18,
    outline: 2, boxOpacity: 45, boxPadding: 6, iconScale: 100,
    donationEvery: 15, donationMsgChance: 40, boxRadius: 8, boxBorder: 0,
  });

  /** 배지 칸 이름: badgeManagerIcon / badgeManagerColor / badgeManagerShare … */
  static badgeField(key, part) {
    return `badge${cap(key)}${part}`;
  }

  static #badges(raw) {
    return DEFAULT_BADGES.map(b => {
      const f = part => raw[Settings.badgeField(b.key, part)];
      const share = Number(f("Share"));
      return {
        ...b,
        icon: ICON_NAMES.includes(f("Icon")) ? f("Icon") : b.icon,
        color: normalizeHex(f("Color")) || b.color,
        share: f("Share") === undefined || f("Share") === "" || !Number.isFinite(share)
          ? b.share : Math.min(100, Math.max(0, share)) / 100,
      };
    });
  }

  static #amounts(text, fallback) {
    const list = String(text || "").split(/[,\s]+/).map(Number).filter(n => Number.isFinite(n) && n > 0).map(Math.trunc);
    return list.length ? list : [...fallback];
  }

  /** 화면의 data-field 이름 목록 (프리셋이 바꿀 수 있는 칸) */
  static FIELDS = Object.freeze([
    "align", "sideMargin", "bottomMargin", "lineH", "visible", "maxChars", "fadeUp",
    "chatStart", "intMin", "intMax", "fadeIn", "fadeOut", "speedVar", "speedPeriod",
    "nickFont", "nickSize", "nickBold", "msgFont", "msgSize", "msgColor",
    "outline", "box", "boxColor", "boxOpacity", "boxPadding", "icon", "iconFollowNick", "iconColor", "iconScale",
    "boxShape", "boxRadius", "boxBorder", "boxBorderColor", "badgesOn", "badgeOverrides",
    ...DEFAULT_BADGES.flatMap(b => ["Icon", "Color", "Share"].map(part => `badge${cap(b.key)}${part}`)),
    "nicks", "msgs", "msgsInOrder", "platform", "donationsOn", "donationEvery", "donationAmounts", "donationMsgChance", "donationUnit",
  ]);

  static #num(raw, key, { min = -Infinity, max = Infinity, int = false } = {}) {
    let v = Number(raw[key]);
    if (raw[key] === undefined || raw[key] === "" || !Number.isFinite(v)) v = Settings.DEFAULTS[key];
    if (int) v = Math.trunc(v);
    return Math.min(max, Math.max(min, v));
  }

  /** raw: 입력칸 이름 → 값. extra: 입력칸 밖에서 관리하는 상태(색, 출렁임 위상, 구간, 올린 글꼴). */
  static fromForm(raw, { colors, phases, sections, loadedFonts = {} }) {
    const n = (key, opts) => Settings.#num(raw, key, opts);
    const platform = platformKey(raw.platform);
    const badges = Settings.#badges(raw);
    return Object.freeze({
      ALIGN: raw.align === "left" ? "left" : "right",
      SIDE_MARGIN: n("sideMargin", { min: 0, int: true }),
      BOTTOM_MARGIN: n("bottomMargin", { min: 0, int: true }),
      LINE_H: n("lineH", { min: 1, int: true }),
      VISIBLE: n("visible", { min: 1, int: true }),
      MAX_CHARS_PER_LINE: n("maxChars", { min: 4, int: true }),
      CHAT_START: n("chatStart", { min: 0 }),
      INTERVAL_MIN: n("intMin", { min: 0.05 }),
      INTERVAL_MAX: n("intMax", { min: 0.05 }),
      FADE_IN_MS: n("fadeIn", { min: 0, int: true }),
      FADE_OUT_MS: n("fadeOut", { min: 0, int: true }),
      FADE_UP_STRENGTH: n("fadeUp", { min: 0, int: true }),
      SPEED_VAR: n("speedVar", { min: 0, max: 100 }) / 100,
      SPEED_PERIOD: n("speedPeriod", { min: 1 }),
      SPEED_PHASES: [...phases],
      SPEED_SECTIONS: sections.map(s => ({ ...s })),
      NICK_FONT: loadedFonts.nick || String(raw.nickFont || "").trim() || DEFAULT_FONT,
      NICK_SIZE: n("nickSize", { min: 4, int: true }),
      NICK_BOLD: bool(raw.nickBold),
      MSG_FONT: loadedFonts.msg || String(raw.msgFont || "").trim() || DEFAULT_FONT,
      MSG_SIZE: n("msgSize", { min: 4, int: true }),
      MSG_COLOR: normalizeHex(raw.msgColor) || "#ffffff",
      OUTLINE: n("outline", { min: 0, max: 20, int: true }),
      BOX: bool(raw.box),
      BOX_COLOR: normalizeHex(raw.boxColor) || "#000000",
      BOX_OPACITY: n("boxOpacity", { min: 0, max: 100 }) / 100,
      BOX_PADDING: n("boxPadding", { min: 0, max: 60, int: true }),
      ICON: ICON_NAMES.includes(raw.icon) ? raw.icon : "",
      ICON_COLOR: bool(raw.iconFollowNick) ? "" : normalizeHex(raw.iconColor) || "",
      ICON_SCALE: n("iconScale", { min: 30, max: 300 }) / 100,
      BOX_SHAPE: BOX_SHAPES.includes(raw.boxShape) ? raw.boxShape : "square",
      BOX_RADIUS: n("boxRadius", { min: 0, max: 200, int: true }),
      BOX_BORDER: n("boxBorder", { min: 0, max: 20, int: true }),
      BOX_BORDER_COLOR: normalizeHex(raw.boxBorderColor) || "#ffffff",
      BADGES_ON: bool(raw.badgesOn),
      BADGES: badges,
      BADGE_OVERRIDES: parseBadgeOverrides(raw.badgeOverrides, badges),
      NICKS: linesOf(raw.nicks),
      MSGS: linesOf(raw.msgs),
      MSGS_IN_ORDER: bool(raw.msgsInOrder),
      COLORS: [...colors],
      DONATIONS_ON: bool(raw.donationsOn),
      DONATION_EVERY: n("donationEvery", { min: 1 }),
      PLATFORM: platform,
      DONATION_AMOUNTS: Settings.#amounts(raw.donationAmounts, PLATFORMS[platform].amounts),
      DONATION_MSG_CHANCE: n("donationMsgChance", { min: 0, max: 100 }) / 100,
      DONATION_UNIT: String(raw.donationUnit || "").trim() || PLATFORMS[platform].unit,
    });
  }
}
