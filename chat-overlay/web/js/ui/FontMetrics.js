// 글꼴의 윗선 · 아랫선 비율(em 기준)을 캔버스로 잰다. libass 글자 크기를 CSS 크기로 바꾸거나 기준선을 잡을 때 쓴다.
const PROBE_PX = 100;

export class FontMetrics {
  #cache = new Map();
  #ctx = document.createElement("canvas").getContext("2d");

  /** { asc, desc } : em 대비 윗선 · 아랫선 비율. 못 재면 맑은 고딕 근삿값. */
  measure(family) {
    if (this.#cache.has(family)) return this.#cache.get(family);
    this.#ctx.font = `${PROBE_PX}px "${family}", "Malgun Gothic", sans-serif`;
    const m = this.#ctx.measureText("가Ag");
    const asc = m.fontBoundingBoxAscent / PROBE_PX, desc = m.fontBoundingBoxDescent / PROBE_PX;
    const ok = Number.isFinite(asc) && Number.isFinite(desc) && asc + desc > 0;
    const value = ok ? { asc, desc } : { asc: 1.08, desc: 0.25 };
    // ttf 를 막 올린 직후처럼 아직 글꼴이 준비 안 됐으면 저장하지 않고 다음에 다시 잰다
    if (ok && document.fonts.check(this.#ctx.font)) this.#cache.set(family, value);
    return value;
  }

  /** (윗선 + 아랫선) / em */
  lineRatio(family) {
    const { asc, desc } = this.measure(family);
    return asc + desc;
  }

  /** libass 줄 상자 안에서 기준선 위치 (줄 높이 대비 윗선 몫) */
  ascentShare(family) {
    const { asc, desc } = this.measure(family);
    return asc / (asc + desc);
  }

  forget() {
    this.#cache.clear();
  }
}
