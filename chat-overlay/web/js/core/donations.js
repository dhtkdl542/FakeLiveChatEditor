// 가짜 후원. chatov/donations.py 와 같은 순서로 난수를 써서 미리보기와 결과 영상이 같다.
import { ShuffledCycle } from "./events.js";
import { Mulberry32 } from "./rng.js";
import { colorForNick } from "./text.js";

export const DEFAULT_AMOUNTS = [10, 30, 50, 100, 300, 550, 1000];
const SEED_MIX = 0x9E3779B9;
const roundMs = t => Math.floor(t * 1000 + 0.5) / 1000;

export function formatCount(n) {
  return String(Math.trunc(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export class Donation {
  constructor(t, nick, amount, msg) {
    Object.assign(this, { t, nick, amount, msg });
    Object.freeze(this);
  }
}

export class DonationGenerator {
  constructor({ nicks, msgs, every, amounts, msgChance, start, rng }) {
    this.nicks = [...nicks];
    this.msgs = [...msgs];
    this.every = Math.max(1, Number(every));
    this.amounts = amounts && amounts.length ? amounts.map(a => Math.trunc(Number(a))) : [...DEFAULT_AMOUNTS];
    this.msgChance = Number(msgChance);
    this.start = Number(start);
    this.rng = rng;
  }

  static donationSeed(seed) {
    return ((seed ^ SEED_MIX) >>> 0);
  }

  static fromSettings(cfg, seed) {
    return new DonationGenerator({
      nicks: cfg.NICKS || [], msgs: cfg.MSGS || [], every: cfg.DONATION_EVERY ?? 15,
      amounts: cfg.DONATION_AMOUNTS || DEFAULT_AMOUNTS, msgChance: cfg.DONATION_MSG_CHANCE ?? 0.4,
      start: cfg.CHAT_START ?? 0.5, rng: new Mulberry32(DonationGenerator.donationSeed(seed)),
    });
  }

  #gap() {
    return this.every * this.rng.uniform(0.5, 1.5);
  }

  generate(duration) {
    if (!this.nicks.length) return [];
    const nicks = new ShuffledCycle(this.nicks, this.rng);
    const msgs = this.msgs.length ? new ShuffledCycle(this.msgs, this.rng) : null;
    const out = [];
    let t = this.start + this.#gap();
    while (t < duration - 1) {
      const nick = nicks.next();
      const r = this.rng.next();
      const amount = this.amounts[Math.min(this.amounts.length - 1, Math.trunc(r ** 2 * this.amounts.length))];
      const msg = msgs && this.rng.next() < this.msgChance ? msgs.next() : "";
      out.push(new Donation(roundMs(t), nick, amount, msg));
      t += this.#gap();
    }
    return out;
  }
}

export const CURRENCY_PREFIX = ["₩", "$", "¥", "€", "£"];

export function isMoney(unit) {
  const u = String(unit || "").trim();
  return CURRENCY_PREFIX.includes(u) || u === "원";
}

/** '하트 550개' · '별풍선 4,860개' 처럼 개수로, 또는 '₩10,000' · '3,000원' 처럼 돈으로 (chatov/donations.py 와 같다) */
export function formatGift(amount, unit) {
  const u = String(unit || "").trim();
  if (CURRENCY_PREFIX.includes(u)) return `${u}${formatCount(amount)}`;
  if (u === "원") return `${formatCount(amount)}원`;
  return u ? `${u} ${formatCount(amount)}개` : `${formatCount(amount)}개`;
}

export function donationChatText(d, unit) {
  const text = `♥ ${formatGift(d.amount, unit)} ${isMoney(unit) ? "후원" : "선물"}!`;
  return d.msg ? `${text} ${d.msg}` : text;
}

/** 후원을 채팅창에 강조 줄로 끼워 넣는다. 같은 시각이면 일반 채팅 다음. */
export function mergeIntoChat(events, donations, palette, unit) {
  const rows = [
    ...events.map(e => [e.t, 0, e]),
    ...donations.map(d => [d.t, 1, Object.freeze({
      t: d.t, nick: d.nick, msg: donationChatText(d, unit), color: colorForNick(d.nick, palette), highlight: true,
    })]),
  ];
  rows.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  return rows.map(r => r[2]);
}

/** 알림 띠는 한 번에 하나. 앞 알림이 끝나기 전에 후원이 오면 줄을 서서 기다린다. */
export function scheduleAlerts(donations, duration, show = 4.0, gap = 0.3) {
  const slots = [];
  let freeAt = -Infinity;
  for (const d of donations) {
    const start = roundMs(Math.max(d.t, freeAt + gap));
    if (start >= duration) break;
    const end = roundMs(Math.min(start + show, duration));
    slots.push({ start, end, donation: d });
    freeAt = end;
  }
  return slots;
}

const POP_MS = 150, SETTLE_MS = 250, POP_FROM = 0.7, POP_PEAK = 1.08, FADE_IN_MS = 150, FADE_OUT_MS = 400;

export function alertScale(ms) {
  if (ms <= 0) return POP_FROM;
  if (ms < POP_MS) return POP_FROM + (POP_PEAK - POP_FROM) * ms / POP_MS;
  if (ms < SETTLE_MS) return POP_PEAK + (1 - POP_PEAK) * (ms - POP_MS) / (SETTLE_MS - POP_MS);
  return 1;
}

export function alertOpacity(ms, durMs) {
  return Math.max(0, Math.min(1, ms / FADE_IN_MS, (durMs - ms) / FADE_OUT_MS));
}

/** 후원 목록 캐시: 설정이 그대로면 다시 만들지 않는다 */
export class DonationCache {
  #key = null; #value = [];

  get(cfg, seed, len) {
    const key = JSON.stringify([len, seed, cfg.DONATIONS_ON, cfg.NICKS, cfg.MSGS, cfg.CHAT_START, cfg.DONATION_EVERY,
      cfg.DONATION_AMOUNTS, cfg.DONATION_MSG_CHANCE]);
    if (key !== this.#key) {
      this.#key = key;
      this.#value = cfg.DONATIONS_ON ? DonationGenerator.fromSettings(cfg, seed).generate(len) : [];
    }
    return this.#value;
  }
}
