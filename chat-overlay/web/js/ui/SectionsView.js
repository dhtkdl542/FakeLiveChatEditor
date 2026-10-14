// 구간별 속도 목록 편집
import { SectionList } from "../core/sections.js";
import { speedLabel } from "../core/format.js";
import { h } from "./dom.js";

export class SectionsView {
  constructor(root, sections, { onPlayFrom }) {
    this.root = root;
    this.sections = sections;
    this.onPlayFrom = onPlayFrom;
    sections.subscribe(() => this.render());
    this.render();
  }

  render() {
    const list = this.sections;
    if (!list.items.length) {
      this.root.replaceChildren(h("p", { className: "status" },
        "아직 구간이 없습니다. 위 타임라인을 드래그하거나 [지금 위치에 구간 추가]를 누르세요."));
      return;
    }
    this.root.replaceChildren(...list.items.map((s, i) => this.#row(s, i)));
  }

  #row(s, i) {
    const list = this.sections;
    const dot = h("span", { className: "sec-dot " + (s.speed >= 1 ? "fast" : "slow") });
    const label = h("b", {}, speedLabel(s.speed));
    const num = (value, onchange, title) => h("input", { type: "number", step: "0.1", min: "0", value: value.toFixed(1), title, onchange });
    const slider = h("input", { type: "range", min: "-100", max: "100", step: "1", value: String(SectionList.speedToSlider(s.speed)) });
    // 슬라이더를 끄는 동안 목록을 다시 그리면 손에서 놓치므로, 끄는 중엔 값만 바꾸고 놓을 때 다시 그린다
    slider.oninput = () => {
      const speed = SectionList.sliderToSpeed(Number(slider.value));
      label.textContent = speedLabel(speed);
      dot.className = "sec-dot " + (speed >= 1 ? "fast" : "slow");
      list.update(i, { speed }, { notify: false });
    };
    slider.onchange = () => list.update(i, { speed: SectionList.sliderToSpeed(Number(slider.value)) });
    slider.onfocus = () => list.select(i);
    return h("div", { className: "sec-item" + (i === list.selected ? " sel" : "") },
      dot,
      num(s.start, e => list.update(i, { start: Number(e.target.value) || 0 }), "시작(초)"),
      h("span", {}, "~"),
      num(s.end, e => list.update(i, { end: Number(e.target.value) || 0 }), "끝(초)"),
      h("span", {}, "초"),
      slider, label,
      h("button", { type: "button", className: "btn ghost", title: "이 구간 1초 전부터 재생",
        onclick: () => { list.select(i); this.onPlayFrom(Math.max(0, s.start - 1)); } }, "▶"),
      h("button", { type: "button", className: "btn ghost", onclick: () => list.remove(i) }, "삭제"));
  }
}
