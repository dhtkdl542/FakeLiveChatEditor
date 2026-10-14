// 채팅창 템플릿: 채팅 줄의 모양 · 배치만 바꾼다 (스티커 · 후원 · 대사는 그대로).
// 모든 템플릿이 같은 칸을 바꾸므로 차례로 골라도 앞 템플릿 값이 남지 않는다. 고른 뒤 자유롭게 고칠 수 있다.
const BASE = Object.freeze({
  align: "right", sideMargin: "24", bottomMargin: "24", lineH: "36", visible: "8", maxChars: "22",
  nickSize: "20", msgSize: "18", nickBold: "", msgColor: "#ffffff", outline: "2",
  box: "", boxColor: "#000000", boxOpacity: "45", boxPadding: "6",
  icon: "", iconFollowNick: "1", iconColor: "#ff4d6d", iconScale: "100",
});

const chat = (label, fields) => Object.freeze({ label, fields: Object.freeze({ ...BASE, ...fields }) });

export const CHAT_TEMPLATES = Object.freeze({
  outline: chat("기본 (글자 테두리)", {}),
  box: chat("반투명 박스", { box: "1" }),
  boxIcon: chat("박스 + 닉 색 아이콘", { box: "1", boxColor: "#101018", boxOpacity: "60", boxPadding: "7", icon: "circle",
    iconScale: "70", nickBold: "1", lineH: "38" }),
  heart: chat("하트 + 굵은 닉", { outline: "3", icon: "heart", iconFollowNick: "", nickBold: "1" }),
  panda: chat("팬더티비 풍", { box: "1", boxColor: "#2b1030", boxOpacity: "50", icon: "heart", iconFollowNick: "",
    iconColor: "#ff5fa2", iconScale: "80", nickBold: "1", outline: "1" }),
  afreeca: chat("아프리카TV 풍", { outline: "3", nickBold: "1", nickSize: "19", msgSize: "19", lineH: "34", visible: "10" }),
  youtube: chat("유튜브 라이브 풍", { box: "1", boxColor: "#0f0f0f", boxOpacity: "55", boxPadding: "8", icon: "circle",
    iconScale: "110", nickSize: "17", lineH: "40", outline: "0" }),
});
