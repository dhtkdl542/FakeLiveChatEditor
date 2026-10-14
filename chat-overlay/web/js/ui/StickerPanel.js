// 꾸미기 탭: 스티커 추가 · 목록 · 속성 편집 (템플릿 고르기는 TemplatePanel)
import { STICKER_FIELDS, formatEntries, parseEntries } from "../core/stickerFields.js";
import { AlertSticker, Sticker } from "../core/stickers.js";
import { $, h, setStatus } from "./dom.js";

function summary(s) {
  if (s.type === "text") return s.text;
  if (s.type === "banner") return s.lines.join(" · ");
  if (s.type === "alert") return `${AlertSticker.STYLES[s.style] || AlertSticker.STYLES[""]} · ${s.unit || "플랫폼 단위"}`;
  if (s.type === "image") return s.path ? s.path.split(/[\\/]/).pop() : "그림 없음";
  if (s.type === "table") return s.title || s.headers.join(" · ");
  if (s.type === "history") return `${s.unit || "플랫폼 단위"} 카드 ${s.count}장`;
  if (s.type === "mvp") return `${s.label} ${s.entries[0] ? s.entries[0][0] : ""}`;
  return s.title;
}

export class StickerPanel {
  #editingId = null;

  constructor({ list, api, onChange }) {
    Object.assign(this, { list, api, onChange });
    $("#btnClearStickers").onclick = () => this.list.replaceAll([]);
    this.#addButtons();
    list.subscribe(() => this.render());
    this.render();
  }

  #addButtons() {
    $("#stickerAdd").replaceChildren(...Sticker.types().map(cls => h("button", {
      type: "button", className: "btn ghost small",
      onclick: () => (cls.TYPE === "image" ? this.addImage() : this.list.add({ type: cls.TYPE })),
    }, "+ " + cls.LABEL)));
  }

  async addImage() {
    try {
      const { path, url } = await this.api.pickImage();
      if (!path) return;
      const img = new Image();
      img.src = url;
      await img.decode().catch(() => {});
      const aspect = img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 1;
      this.list.add({ type: "image", path, url, aspect });
    } catch (e) {
      setStatus($("#templateNote"), "그림을 불러오지 못했습니다: " + e.message, "warn");
    }
  }

  render() {
    const items = this.list.items;
    $("#stickerList").replaceChildren(...(items.length ? items.map(s => h("div", {
      className: "sticker-item" + (s.id === this.list.selectedId ? " selected" : ""),
      onclick: () => this.list.select(s.id),
    },
      h("span", { className: "kind" }, Sticker.fromObject(s).constructor.LABEL),
      h("span", { className: "summary" }, summary(s)),
      h("button", { type: "button", className: "btn ghost", onclick: e => { e.stopPropagation(); this.list.remove(s.id); } }, "삭제"),
    )) : [h("p", { className: "status" }, "스티커가 없습니다. 위 템플릿을 적용하거나 + 버튼으로 추가하세요.")]));
    this.#editor();
  }

  #editor() {
    const box = $("#stickerEditor");
    const s = this.list.get(this.list.selectedId);
    // 같은 스티커를 편집하는 중이면(끌어 옮기기 등) 입력칸을 다시 만들지 않고 값만 맞춘다
    if (s && this.#editingId === s.id && box.contains(document.activeElement)) return;
    this.#editingId = s ? s.id : null;
    if (!s) { box.replaceChildren(); return; }
    const fields = STICKER_FIELDS[s.type].map(f => this.#field(s, f));
    if (s.type === "image") {
      fields.unshift(h("button", { type: "button", className: "btn ghost small", onclick: () => this.#replaceImage(s.id) }, "그림 바꾸기"));
    }
    box.replaceChildren(h("h4", {}, `${Sticker.fromObject(s).constructor.LABEL} 편집`), ...fields);
  }

  async #replaceImage(id) {
    const { path, url } = await this.api.pickImage();
    if (path) this.list.update(id, { path, url });
  }

  #field(s, f) {
    const id = s.id;
    const value = s[f.key];
    const send = (v, notify) => { this.list.update(id, { [f.key]: v }, { notify }); this.onChange(); };
    let input;
    if (f.input === "check") {
      input = h("input", { type: "checkbox", checked: Boolean(value) });
      input.onchange = () => send(input.checked, true);
      return h("label", { className: "field check", dataset: { key: f.key } }, input, h("span", {}, f.label));
    }
    if (f.input === "entries" || f.input === "lines") {
      input = h("textarea", { rows: 5, value: f.input === "entries" ? formatEntries(value) : value.join("\n") });
      const read = () => (f.input === "entries" ? parseEntries(input.value) : input.value.split(/\r?\n/));
      input.oninput = () => send(read(), false);
      input.onchange = () => send(read(), true);
    } else if (f.input === "list") {
      input = h("input", { type: "text", value: value.join(", ") });
      const read = () => input.value.split(",").map(v => v.trim()).filter(Boolean);
      input.oninput = () => send(read(), false);
      input.onchange = () => send(read(), true);
    } else if (f.input === "select") {
      input = h("select", {}, ...Object.entries(f.options).map(([v, label]) => h("option", { value: v }, label)));
      input.value = String(value);
      input.onchange = () => send(input.value, true);
    } else if (f.input === "percent") {
      input = h("input", { type: "number", min: "0", max: String(f.max || 100), step: "5", value: String(Math.round(value * 100)) });
      input.oninput = () => send(Number(input.value) / 100, false);
      input.onchange = () => send(Number(input.value) / 100, true);
    } else {
      input = h("input", { type: f.input === "number" ? "number" : f.input === "color" ? "color" : "text", value: String(value) });
      const read = () => (f.input === "number" ? Number(input.value) : input.value);
      input.oninput = () => send(read(), false);
      input.onchange = () => send(read(), true);
    }
    const unit = f.input === "percent" ? " %" : "";
    return h("label", { className: "field", dataset: { key: f.key } }, h("span", {}, f.label + unit), input);
  }
}
