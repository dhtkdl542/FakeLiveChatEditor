// 미리보기에 스티커 · 후원 알림을 그리고, 스티커를 끌어 옮기거나 휠로 크기를 바꾼다.
// 그리는 도형은 core/stickers.js 가 만든 목록이고, 결과 영상(ASS)도 같은 목록을 그린다.
import { alertOpacity, alertScale, Donation, scheduleAlerts } from "../core/donations.js";
import { cssFontPx } from "../core/fontmetrics.js";
import { platformOf } from "../core/platforms.js";
import { StickerState } from "../core/stickers.js";
import { h } from "./dom.js";

// 알림 자리를 골랐을 때 보여 줄 견본 (플랫폼에서 흔한 금액)
const sample = platform => new Donation(0, "닉네임", platformOf(platform).amounts[3], "");
const SVG_NS = "http://www.w3.org/2000/svg";
const TRANSLATE_X = { left: "0", center: "-50%", right: "-100%" };

export class StickerLayer {
  /** 마지막으로 그린 스티커 도형 (id → 도형 목록). 알림은 튀어나오는 중일 수 있어 뺀다. 화면 검사용. */
  lastPrims = new Map();
  #drag = null;
  #slotsKey = null;
  #slots = [];

  constructor({ stage, below, above, hit, list, metrics, onChange }) {
    Object.assign(this, { stage, below, above, hit, list, metrics, onChange });
    window.addEventListener("pointermove", e => this.#move(e));
    window.addEventListener("pointerup", () => this.#end());
  }

  // ---------- 도형 그리기 ----------
  #rect(p, k) {
    return h("div", { className: "prim rect", style: {
      left: (p.cx - p.w / 2) * k + "px", top: (p.cy - p.h / 2) * k + "px", width: p.w * k + "px", height: p.h * k + "px",
      borderRadius: p.r * k + "px", background: p.color, border: p.borderW > 0 ? `${p.borderW * k}px solid ${p.borderColor}` : "0",
      boxSizing: "border-box", opacity: String(p.opacity), zIndex: String(p.layer),
    } });
  }

  /** 테두리가 굵은 한 줄 글자(글자 스티커)는 SVG 로: 모서리를 libass 처럼 둥글게 그릴 수 있다 */
  #svgText(p, k) {
    const line = p.lines[0];
    const size = Math.max(...line.map(r => r.size));
    const font = line[0].font;
    // libass 줄 상자: 높이 = 글자 크기, 가운데 = p.y, 기준선 = 위에서 (윗선 몫 × 높이)
    const baseline = p.y - size / 2 + size * this.metrics.ascentShare(font);
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", "prim text");
    svg.setAttribute("width", "1");
    svg.setAttribute("height", "1");
    Object.assign(svg.style, { left: p.x * k + "px", top: baseline * k + "px", overflow: "visible", zIndex: String(p.layer) });
    const text = document.createElementNS(SVG_NS, "text");
    text.setAttribute("x", "0");
    text.setAttribute("y", "0");
    text.setAttribute("text-anchor", { left: "start", center: "middle", right: "end" }[p.align]);
    text.setAttribute("stroke", p.outlineColor);
    text.setAttribute("stroke-width", String(2 * p.outlineW * k));
    text.setAttribute("stroke-linejoin", "round");
    text.setAttribute("paint-order", "stroke fill");
    for (const r of line) {
      const span = document.createElementNS(SVG_NS, "tspan");
      span.setAttribute("font-family", `"${r.font}", "Malgun Gothic", sans-serif`);
      span.setAttribute("font-size", String(cssFontPx(r.size, this.metrics.lineRatio(r.font)) * k));
      span.setAttribute("font-weight", r.bold ? "700" : "400");
      span.setAttribute("fill", r.color);
      span.textContent = r.text;
      text.append(span);
    }
    svg.append(text);
    return svg;
  }

  #text(p, k) {
    if (p.outlineW > 0 && p.lines.length === 1) return this.#svgText(p, k);
    const el = h("div", { className: "prim text", style: {
      left: p.x * k + "px", top: p.y * k + "px", transform: `translate(${TRANSLATE_X[p.align]}, -50%)`,
      textAlign: p.align, zIndex: String(p.layer),
    } });
    for (const line of p.lines) {
      const row = h("div", { style: { lineHeight: Math.max(...line.map(r => r.size)) * k + "px" } });
      for (const r of line) {
        row.append(h("span", { style: {
          fontFamily: `"${r.font}", "Malgun Gothic", sans-serif`,
          fontSize: cssFontPx(r.size, this.metrics.lineRatio(r.font)) * k + "px",
          fontWeight: r.bold ? "700" : "400", color: r.color,
          webkitTextStroke: p.outlineW > 0 ? `${2 * p.outlineW * k}px ${p.outlineColor}` : "0",
          paintOrder: "stroke fill",
        } }, r.text));
      }
      el.append(row);
    }
    return el;
  }

  #image(p, k) {
    const style = { left: (p.cx - p.w / 2) * k + "px", top: (p.cy - p.h / 2) * k + "px", width: p.w * k + "px", height: p.h * k + "px" };
    return p.url ? h("img", { className: "prim image", src: p.url, draggable: false, style })
      : h("div", { className: "prim missing", style }, "그림 없음");
  }

  #group(prims, k, extraStyle = {}, id = "") {
    const g = h("div", { className: "group", style: extraStyle, dataset: { id } });
    for (const p of prims) g.append(p.kind === "rect" ? this.#rect(p, k) : p.kind === "text" ? this.#text(p, k) : this.#image(p, k));
    return g;
  }

  // ---------- 끌어 옮기기 ----------
  #handle(group, id) {
    const stageBox = this.stage.getBoundingClientRect();
    let l = Infinity, t = Infinity, r = -Infinity, b = -Infinity;
    for (const el of group.children) {
      const box = el.getBoundingClientRect();
      l = Math.min(l, box.left); t = Math.min(t, box.top); r = Math.max(r, box.right); b = Math.max(b, box.bottom);
    }
    if (!Number.isFinite(l)) return;
    const handle = h("div", { className: "handle" + (id === this.list.selectedId ? " selected" : ""), dataset: { id }, style: {
      left: l - stageBox.left + "px", top: t - stageBox.top + "px", width: r - l + "px", height: b - t + "px",
    } });
    handle.addEventListener("pointerdown", e => this.#start(e, id));
    handle.addEventListener("click", e => e.stopPropagation());
    handle.addEventListener("wheel", e => {
      e.preventDefault();
      this.list.scaleBy(id, e.deltaY < 0 ? 1.08 : 1 / 1.08);
    }, { passive: false });
    this.hit.append(handle);
  }

  #start(e, id) {
    e.stopPropagation();
    e.preventDefault();
    const s = this.list.get(id);
    this.list.select(id);
    this.#drag = { id, x0: s.x, y0: s.y, px: e.clientX, py: e.clientY, moved: false };
  }

  #move(e) {
    const d = this.#drag;
    if (!d) return;
    const box = this.stage.getBoundingClientRect();
    d.moved = true;
    this.list.moveTo(d.id, d.x0 + (e.clientX - d.px) / box.width, d.y0 + (e.clientY - d.py) / box.height, { notify: false });
    this.onChange();
  }

  #end() {
    const d = this.#drag;
    this.#drag = null;
    if (d && d.moved) this.list.update(d.id, {});  // 다 끈 뒤 한 번 알려서 저장 · 패널 갱신
  }

  #alertSlots(donations, length, show) {
    const key = [donations, length, show];
    if (!this.#slotsKey || this.#slotsKey.some((v, i) => v !== key[i])) {
      this.#slotsKey = key;
      this.#slots = scheduleAlerts(donations, length, show);
    }
    return this.#slots;
  }

  render({ source, now, donations, length, unit = "하트", platform = "panda" }) {
    const { width, height } = source.resolution;
    const k = (this.stage.clientWidth || 1) / width;
    const state = StickerState.at(donations, now, unit, platform);
    this.below.replaceChildren();
    this.above.replaceChildren();
    this.hit.replaceChildren();
    this.lastPrims = new Map();
    for (const s of this.list.stickers()) {
      if (s.type === "alert") {
        const slot = this.#alertSlots(donations, length, s.show).find(a => a.start <= now && now < a.end);
        const selected = s.id === this.list.selectedId;
        if (!slot && !selected) continue;
        const ms = slot ? (now - slot.start) * 1000 : 1000;
        const [cx, cy] = s.center(width, height);
        const group = this.#group(s.layoutAlert(width, height, slot ? slot.donation : sample(platform), state), k, {
          transformOrigin: `${cx * k}px ${cy * k}px`,
          transform: `scale(${slot ? alertScale(ms) : 1})`,
          opacity: String(slot ? alertOpacity(ms, (slot.end - slot.start) * 1000) : 0.55),
        }, s.id);
        this.above.append(group);
        this.#handle(group, s.id);
        continue;
      }
      const prims = s.layout(width, height, state);
      const group = this.#group(prims, k, {}, s.id);
      this.lastPrims.set(s.id, prims);
      this.below.append(group);
      this.#handle(group, s.id);
    }
  }
}
