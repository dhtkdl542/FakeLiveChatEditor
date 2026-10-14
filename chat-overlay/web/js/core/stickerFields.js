// 스티커 종류별 편집 칸. 화면은 이 목록을 보고 입력칸을 만든다.
import { AlertSticker } from "./stickers.js";

const UNIT = { key: "unit", label: "후원 단위 (비우면 플랫폼 단위)", input: "text" };
const PANEL_STYLE = [
  { key: "accent", label: "강조 색", input: "color" },
  { key: "textColor", label: "글자 색", input: "color" },
  { key: "bg", label: "바탕 색", input: "color" },
  { key: "bgOpacity", label: "바탕 불투명도", input: "percent" },
  { key: "borderColor", label: "테두리 색", input: "color" },
  { key: "borderWidth", label: "테두리 두께", input: "number" },
  { key: "font", label: "글꼴", input: "text" },
];
const COMMON = [{ key: "scale", label: "크기", input: "percent", max: 500 }];

export const STICKER_FIELDS = Object.freeze({
  text: [
    { key: "text", label: "글자", input: "text" },
    { key: "heart", label: "하트 붙이기", input: "check" },
    { key: "fill", label: "글자 색", input: "color" },
    { key: "outer", label: "바깥 테두리", input: "color" },
    { key: "inner", label: "안쪽 테두리", input: "color" },
    { key: "heartColor", label: "하트 색", input: "color" },
    { key: "size", label: "글자 크기", input: "number" },
    { key: "innerWidth", label: "안쪽 두께", input: "number" },
    { key: "outerWidth", label: "바깥 두께", input: "number" },
    { key: "font", label: "글꼴", input: "text" },
    ...COMMON,
  ],
  ranking: [
    { key: "title", label: "제목", input: "text" },
    { key: "entries", label: "기본 순위 (한 줄에 '닉 숫자')", input: "entries" },
    { key: "rows", label: "보일 줄 수", input: "number" },
    { key: "auto", label: "후원 들어오면 순위 갱신", input: "check" },
    { key: "width", label: "폭", input: "number" },
    ...PANEL_STYLE, ...COMMON,
  ],
  goal: [
    { key: "title", label: "제목", input: "text" },
    { key: "current", label: "시작 개수", input: "number" },
    { key: "target", label: "목표 개수", input: "number" },
    { key: "auto", label: "후원 들어오면 채우기", input: "check" },
    { key: "track", label: "게이지 바탕", input: "color" },
    { key: "width", label: "폭", input: "number" },
    ...PANEL_STYLE, ...COMMON,
  ],
  banner: [
    { key: "lines", label: "내용 (한 줄씩, 첫 줄이 제목)", input: "lines" },
    { key: "width", label: "폭", input: "number" },
    ...PANEL_STYLE, ...COMMON,
  ],
  table: [
    { key: "title", label: "제목 (비우면 없음)", input: "text" },
    { key: "headers", label: "머리줄 (쉼표로 구분)", input: "list" },
    { key: "entries", label: "멤버와 시작 점수 (한 줄에 '이름 숫자')", input: "entries" },
    { key: "rows", label: "보일 줄 수", input: "number" },
    { key: "auto", label: "후원 들어오면 멤버 점수 올리기", input: "check" },
    { key: "showTotal", label: "총합 줄", input: "check" },
    { key: "highlightRow", label: "강조할 줄 번호 (0 = 없음)", input: "number" },
    { key: "width", label: "폭", input: "number" },
    { key: "headerBg", label: "머리줄 바탕", input: "color" },
    { key: "headerText", label: "머리줄 글자", input: "color" },
    { key: "titleBg", label: "제목 바탕", input: "color" },
    { key: "titleText", label: "제목 글자", input: "color" },
    { key: "cellBg", label: "칸 바탕", input: "color" },
    { key: "cellText", label: "칸 글자", input: "color" },
    { key: "highlight", label: "강조 줄 색", input: "color" },
    { key: "totalBg", label: "총합 줄 색", input: "color" },
    { key: "grid", label: "칸막이 색", input: "color" },
    { key: "bgOpacity", label: "불투명도", input: "percent" },
    { key: "font", label: "글꼴", input: "text" },
    ...COMMON,
  ],
  history: [
    { key: "entries", label: "처음 쌓여 있는 카드 (한 줄에 '닉 숫자', 위가 최신)", input: "entries" },
    { key: "count", label: "보일 카드 수", input: "number" },
    { key: "auto", label: "후원 들어오면 맨 위에 쌓기", input: "check" },
    UNIT,
    { key: "width", label: "카드 폭", input: "number" },
    { key: "bg", label: "카드 바탕", input: "color" },
    { key: "bgOpacity", label: "불투명도", input: "percent" },
    { key: "textColor", label: "글자 색", input: "color" },
    { key: "font", label: "글꼴", input: "text" },
    ...COMMON,
  ],
  mvp: [
    { key: "label", label: "앞 글자", input: "text" },
    { key: "entries", label: "기본 후원 (한 줄에 '닉 숫자')", input: "entries" },
    { key: "auto", label: "후원 들어오면 MVP 바꾸기", input: "check" },
    { key: "size", label: "글자 크기", input: "number" },
    { key: "labelColor", label: "앞 글자 색", input: "color" },
    { key: "nickColor", label: "닉 색", input: "color" },
    { key: "amountColor", label: "숫자 색", input: "color" },
    { key: "outline", label: "테두리 색", input: "color" },
    { key: "outlineWidth", label: "테두리 두께", input: "number" },
    { key: "font", label: "글꼴", input: "text" },
    ...COMMON,
  ],
  alert: [
    { key: "style", label: "후원창 모양", input: "select", options: AlertSticker.STYLES },
    UNIT,
    { key: "show", label: "보이는 시간 (초)", input: "number" },
    { key: "width", label: "폭", input: "number" },
    ...PANEL_STYLE, ...COMMON,
  ],
  image: [
    { key: "height", label: "높이 (1080p 기준 px)", input: "number" },
    ...COMMON,
  ],
});

/** "별사 6558" 처럼 한 줄에 '닉 숫자'. 닉에 띄어쓰기가 있어도 마지막 숫자만 금액으로 본다. */
export function parseEntries(text) {
  return String(text || "").split(/\r?\n/).map(l => l.trim()).filter(Boolean).map(line => {
    const m = line.match(/^(.*?)\s+([\d,]+)$/);
    return m ? [m[1].trim(), Number(m[2].replace(/,/g, ""))] : [line, 0];
  });
}

export function formatEntries(entries) {
  return entries.map(([nick, amount]) => `${nick} ${amount}`).join("\n");
}
