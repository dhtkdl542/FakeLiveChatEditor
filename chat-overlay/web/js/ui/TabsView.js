// 오른쪽 설정 탭
import { $$ } from "./dom.js";

export class TabsView {
  constructor(nav, panels, onSelect = () => {}) {
    this.nav = nav;
    this.panels = panels;
    this.onSelect = onSelect;
    nav.addEventListener("click", e => {
      const btn = e.target.closest("[data-tab]");
      if (btn) this.select(btn.dataset.tab);
    });
  }

  get current() {
    return this.nav.querySelector(".active")?.dataset.tab;
  }

  select(name) {
    if (!this.nav.querySelector(`[data-tab="${name}"]`)) return;
    for (const b of $$("[data-tab]", this.nav)) b.classList.toggle("active", b.dataset.tab === name);
    for (const p of $$("[data-panel]", this.panels)) p.classList.toggle("active", p.dataset.panel === name);
    this.onSelect(name);
  }
}
