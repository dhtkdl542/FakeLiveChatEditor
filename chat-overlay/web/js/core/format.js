// 화면 표시용 형식
export function fmtTime(t) {
  const v = Math.max(0, t || 0);
  return Math.floor(v / 60) + ":" + (v % 60).toFixed(1).padStart(4, "0");
}

export function fmtBytes(n) {
  return n >= 1e9 ? (n / 1e9).toFixed(2) + "GB" : (n / 1e6).toFixed(0) + "MB";
}

export function fmtMul(s) {
  return "×" + (s >= 1 ? s.toFixed(1) : s.toFixed(2));
}

export function speedLabel(s) {
  return fmtMul(s) + (s > 1.01 ? " 빠르게" : s < 0.99 ? " 느리게" : " 그대로");
}
