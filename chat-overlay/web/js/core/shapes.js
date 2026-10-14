// ASS 벡터 드로잉(\p3, 좌표 = 픽셀 × 4) 으로 둥근 사각형과 테두리 고리. chatov/shapes.py 와 같은 경로.
export const UNIT = 4;
const KAPPA = 0.5523;

const q = v => Math.floor(v * UNIT + 0.5);
const pt = (x, y) => `${q(x)} ${q(y)}`;
const radius = (w, h, r) => Math.max(0, Math.min(r, w / 2, h / 2));

export function roundedRectDrawing(w, h, r, x0 = 0, y0 = 0) {
  r = radius(w, h, r);
  const p = (x, y) => pt(x0 + x, y0 + y);
  if (r === 0) return `m ${p(0, 0)} l ${p(w, 0)} l ${p(w, h)} l ${p(0, h)} l ${p(0, 0)}`;
  const c = KAPPA * r;
  return [
    `m ${p(r, 0)}`, `l ${p(w - r, 0)}`, `b ${p(w - r + c, 0)} ${p(w, r - c)} ${p(w, r)}`,
    `l ${p(w, h - r)}`, `b ${p(w, h - r + c)} ${p(w - r + c, h)} ${p(w - r, h)}`,
    `l ${p(r, h)}`, `b ${p(r - c, h)} ${p(0, h - r + c)} ${p(0, h - r)}`,
    `l ${p(0, r)}`, `b ${p(0, r - c)} ${p(r - c, 0)} ${p(r, 0)}`,
  ].join(" ");
}

function reversedRect(w, h, r, x0, y0) {
  r = radius(w, h, r);
  const p = (x, y) => pt(x0 + x, y0 + y);
  if (r === 0) return `m ${p(0, 0)} l ${p(0, h)} l ${p(w, h)} l ${p(w, 0)} l ${p(0, 0)}`;
  const c = KAPPA * r;
  return [
    `m ${p(r, 0)}`, `b ${p(r - c, 0)} ${p(0, r - c)} ${p(0, r)}`, `l ${p(0, h - r)}`,
    `b ${p(0, h - r + c)} ${p(r - c, h)} ${p(r, h)}`, `l ${p(w - r, h)}`,
    `b ${p(w - r + c, h)} ${p(w, h - r + c)} ${p(w, h - r)}`, `l ${p(w, r)}`,
    `b ${p(w, r - c)} ${p(w - r + c, 0)} ${p(w - r, 0)}`, `l ${p(r, 0)}`,
  ].join(" ");
}

export function ringDrawing(w, h, r, border) {
  if (border * 2 >= Math.min(w, h)) return roundedRectDrawing(w, h, r);
  return roundedRectDrawing(w, h, r) + " " +
    reversedRect(w - 2 * border, h - 2 * border, Math.max(0, r - border), border, border);
}

/** ASS 드로잉(m / l / b, 좌표 × unit)을 SVG 경로로. 여러 조각(m)은 각각 닫는다. */
export function drawingToSvg(path, unit = UNIT) {
  const out = [];
  let cmd = null, nums = [];
  const flush = () => {
    const per = cmd === "b" ? 6 : 2;
    for (let i = 0; i + per <= nums.length; i += per) {
      const letter = cmd === "m" ? (i === 0 ? "M" : "L") : cmd === "b" ? "C" : "L";
      out.push(letter, ...nums.slice(i, i + per).map(n => n / unit));
    }
  };
  for (const tok of path.trim().split(/\s+/)) {
    if (tok === "m" || tok === "l" || tok === "b") {
      if (cmd) flush();
      if (tok === "m" && out.length) out.push("Z");
      cmd = tok;
      nums = [];
    } else nums.push(Number(tok));
  }
  if (cmd) flush();
  return out.length ? out.join(" ") + " Z" : "";
}
