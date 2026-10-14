import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { Observable } from "../js/core/observable.js";
import { SectionList } from "../js/core/sections.js";
import { SimulatedClock, VideoClock } from "../js/core/clock.js";
import { Settings } from "../js/core/settings.js";
import { CHAT_TEMPLATES } from "../js/core/presets.js";
import { TimelineScale, TimelineGesture } from "../js/core/timeline.js";
import { fmtTime, fmtBytes, fmtMul, speedLabel } from "../js/core/format.js";
import { linesOf, mergeLines } from "../js/core/lines.js";

describe("Observable", () => {
  test("구독자에게 알리고 구독 해제할 수 있다", () => {
    const o = new Observable();
    const seen = [];
    const off = o.subscribe(v => seen.push(v));
    o.emit(1);
    off();
    o.emit(2);
    assert.deepEqual(seen, [1]);
  });
});

describe("SectionList", () => {
  test("추가하면 시작 순으로 정렬되고 새 구간이 선택된다", () => {
    const list = new SectionList(60);
    list.add(10, 15, 2);
    list.add(2, 5, 0.5);
    assert.deepEqual(list.items.map(s => s.start), [2, 10]);
    assert.equal(list.selected, 0);
  });

  test("영상 길이 밖으로 못 나가고 최소 길이를 지킨다", () => {
    const list = new SectionList(20);
    list.add(-3, 30, 2);
    assert.deepEqual([list.items[0].start, list.items[0].end], [0, 20]);
    list.update(0, { start: 19.95 });
    assert.ok(list.items[0].end - list.items[0].start >= SectionList.MIN_LENGTH - 1e-9);
    assert.ok(list.items[0].end <= 20);
  });

  test("속도 범위를 지킨다", () => {
    const list = new SectionList(20);
    list.add(1, 2, 99);
    assert.equal(list.items[0].speed, SectionList.MAX_SPEED);
    list.update(0, { speed: 0.001 });
    assert.equal(list.items[0].speed, 1 / SectionList.MAX_SPEED);
  });

  test("슬라이더 값과 속도 변환은 서로 되돌릴 수 있다", () => {
    assert.equal(SectionList.sliderToSpeed(0), 1);
    assert.equal(SectionList.sliderToSpeed(100), SectionList.MAX_SPEED);
    assert.equal(SectionList.speedToSlider(SectionList.sliderToSpeed(37)), 37);
  });

  test("삭제·선택·위치로 찾기", () => {
    const list = new SectionList(60);
    list.add(1, 3, 2);
    list.add(5, 8, 2);
    assert.equal(list.indexAt(6), 1);
    assert.equal(list.indexAt(4), -1);
    list.remove(0);
    assert.equal(list.items.length, 1);
    assert.equal(list.selected, -1);
  });

  test("영상 길이가 줄면 넘치는 구간은 자르거나 버린다", () => {
    const list = new SectionList(60);
    list.add(1, 3, 2);
    list.add(10, 40, 2);
    list.add(50, 55, 2);
    list.setLength(20);
    assert.deepEqual(list.items.map(s => [s.start, s.end]), [[1, 3], [10, 20]]);
  });

  test("알리지 않고 값만 바꿀 수 있다 (슬라이더를 끄는 동안)", () => {
    const list = new SectionList(60);
    list.add(1, 3, 2);
    let count = 0;
    list.subscribe(() => count++);
    list.update(0, { speed: 4 }, { notify: false });
    assert.equal(count, 0);
    assert.equal(list.toSettings()[0].speed, 4);
  });

  test("바뀔 때마다 알리고 설정용 배열을 준다", () => {
    const list = new SectionList(60);
    let count = 0;
    list.subscribe(() => count++);
    list.add(1, 3, 2);
    list.update(0, { speed: 3 });
    assert.equal(count, 2);
    assert.deepEqual(list.toSettings(), [{ start: 1, end: 3, speed: 3 }]);
  });
});

describe("SimulatedClock", () => {
  test("재생하면 시간이 흐르고 끝에서 반복하거나 멈춘다", () => {
    const loop = new SimulatedClock(10, true);
    loop.play();
    loop.tick(12);
    assert.equal(loop.now, 2);
    const once = new SimulatedClock(10, false);
    once.play();
    once.tick(12);
    assert.equal(once.now, 10);
    assert.equal(once.playing, false);
  });

  test("멈춘 상태에서는 흐르지 않고, 끝에서 재생하면 처음부터", () => {
    const c = new SimulatedClock(10, false);
    c.tick(5);
    assert.equal(c.now, 0);
    c.seek(10);
    c.play();
    assert.equal(c.now, 0);
  });

  test("seek 은 범위 안으로", () => {
    const c = new SimulatedClock(10, true);
    c.seek(-5);
    assert.equal(c.now, 0);
    c.seek(50);
    assert.equal(c.now, 10);
  });
});

describe("VideoClock", () => {
  const fakeVideo = () => ({ currentTime: 0, paused: true, ended: false, duration: 30,
    play() { this.paused = false; return Promise.resolve(); }, pause() { this.paused = true; } });

  test("영상 요소의 시간과 재생 상태를 따른다", () => {
    const v = fakeVideo();
    const c = new VideoClock(v);
    c.play();
    assert.equal(c.playing, true);
    v.currentTime = 3.5;
    assert.equal(c.now, 3.5);
    c.pause();
    assert.equal(c.playing, false);
  });

  test("끝난 영상을 재생하면 처음부터, seek 은 범위 안으로", () => {
    const v = fakeVideo();
    v.ended = true;
    v.currentTime = 30;
    const c = new VideoClock(v);
    c.play();
    assert.equal(v.currentTime, 0);
    c.seek(99);
    assert.equal(v.currentTime, 30);
  });
});

describe("Settings.fromForm", () => {
  const extra = { colors: ["#fff"], phases: [1, 2, 3], sections: [] };
  const raw = {
    align: "right", sideMargin: "24", bottomMargin: "24", lineH: "36", visible: "6", maxChars: "2",
    chatStart: "0.5", intMin: "0.3", intMax: "0.9", fadeIn: "180", fadeOut: "450", fadeUp: "18",
    speedVar: "50", speedPeriod: "8", nickFont: " Malgun Gothic ", nickSize: "20", msgFont: "", msgSize: "18",
    nickBold: "", msgColor: "#ffffff", outline: "2", box: "", boxColor: "#000000", boxOpacity: "45",
    boxPadding: "6", icon: "", iconFollowNick: "1", iconColor: "#ff0000", iconScale: "100",
    nicks: "a\n\n b \n", msgs: "x\ny",
  };

  test("숫자와 목록으로 정리한다", () => {
    const s = Settings.fromForm(raw, extra);
    assert.equal(s.ALIGN, "right");
    assert.equal(s.SIDE_MARGIN, 24);
    assert.equal(s.SPEED_VAR, 0.5);
    assert.deepEqual(s.NICKS, ["a", "b"]);
    assert.deepEqual(s.MSGS, ["x", "y"]);
    assert.equal(s.NICK_FONT, "Malgun Gothic");
    assert.equal(s.MSG_FONT, "Malgun Gothic");
    assert.deepEqual(s.COLORS, ["#fff"]);
    assert.deepEqual(s.SPEED_PHASES, [1, 2, 3]);
    assert.equal("CHAT_X_RATIO" in s, false);
  });

  test("채팅 모양 옵션", () => {
    const s = Settings.fromForm({ ...raw, box: "1", boxColor: "#102030", boxOpacity: "60", boxPadding: "8",
      icon: "heart", iconFollowNick: "", iconColor: "#00FF00", iconScale: "150", nickBold: "1", msgColor: "ff0" }, extra);
    assert.deepEqual([s.BOX, s.BOX_COLOR, s.BOX_OPACITY, s.BOX_PADDING], [true, "#102030", 0.6, 8]);
    assert.deepEqual([s.ICON, s.ICON_COLOR, s.ICON_SCALE], ["heart", "#00ff00", 1.5]);
    assert.deepEqual([s.NICK_BOLD, s.MSG_COLOR], [true, "#ffff00"]);
  });

  test("아이콘 색을 닉 색에 맞추면 비워 둔다", () => {
    assert.equal(Settings.fromForm({ ...raw, icon: "star" }, extra).ICON_COLOR, "");
  });

  test("이상한 값은 기본값이나 허용 범위로", () => {
    const s = Settings.fromForm({ ...raw, visible: "0", lineH: "abc", align: "middle", icon: "banana",
      boxOpacity: "300", msgColor: "nope" }, extra);
    assert.equal(s.MAX_CHARS_PER_LINE, 4);
    assert.equal(s.VISIBLE, 1);
    assert.equal(s.LINE_H, Settings.DEFAULTS.lineH);
    assert.equal(s.ALIGN, "right");
    assert.equal(s.ICON, "");
    assert.equal(s.BOX_OPACITY, 1);
    assert.equal(s.MSG_COLOR, "#ffffff");
  });

  test("기본값은 오른쪽 아래 구석에 살짝 띄운 자리", () => {
    assert.deepEqual([Settings.DEFAULTS.sideMargin, Settings.DEFAULTS.bottomMargin], [24, 24]);
  });

  test("ttf 를 올렸으면 그 글꼴 이름을 쓴다", () => {
    const s = Settings.fromForm(raw, { ...extra, loadedFonts: { nick: "ChatFont_nick" } });
    assert.equal(s.NICK_FONT, "ChatFont_nick");
  });
});

describe("CHAT_TEMPLATES", () => {
  const extra = { colors: [], phases: [0, 0, 0], sections: [] };

  test("프리셋은 아는 입력칸만 바꾼다", () => {
    for (const [name, preset] of Object.entries(CHAT_TEMPLATES)) {
      assert.ok(preset.label, name);
      for (const key of Object.keys(preset.fields)) assert.ok(Settings.FIELDS.includes(key), `${name}: ${key}`);
    }
  });

  test("반투명 박스 프리셋을 고르면 박스가 켜진다", () => {
    const s = Settings.fromForm(CHAT_TEMPLATES.box.fields, extra);
    assert.equal(s.BOX, true);
    assert.equal(Settings.fromForm(CHAT_TEMPLATES.outline.fields, extra).BOX, false);
  });

  test("아이콘 프리셋은 아이콘이 있다", () => {
    assert.notEqual(Settings.fromForm(CHAT_TEMPLATES.boxIcon.fields, extra).ICON, "");
  });
});

describe("TimelineScale / TimelineGesture", () => {
  const scale = new TimelineScale(60, 600);

  test("시간 ↔ 픽셀", () => {
    assert.equal(scale.xOf(30), 300);
    assert.equal(scale.tAt(150), 15);
    assert.equal(scale.tAt(-10), 0);
    assert.equal(scale.tAt(9999), 60);
  });

  test("짧게 누르면 그 위치로 이동", () => {
    const g = new TimelineGesture(() => scale);
    g.down(100);
    g.move(102);
    assert.deepEqual(g.up(102), { type: "seek", t: 10.2 });
  });

  test("드래그하면 구간 만들기 (방향 상관없이)", () => {
    const g = new TimelineGesture(() => scale);
    g.down(300);
    g.move(200);
    assert.deepEqual(g.preview, { start: 20, end: 30 });
    assert.deepEqual(g.up(200), { type: "section", start: 20, end: 30 });
    assert.equal(g.preview, null);
  });

  test("너무 짧은 드래그는 이동으로 처리", () => {
    const g = new TimelineGesture(() => scale);
    g.down(100);
    g.move(102.5);
    g.move(105);
    assert.equal(g.up(102).type, "seek");
  });

  test("누르지 않고 놓으면 아무 일 없음", () => {
    assert.equal(new TimelineGesture(() => scale).up(5), null);
  });
});

describe("format", () => {
  test("시간, 용량, 배율 표시", () => {
    assert.equal(fmtTime(75.25), "1:15.3");
    assert.equal(fmtTime(-1), "0:00.0");
    assert.equal(fmtBytes(4_800_000_000), "4.80GB");
    assert.equal(fmtBytes(274_000_000), "274MB");
    assert.equal(fmtMul(2), "×2.0");
    assert.equal(fmtMul(0.25), "×0.25");
    assert.equal(speedLabel(2), "×2.0 빠르게");
    assert.equal(speedLabel(0.5), "×0.50 느리게");
    assert.equal(speedLabel(1), "×1.0 그대로");
  });
});

describe("lines", () => {
  test("빈 줄과 공백을 걷어낸다", () => {
    assert.deepEqual(linesOf(" a \r\n\nb"), ["a", "b"]);
  });

  test("바꾸기와 뒤에 추가 (중복 제외)", () => {
    assert.deepEqual(mergeLines(["a", "b"], ["c"], "replace"), ["c"]);
    assert.deepEqual(mergeLines(["a", "b"], ["b", "c"], "append"), ["a", "b", "c"]);
  });
});
