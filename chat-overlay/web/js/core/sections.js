// 구간별 속도 목록. 타임라인 드래그와 구간 패널이 함께 쓰는 상태.
import { Observable } from "./observable.js";

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export class SectionList extends Observable {
  static MIN_LENGTH = 0.2;
  static MAX_SPEED = 5;  // 슬라이더 범위: 1/5배 ~ 5배

  #items = [];
  #length;
  selected = -1;

  constructor(length) {
    super();
    this.#length = length;
  }

  static sliderToSpeed(v) {
    return Math.pow(SectionList.MAX_SPEED, v / 100);
  }

  static speedToSlider(s) {
    return Math.round((Math.log(s) / Math.log(SectionList.MAX_SPEED)) * 100);
  }

  get items() {
    return this.#items.map(s => Object.freeze({ ...s }));
  }

  get length() {
    return this.#length;
  }

  #normalize(s) {
    const len = this.#length, min = SectionList.MIN_LENGTH, max = SectionList.MAX_SPEED;
    const start = clamp(s.start, 0, Math.max(0, len - min));
    const end = clamp(Math.max(s.end, start + min), start + min, len);
    return { start, end, speed: clamp(s.speed, 1 / max, max) };
  }

  #sortKeeping(item) {
    this.#items.sort((a, b) => a.start - b.start);
    this.selected = item ? this.#items.indexOf(item) : -1;
  }

  add(start, end, speed) {
    const item = this.#normalize({ start: Math.min(start, end), end: Math.max(start, end), speed });
    this.#items.push(item);
    this.#sortKeeping(item);
    this.emit();
  }

  /** notify:false 면 구독자에게 알리지 않는다 (슬라이더를 끄는 동안 목록을 다시 그리지 않도록) */
  update(index, patch, { notify = true } = {}) {
    const item = this.#items[index];
    if (!item) return;
    Object.assign(item, this.#normalize({ ...item, ...patch }));
    this.#sortKeeping(this.#items[this.selected] === item || this.selected < 0 ? item : this.#items[this.selected]);
    if (notify) this.emit();
  }

  remove(index) {
    this.#items.splice(index, 1);
    this.selected = -1;
    this.emit();
  }

  select(index) {
    if (index === this.selected) return;
    this.selected = index;
    this.emit();
  }

  indexAt(t) {
    return this.#items.findIndex(s => t >= s.start && t <= s.end);
  }

  setLength(length) {
    this.#length = length;
    this.#items = this.#items
      .filter(s => s.start < length - SectionList.MIN_LENGTH)
      .map(s => this.#normalize(s));
    this.selected = -1;
    this.emit();
  }

  toSettings() {
    return this.#items.map(s => ({ start: s.start, end: s.end, speed: s.speed }));
  }
}
