// 언제 누가 무슨 채팅을 치는지 정하는 타임라인. chatov/timeline.py 와 같은 순서로 난수를 쓴다.
import { Mulberry32 } from "./rng.js";
import { SpeedCurve } from "./speed.js";
import { colorForNick } from "./text.js";

export const END_MARGIN = 0.2;

export class ShuffledCycle {
  #items; #rng; #bag = [];

  constructor(items, rng) {
    if (!items.length) throw new Error("목록이 비었습니다.");
    this.#items = [...items];
    this.#rng = rng;
  }

  next() {
    if (!this.#bag.length) {
      const bag = [...this.#items];
      for (let i = bag.length - 1; i > 0; i--) {
        const j = this.#rng.below(i + 1);
        [bag[i], bag[j]] = [bag[j], bag[i]];
      }
      this.#bag = bag;
    }
    return this.#bag.pop();
  }
}

export class EventGenerator {
  static STEP = 0.02;  // 속도 곡선을 적분하는 시간 간격(초)

  constructor({ curve, nicks, msgs, palette, start, intervalMin, intervalMax, rng }) {
    this.curve = curve;
    this.nicks = nicks;
    this.msgs = msgs;
    this.palette = palette;
    this.start = start;
    this.lo = intervalMin;
    this.hi = Math.max(intervalMin, intervalMax);
    this.rng = rng;
  }

  static fromSettings(cfg, seed) {
    return new EventGenerator({
      curve: SpeedCurve.fromSettings(cfg),
      nicks: cfg.NICKS || [], msgs: cfg.MSGS || [], palette: cfg.COLORS || [],
      start: Number(cfg.CHAT_START ?? 0.5),
      intervalMin: Number(cfg.INTERVAL_MIN ?? 0.25),
      intervalMax: Number(cfg.INTERVAL_MAX ?? 0.7),
      rng: new Mulberry32(seed),
    });
  }

  /** 다음 채팅까지 '속도 × 시간' 이 랜덤 간격만큼 쌓이면 채팅 하나. 빠른 구간일수록 빨리 쌓인다. */
  generate(duration) {
    if (!this.nicks.length || !this.msgs.length) return [];
    const nicks = new ShuffledCycle(this.nicks, this.rng);
    const msgs = new ShuffledCycle(this.msgs, this.rng);
    const step = EventGenerator.STEP;
    const events = [];
    let t = this.start;
    while (t < duration - END_MARGIN) {
      const nick = nicks.next();
      events.push(Object.freeze({ t: Math.round(t * 1000) / 1000, nick, msg: msgs.next(), color: colorForNick(nick, this.palette) }));
      let need = this.rng.uniform(this.lo, this.hi);
      while (need > 0 && t < duration) {
        need -= this.curve.at(t) * step;
        t += step;
      }
    }
    return events;
  }
}

/** 타임라인에 영향을 주는 설정이 바뀔 때만 다시 만든다 (영상이 길면 매 프레임 만들기엔 무겁다). */
export class EventCache {
  #build; #key = null; #value = [];

  constructor(build = (cfg, seed, len) => EventGenerator.fromSettings(cfg, seed).generate(len)) {
    this.#build = build;
  }

  static keyOf(cfg, seed, len) {
    return JSON.stringify([len, seed, cfg.CHAT_START, cfg.INTERVAL_MIN, cfg.INTERVAL_MAX, cfg.SPEED_VAR,
      cfg.SPEED_PERIOD, cfg.SPEED_PHASES, cfg.SPEED_SECTIONS, cfg.NICKS, cfg.MSGS, cfg.COLORS]);
  }

  get(cfg, seed, len) {
    const key = EventCache.keyOf(cfg, seed, len);
    if (key !== this.#key) {
      this.#key = key;
      this.#value = this.#build(cfg, seed, len);
    }
    return this.#value;
  }
}
