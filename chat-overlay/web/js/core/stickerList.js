// 화면에 붙인 스티커 목록. 미리보기 끌어 옮기기 · 편집 패널 · 저장이 함께 쓰는 상태.
import { Observable } from "./observable.js";
import { Sticker } from "./stickers.js";

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
let counter = 0;
const newId = () => `s${Date.now().toString(36)}${(counter++).toString(36)}`;

export class StickerList extends Observable {
  static MIN_SCALE = 0.2;
  static MAX_SCALE = 5;

  #items = [];
  selectedId = null;

  /** 기본값을 채우고 검사한 깨끗한 객체로 */
  static #normalize(obj) {
    return Sticker.fromObject(obj).toObject();
  }

  get items() {
    return this.#items.map(s => ({ ...s }));
  }

  get(id) {
    const s = this.#items.find(i => i.id === id);
    return s ? { ...s } : null;
  }

  add(obj) {
    if (obj.type === "alert" && this.#items.some(s => s.type === "alert")) {
      this.selectedId = this.#items.find(s => s.type === "alert").id;
      this.emit();
      return this.selectedId;
    }
    const item = { ...StickerList.#normalize(obj), id: newId() };
    this.#items.push(item);
    this.selectedId = item.id;
    this.emit();
    return item.id;
  }

  update(id, patch, { notify = true } = {}) {
    const i = this.#items.findIndex(s => s.id === id);
    if (i < 0) return;
    this.#items[i] = { ...StickerList.#normalize({ ...this.#items[i], ...patch }), id };
    if (notify) this.emit();
  }

  moveTo(id, x, y, opts) {
    this.update(id, { x: clamp(x, 0, 1), y: clamp(y, 0, 1) }, opts);
  }

  scaleBy(id, factor, opts) {
    const s = this.get(id);
    if (s) this.update(id, { scale: clamp(s.scale * factor, StickerList.MIN_SCALE, StickerList.MAX_SCALE) }, opts);
  }

  remove(id) {
    this.#items = this.#items.filter(s => s.id !== id);
    if (this.selectedId === id) this.selectedId = null;
    this.emit();
  }

  select(id) {
    if (this.selectedId === id) return;
    this.selectedId = id;
    this.emit();
  }

  replaceAll(objects) {
    this.#items = [];
    for (const o of objects) {
      if (o.type === "alert" && this.#items.some(s => s.type === "alert")) continue;
      this.#items.push({ ...StickerList.#normalize(o), id: newId() });
    }
    this.selectedId = null;
    this.emit();
  }

  /** 저장해 둔 목록 복원. 깨진 항목은 건너뛴다. */
  load(objects) {
    const ok = [];
    for (const o of Array.isArray(objects) ? objects : []) {
      if (!o || typeof o !== "object") continue;
      try {
        StickerList.#normalize(o);
        ok.push(o);
      } catch {
        /* 모르는 종류 등은 건너뛴다 */
      }
    }
    this.replaceAll(ok);
  }

  toJSON() {
    return this.#items.map(({ id, ...rest }) => rest);
  }

  /** 미리보기 · 렌더링에 쓰는 스티커 객체 (id 포함) */
  stickers() {
    return this.#items.map(s => Sticker.fromObject(s));
  }
}
