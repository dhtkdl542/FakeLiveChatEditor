// data-field 가 붙은 입력칸들을 한꺼번에 읽고 쓴다. 체크박스는 "1" / "" 로 다룬다.
import { $$ } from "./dom.js";

const isCheck = el => el.type === "checkbox";

export class FormView {
  constructor(root) {
    this.root = root;
  }

  #field(name) {
    return this.root.querySelector(`[data-field="${name}"]`);
  }

  #read(el) {
    return isCheck(el) ? (el.checked ? "1" : "") : el.value;
  }

  values() {
    const v = {};
    for (const el of $$("[data-field]", this.root)) v[el.dataset.field] = this.#read(el);
    return v;
  }

  get(name) {
    const el = this.#field(name);
    return el ? this.#read(el) : "";
  }

  set(name, value) {
    const el = this.#field(name);
    if (!el) return;
    if (isCheck(el)) el.checked = Boolean(value) && value !== "0";
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /** 여러 칸을 한 번에 바꾼다 (프리셋) */
  apply(fields) {
    for (const [name, value] of Object.entries(fields)) this.set(name, value);
  }

  onChange(fn) {
    this.root.addEventListener("input", fn);
    this.root.addEventListener("change", fn);
  }

  /** <i data-show="speedVar" data-unit="%"> 처럼 값을 옆에 보여주는 표시를 갱신 */
  refreshLabels() {
    for (const el of $$("[data-show]", this.root)) el.textContent = this.get(el.dataset.show) + (el.dataset.unit || "");
  }
}
