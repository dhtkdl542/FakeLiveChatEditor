// 타임라인 좌표 변환과 마우스 동작 해석 (클릭 = 이동, 드래그 = 구간 만들기)
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const snap = t => Math.round(t * 100) / 100;  // 0.01초 단위로 맞춘다

export class TimelineScale {
  constructor(length, width) {
    this.length = length;
    this.width = width;
  }

  xOf(t) {
    return (t / this.length) * this.width;
  }

  tAt(x) {
    return snap(clamp((x / this.width) * this.length, 0, this.length));
  }
}

export class TimelineGesture {
  static DRAG_PX = 4;          // 이만큼 움직여야 드래그로 본다
  static MIN_SECTION = 0.3;    // 이보다 짧은 드래그는 클릭으로 본다

  #getScale; #down = null;

  constructor(getScale) {
    this.#getScale = getScale;
  }

  down(x) {
    this.#down = { x0: x, x1: x, moved: false };
  }

  move(x) {
    if (!this.#down) return;
    this.#down.x1 = x;
    if (Math.abs(x - this.#down.x0) > TimelineGesture.DRAG_PX) this.#down.moved = true;
  }

  get preview() {
    const d = this.#down;
    if (!d || !d.moved) return null;
    const scale = this.#getScale();
    const a = scale.tAt(d.x0), b = scale.tAt(d.x1);
    return { start: Math.min(a, b), end: Math.max(a, b) };
  }

  up(x) {
    const d = this.#down;
    this.#down = null;
    if (!d) return null;
    const scale = this.#getScale();
    const a = scale.tAt(d.x0), b = scale.tAt(x);
    if (d.moved && Math.abs(b - a) >= TimelineGesture.MIN_SECTION) {
      return { type: "section", start: Math.min(a, b), end: Math.max(a, b) };
    }
    return { type: "seek", t: b };
  }
}
