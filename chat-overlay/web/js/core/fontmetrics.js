// libass 는 글자 크기를 '윗선~아랫선 전체 높이'로 쓰고, CSS 는 em 으로 쓴다.
// 그래서 같은 숫자라도 libass 쪽 글자가 작다 (맑은 고딕은 약 1.33배). 미리보기를 결과 영상과 맞추려면 나눠 준다.

/** lineRatio = (윗선 + 아랫선) / em. 화면 쪽 FontMetrics 가 캔버스로 재서 넘겨준다. */
export function cssFontPx(assPx, lineRatio) {
  return lineRatio > 0 ? assPx / lineRatio : assPx;
}
