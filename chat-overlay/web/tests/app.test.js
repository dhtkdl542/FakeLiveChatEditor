import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { Mulberry32 } from "../js/core/rng.js";
import { Palette } from "../js/core/palette.js";
import { VideoSource } from "../js/core/video.js";
import { buildRenderRequest, suggestOutputName } from "../js/core/export.js";

describe("Palette", () => {
  const make = colors => new Palette(colors, new Mulberry32(1));

  test("색 추가·수정·삭제, 마지막 하나는 못 지운다", () => {
    const p = make(["#ff0000"]);
    p.add("#00ff00");
    p.set(0, "FFF");
    assert.deepEqual(p.colors, ["#ffffff", "#00ff00"]);
    p.remove(0);
    p.remove(0);
    assert.deepEqual(p.colors, ["#00ff00"]);
  });

  test("잘못된 색은 무시", () => {
    const p = make(["#ff0000"]);
    p.set(0, "banana");
    assert.deepEqual(p.colors, ["#ff0000"]);
  });

  test("랜덤 색 추가와 개수 맞추기", () => {
    const p = make(["#ff0000"]);
    p.add();
    assert.match(p.colors[1], /^#[0-9a-f]{6}$/);
    p.fitTo(4);
    assert.equal(p.colors.length, 4);
    p.fitTo(2);
    assert.equal(p.colors.length, 2);
    p.fitTo(0);
    assert.equal(p.colors.length, 1);
  });

  test("전부 랜덤은 개수를 유지하고 알린다", () => {
    const p = make(["#000000", "#000000"]);
    let n = 0;
    p.subscribe(() => n++);
    p.randomizeAll();
    assert.equal(p.colors.length, 2);
    assert.notDeepEqual(p.colors, ["#000000", "#000000"]);
    assert.equal(n, 1);
  });
});

describe("VideoSource", () => {
  test("영상 없을 때는 1920×1080 60초 샘플", () => {
    const v = new VideoSource();
    assert.equal(v.hasVideo, false);
    assert.equal(v.length, 60);
    assert.deepEqual(v.resolution, { width: 1920, height: 1080 });
  });

  test("서버가 읽은 정보로 먼저 채우고, 브라우저가 읽으면 재생 가능", () => {
    const v = new VideoSource();
    let n = 0;
    v.subscribe(() => n++);
    v.load({ path: "C:/v/clip.mp4", url: "/video/t.mp4", width: 1280, height: 720, duration: 12 });
    assert.deepEqual([v.hasVideo, v.playable, v.length, v.name], [true, false, 12, "clip.mp4"]);
    v.onMetadata({ videoWidth: 1080, videoHeight: 1920, duration: 12.5 });
    assert.deepEqual([v.playable, v.resolution.width, v.length], [true, 1080, 12.5]);
    assert.equal(n, 2);
  });

  test("브라우저가 못 읽는 코덱: 서버 정보가 있으면 검은 화면 미리보기", () => {
    const v = new VideoSource();
    v.load({ path: "a.mkv", url: "/video/x.mkv", width: 100, height: 100, duration: 5 });
    v.onError();
    assert.deepEqual([v.hasVideo, v.playable, v.error], [true, false, "codec"]);
  });

  test("정보도 못 읽고 재생도 안 되면 샘플로 돌아간다", () => {
    const v = new VideoSource();
    v.load({ path: "a.xyz", url: "/video/x.xyz" });
    v.onError();
    assert.deepEqual([v.hasVideo, v.error, v.length], [false, "unreadable", 60]);
  });

  test("무한 길이(스트림)는 무시", () => {
    const v = new VideoSource();
    v.load({ path: "a.webm", url: "/v", width: 10, height: 10, duration: 3 });
    v.onMetadata({ videoWidth: 10, videoHeight: 10, duration: Infinity });
    assert.equal(v.length, 3);
  });
});

describe("export", () => {
  test("저장 이름 제안", () => {
    assert.equal(suggestOutputName("C:\\a\\clip.final.mov"), "clip.final_chat.mp4");
    assert.equal(suggestOutputName("/x/y/z"), "z_chat.mp4");
  });

  test("미리보기 타임라인을 같이 보내서 결과가 똑같이 나오게", () => {
    const req = buildRenderRequest({ videoPath: "C:/v.mp4", outputPath: "C:/o.mp4", settings: { NICKS: ["a"] },
      events: [{ t: 1, nick: "a", msg: "m", color: "#fff" }], previewMatchesVideo: true });
    assert.deepEqual(req, { videoPath: "C:/v.mp4", outputPath: "C:/o.mp4",
      settings: { NICKS: ["a"], STICKERS: [], EVENTS: [{ t: 1, nick: "a", msg: "m", color: "#fff" }], DONATIONS: [],
        TEXT_WIDTHS: {} } });
  });

  test("미리보기가 영상 길이를 모르면 서버가 새로 만든다", () => {
    const req = buildRenderRequest({ videoPath: "v", outputPath: "o", settings: {}, events: [{}], previewMatchesVideo: false });
    assert.equal("EVENTS" in req.settings, false);
  });
});
