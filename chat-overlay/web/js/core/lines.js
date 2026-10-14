// 여러 줄 입력칸 다루기
export function linesOf(text) {
  return String(text || "").split(/\r?\n/).map(s => s.trim()).filter(Boolean);
}

/** AI가 만든 줄을 기존 목록에 넣는다. append 는 이미 있는 줄을 빼고 뒤에 붙인다. */
export function mergeLines(existing, incoming, mode) {
  if (mode !== "append") return [...incoming];
  const seen = new Set(existing);
  return [...existing, ...incoming.filter(l => !seen.has(l))];
}
