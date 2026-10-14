// 닉네임 색 목록
import { Observable } from "./observable.js";
import { normalizeHex, randomColor } from "./text.js";

export class Palette extends Observable {
  #colors;
  #rng;

  constructor(colors, rng) {
    super();
    this.#colors = colors.map(c => normalizeHex(c) || "#ffffff");
    this.#rng = rng;
  }

  get colors() {
    return [...this.#colors];
  }

  add(color) {
    this.#colors.push(normalizeHex(color || "") || randomColor(this.#rng));
    this.emit();
  }

  set(index, value) {
    const hex = normalizeHex(value);
    if (!hex || index < 0 || index >= this.#colors.length) return;
    this.#colors[index] = hex;
    this.emit();
  }

  remove(index) {
    if (this.#colors.length <= 1) return;
    this.#colors.splice(index, 1);
    this.emit();
  }

  randomize(index) {
    this.#colors[index] = randomColor(this.#rng);
    this.emit();
  }

  randomizeAll() {
    this.#colors = this.#colors.map(() => randomColor(this.#rng));
    this.emit();
  }

  fitTo(n) {
    const target = Math.max(1, n);
    while (this.#colors.length < target) this.#colors.push(randomColor(this.#rng));
    this.#colors.length = target;
    this.emit();
  }
}
