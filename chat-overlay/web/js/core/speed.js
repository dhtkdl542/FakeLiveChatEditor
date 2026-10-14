// 시간에 따른 채팅 속도 배율. chatov/speed.py 와 같은 식.
export class SpeedSection {
  static RAMP = 0.6;        // 경계에서 속도가 서서히 바뀌는 시간(초)
  static MIN_SPEED = 0.05;

  constructor(start, end, speed) {
    Object.assign(this, { start, end, speed });
    Object.freeze(this);
  }

  static fromObject(o) {
    const start = Number(o.start), end = Number(o.end);
    if (!(end > start)) return null;
    return new SpeedSection(start, end, Math.max(SpeedSection.MIN_SPEED, Number(o.speed)));
  }

  /** 구간 안에서 0→1→0 으로 부드럽게 변하는 가중치 (smoothstep) */
  weight(t) {
    if (t <= this.start || t >= this.end) return 0;
    const ramp = Math.min(SpeedSection.RAMP, (this.end - this.start) / 2);
    const w = Math.min(1, (t - this.start) / ramp, (this.end - t) / ramp);
    return w * w * (3 - 2 * w);
  }
}

export class SpeedCurve {
  static RANGE = 4;  // 출렁임 100%일 때 1/4배 ~ 4배

  constructor({ amplitude, period, phases, sections = [] }) {
    this.amplitude = amplitude;
    this.period = period;
    this.phases = phases;
    this.sections = sections;
    Object.freeze(this);
  }

  static randomPhases(random = Math.random) {
    return [0, 1, 2].map(() => random() * Math.PI * 2);
  }

  static fromSettings(cfg, random = Math.random) {
    const phases = Array.isArray(cfg.SPEED_PHASES) && cfg.SPEED_PHASES.length === 3
      ? cfg.SPEED_PHASES.map(Number) : SpeedCurve.randomPhases(random);
    return new SpeedCurve({
      amplitude: Math.min(1, Math.max(0, Number(cfg.SPEED_VAR ?? 0))),
      period: Math.max(1, Number(cfg.SPEED_PERIOD ?? 8)),
      phases,
      sections: (cfg.SPEED_SECTIONS || []).map(SpeedSection.fromObject).filter(Boolean),
    });
  }

  wave(t) {
    if (this.amplitude <= 0) return 1;
    const p = this.phases;
    const x = 2 * Math.PI * t / this.period;
    const n = (Math.sin(x + p[0]) + 0.6 * Math.sin(x * 1.87 + p[1]) + 0.3 * Math.sin(x * 3.41 + p[2])) / 1.9;
    return Math.pow(SpeedCurve.RANGE, this.amplitude * n);
  }

  at(t) {
    let s = this.wave(t);
    for (const sec of this.sections) {
      const w = sec.weight(t);
      if (w > 0) s *= Math.pow(sec.speed, w);
    }
    return s;
  }
}
