// 닉네임 색 편집
import { $, h } from "./dom.js";

const PRESETS = ["#ffffff", "#ffff00", "#ffe066", "#ffb347", "#ff7a00", "#ff4d4d", "#ff80ff", "#c084fc",
  "#47b3ff", "#00e5ff", "#a0ffa0", "#39ff14", "#80ffff", "#c0c0c0", "#000000"];

export class PaletteView {
  #editing = false;  // 색 창을 드래그하는 동안 목록을 다시 그리면 창이 닫히므로 막는다

  constructor(palette, getNickCount) {
    this.palette = palette;
    $("#swatches").replaceChildren(...PRESETS.map(c =>
      h("button", { type: "button", className: "swatch", title: c, style: { background: c }, onclick: () => palette.add(c) })));
    $("#btnAddColor").onclick = () => palette.add();
    $("#btnFitColors").onclick = () => palette.fitTo(getNickCount());
    $("#btnRandomColors").onclick = () => palette.randomizeAll();
    palette.subscribe(() => { if (!this.#editing) this.render(); });
    this.render();
  }

  #editInPlace(i, value, other) {
    this.#editing = true;
    this.palette.set(i, value);
    this.#editing = false;
    other.value = this.palette.colors[i];
  }

  render() {
    $("#colors").replaceChildren(...this.palette.colors.map((c, i) => {
      const hex = h("input", { type: "text", value: c, maxLength: 7 });
      const picker = h("input", { type: "color", value: c });
      picker.oninput = () => this.#editInPlace(i, picker.value, hex);
      hex.onchange = () => this.#editInPlace(i, hex.value, picker);
      return h("div", { className: "color-item" },
        picker, hex,
        h("button", { type: "button", className: "btn ghost", onclick: () => this.palette.randomize(i) }, "랜덤"),
        h("button", { type: "button", className: "btn ghost", onclick: () => this.palette.remove(i) }, "삭제"));
    }));
  }
}
