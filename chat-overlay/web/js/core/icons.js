// 닉네임 앞 아이콘. chatov/icons.py 와 같은 모양(ASS 드로잉 문법)을 같은 방식으로 정규화해 SVG 로 그린다.
export const ICON_NAMES = ["circle", "rounded", "heart", "star", "crown", "diamond", "shield"];

export const ICON_LABELS = {
  circle: "● 원", rounded: "■ 둥근 사각", heart: "♥ 하트", star: "★ 별", crown: "♛ 왕관", diamond: "◆ 다이아", shield: "⛨ 방패",
};

const RAW = {
  circle: "m 50 0 b 77.6 0 100 22.4 100 50 b 100 77.6 77.6 100 50 100 b 22.4 100 0 77.6 0 50 b 0 22.4 22.4 0 50 0",
  rounded: "m 20 0 l 80 0 b 91 0 100 9 100 20 l 100 80 b 100 91 91 100 80 100 l 20 100 b 9 100 0 91 0 80 " +
    "l 0 20 b 0 9 9 0 20 0",
  heart: "m 50 92 b 20 70 0 52 0 30 b 0 13 13 2 28 2 b 38 2 46 8 50 16 b 54 8 62 2 72 2 b 87 2 100 13 100 30 " +
    "b 100 52 80 70 50 92",
  star: "m 50 0 l 61.8 35.4 99 35.4 69.1 57.3 80.3 92.7 50 70.8 19.7 92.7 30.9 57.3 1 35.4 38.2 35.4",
  crown: "m 0 85 l 0 25 27 50 50 10 73 50 100 25 100 85",
  diamond: "m 50 0 l 100 50 50 100 0 50",
  shield: "m 50 0 l 100 14 l 100 48 b 100 76 78 94 50 100 b 22 94 0 76 0 48 l 0 14 l 50 0",
};

const TOKEN = /[mlb]|-?\d+(?:\.\d+)?/g;
const fmt = v => String(Math.floor(v * 100 + 0.5) / 100);

function transform(path, fn) {
  const out = [];
  let pending = null;
  for (const tok of path.match(TOKEN)) {
    if ("mlb".includes(tok)) out.push(tok);
    else if (pending === null) pending = Number(tok);
    else { out.push(...fn(pending, Number(tok))); pending = null; }
  }
  return out.join(" ");
}

function normalize(path) {
  const nums = path.match(TOKEN).filter(t => !"mlb".includes(t)).map(Number);
  const xs = nums.filter((_, i) => i % 2 === 0), ys = nums.filter((_, i) => i % 2 === 1);
  const x0 = Math.min(...xs), y0 = Math.min(...ys), k = 100 / (Math.max(...ys) - y0);
  return Object.freeze({
    path: transform(path, (x, y) => [fmt((x - x0) * k), fmt((y - y0) * k)]),
    width: (Math.max(...xs) - x0) * k,
  });
}

const SHAPES = Object.fromEntries(ICON_NAMES.map(n => [n, normalize(RAW[n])]));

export function iconShape(name) {
  return SHAPES[name] || null;
}

/** ASS 드로잉(m / l / b)을 SVG 경로(M / L / C)로. 좌표는 세로 0~100 기준. */
export function iconSvgPath(name) {
  const shape = iconShape(name);
  if (!shape) return "";
  const out = [];
  let cmd = null, nums = [];
  const flush = () => {
    const per = cmd === "b" ? 6 : 2;
    for (let i = 0; i + per <= nums.length; i += per) {
      const letter = cmd === "m" && i === 0 ? "M" : cmd === "b" ? "C" : "L";
      out.push(letter, ...nums.slice(i, i + per));
    }
  };
  for (const tok of shape.path.split(" ")) {
    if ("mlb".includes(tok)) { if (cmd) flush(); cmd = tok; nums = []; }
    else nums.push(tok);
  }
  if (cmd) flush();
  return out.join(" ") + " Z";
}
