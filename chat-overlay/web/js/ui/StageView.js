// 미리보기 화면: 영상(또는 샘플 배경) 위에 ASS 자막과 같은 자리·크기·모양으로 채팅을 그린다
import { cssFontPx } from "../core/fontmetrics.js";
import { iconShape, iconSvgPath } from "../core/icons.js";
import { h } from "./dom.js";

const SVG_NS = "http://www.w3.org/2000/svg";

function iconSvg(name, sizePx, color, outlinePx) {
  const shape = iconShape(name);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${shape.width} 100`);
  svg.setAttribute("width", String((shape.width * sizePx) / 100));
  svg.setAttribute("height", String(sizePx));
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", iconSvgPath(name));
  path.setAttribute("fill", color);
  if (outlinePx > 0) {
    // libass 는 드로잉에도 바깥 테두리를 그린다. SVG 선은 가운데 기준이라 두 배 굵기로 그리고 채움 아래에 깐다
    path.setAttribute("stroke", "#000");
    path.setAttribute("stroke-width", String((2 * outlinePx * 100) / sizePx));
    path.setAttribute("stroke-linejoin", "round");
    path.setAttribute("paint-order", "stroke fill");
  }
  svg.append(path);
  return svg;
}

export class StageView {
  constructor({ box, stage, video, overlay, badge, metrics }) {
    Object.assign(this, { box, stage, video, overlay, badge, metrics });
  }

  /** 영상 비율을 지키면서 칸에 맞춘다. 반환값 = 화면 px / 영상 px */
  #fit(width, height) {
    const maxW = this.box.clientWidth || 800;
    const maxH = Math.max(240, window.innerHeight * 0.58);
    const w = Math.min(maxW, (maxH * width) / height);
    const hgt = (w * height) / width;
    if (this.stage.style.width !== w + "px") this.stage.style.width = w + "px";
    if (this.stage.style.height !== hgt + "px") this.stage.style.height = hgt + "px";
    return w / width;
  }

  render({ source, layout, frame, now }) {
    const { width, height } = source.resolution;
    const k = this.#fit(width, height);
    this.video.hidden = !(source.hasVideo && source.playable);
    this.stage.classList.toggle("sample", !source.hasVideo);
    this.badge.textContent = !source.hasVideo ? "샘플 화면 (1920×1080)"
      : source.playable ? "" : "브라우저가 재생할 수 없는 형식 · 채팅만 미리보기";
    this.overlay.replaceChildren(...frame.rows.map(row => this.#line(row, layout, frame, now, width, height, k)));
  }

  #line(row, layout, frame, now, width, height, k) {
    const s = layout.style;
    const { x, y, align } = layout.position(row, width, height);
    const { textOpacity, background, radius, border } = layout.paint(row);
    const nickPx = cssFontPx(s.nickSize, this.metrics.lineRatio(s.nickFont)) * k;
    const msgPx = cssFontPx(s.msgSize, this.metrics.lineRatio(s.msgFont)) * k;
    const nickFont = `"${s.nickFont}", "Malgun Gothic", sans-serif`;
    const msgFont = `"${s.msgFont}", "Malgun Gothic", sans-serif`;
    // libass 처럼: 줄 높이 = 가장 큰 글자 크기, (x, y) = 글자 줄의 아래 모서리, 박스는 그 바깥으로 여백만큼.
    // 요소는 박스 바깥 모서리 기준으로 놓는다.
    const pad = s.padding(row);
    const outerX = align === "right" ? x + pad : x - pad;
    const outerY = y + pad;
    const line = h("div", { className: "vline", style: {
      left: outerX * k + "px", top: outerY * k + "px",
      lineHeight: Math.max(s.nickSize, s.msgSize) * k + "px",
      transform: align === "right" ? "translate(-100%, -100%)" : "translateY(-100%)",
      opacity: String(layout.fade(row, now, frame.startT, frame.nextT)),
      background: background || "transparent",
      padding: pad * k + "px",
      // 둥근 · 알약 박스와 테두리: 결과 영상도 같은 크기의 도형을 박스 안쪽 테두리로 그린다
      borderRadius: radius * k + "px",
      boxShadow: border ? `inset 0 0 0 ${border.width * k}px ${border.color}` : "none",
    } });
    // 박스가 없으면 libass 처럼 매끈한 바깥 테두리 (선은 가운데 기준이라 두 배 굵기로, 채움 아래에)
    const outlinePx = background ? 0 : s.outline * k;
    const text = (content, font, px, color, bold) => h("span", { style: {
      fontFamily: font, fontSize: px + "px", fontWeight: bold ? "700" : "400",
      color, opacity: String(textOpacity),
      webkitTextStroke: outlinePx > 0 ? `${2 * outlinePx}px #000` : "0",
      paintOrder: "stroke fill",
    } }, content);

    if (row.nick) {
      // 공통 아이콘 다음에 닉네임 배지 (같은 닉은 늘 같은 배지)
      for (const [name, color] of s.icons(row)) {
        if (!iconShape(name)) continue;
        const icon = iconSvg(name, layout.iconSize() * k, color, outlinePx);
        icon.style.opacity = String(textOpacity);
        line.append(icon, text(" ", msgFont, msgPx, "#fff", false));
      }
      line.append(text(row.nick + " ", nickFont, nickPx, row.color, s.nickBold));
    }
    line.append(row.highlight ? text(row.msg, msgFont, msgPx, "#ffffff", true) : text(row.msg, msgFont, msgPx, s.msgColor, false));
    return line;
  }
}
