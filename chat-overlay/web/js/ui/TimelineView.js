// 타임라인: 속도 곡선 + 구간 + 채팅이 올라오는 시각 + 재생 위치. 클릭 = 이동, 드래그 = 구간 만들기
import { TimelineGesture, TimelineScale } from "../core/timeline.js";
import { fmtMul } from "../core/format.js";

const LOG_MAX = Math.log(8);  // 세로 범위 1/8배 ~ 8배
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export class TimelineView {
  #length = 60;

  constructor(canvas, { onSeek, onCreateSection, onChange }) {
    this.canvas = canvas;
    this.gesture = new TimelineGesture(() => new TimelineScale(this.#length, canvas.clientWidth || 1));
    canvas.addEventListener("pointerdown", e => {
      canvas.setPointerCapture(e.pointerId);
      this.gesture.down(e.offsetX);
      onChange();
    });
    canvas.addEventListener("pointermove", e => { this.gesture.move(e.offsetX); onChange(); });
    canvas.addEventListener("pointerup", e => {
      const action = this.gesture.up(e.offsetX);
      if (action?.type === "seek") onSeek(action.t);
      if (action?.type === "section") onCreateSection(action.start, action.end);
      onChange();
    });
  }

  draw({ curve, length, now, events, donations = [], sections, selected }) {
    this.#length = length;
    const cv = this.canvas, dpr = window.devicePixelRatio || 1;
    const W = cv.clientWidth, H = cv.clientHeight;
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) {
      cv.width = Math.round(W * dpr);
      cv.height = Math.round(H * dpr);
    }
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const scale = new TimelineScale(length, W);
    const top = 16, bottom = H - 14, mid = (top + bottom) / 2, half = (bottom - top) / 2;
    const yOf = s => mid - clamp(Math.log(s) / LOG_MAX, -1, 1) * half;

    ctx.font = "11px sans-serif";
    sections.forEach((s, i) => {
      const fast = s.speed >= 1, x0 = scale.xOf(s.start), x1 = scale.xOf(s.end);
      ctx.globalAlpha = i === selected ? 0.34 : 0.18;
      ctx.fillStyle = css(fast ? "--fast" : "--slow");
      ctx.fillRect(x0, 0, x1 - x0, H);
      ctx.globalAlpha = 1;
      ctx.fillText(fmtMul(s.speed), x0 + 3, 12);
    });
    const drag = this.gesture.preview;
    if (drag) {
      ctx.fillStyle = "rgba(122,162,255,.25)";
      ctx.fillRect(scale.xOf(drag.start), 0, scale.xOf(drag.end) - scale.xOf(drag.start), H);
    }

    ctx.strokeStyle = "rgba(143,152,173,.22)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "rgba(143,152,173,.8)";
    ctx.font = "10px sans-serif";
    [[4, "4x"], [1, "1x"], [0.25, "1/4x"]].forEach(([s, label]) => {
      ctx.beginPath(); ctx.moveTo(0, yOf(s)); ctx.lineTo(W, yOf(s)); ctx.stroke();
      ctx.fillText(label, W - ctx.measureText(label).width - 4, yOf(s) - 2);
    });

    ctx.strokeStyle = css("--accent");
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let px = 0; px <= W; px++) {
      const y = yOf(curve.at(scale.tAt(px)));
      px ? ctx.lineTo(px, y) : ctx.moveTo(px, y);
    }
    ctx.stroke();

    ctx.fillStyle = "rgba(232,236,244,.45)";
    for (const e of events) if (!e.highlight) ctx.fillRect(Math.floor(scale.xOf(e.t)), H - 10, 1, 8);

    // 후원: 분홍 하트
    ctx.fillStyle = "#ff5fa2";
    ctx.font = "11px sans-serif";
    for (const d of donations) ctx.fillText("♥", scale.xOf(d.t) - 4, H - 12);

    ctx.strokeStyle = css("--ok");
    ctx.lineWidth = 2;
    const px = scale.xOf(now);
    ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, H); ctx.stroke();
  }
}
