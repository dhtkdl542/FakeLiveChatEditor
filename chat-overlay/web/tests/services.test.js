import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { ApiClient, BridgeTransport, FetchTransport, pickTransport } from "../js/core/api.js";
import { FormMemory, PrefsStore } from "../js/core/prefs.js";
import { MODEL_CATALOG, OllamaViewModel } from "../js/core/ollama.js";

function fakeFetch(status, text) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url, init });
    return { ok: status < 400, status, text: async () => text };
  };
  fn.calls = calls;
  return fn;
}

describe("FetchTransport (브라우저 모드)", () => {
  test("JSON 으로 보내고 JSON 을 받는다", async () => {
    const f = fakeFetch(200, '{"ok":true,"path":"C:/a.mp4"}');
    const data = await new ApiClient(new FetchTransport(f)).pickVideo();
    assert.equal(data.path, "C:/a.mp4");
    assert.equal(f.calls[0].url, "/api/pick-video");
    assert.equal(f.calls[0].init.method, "POST");
    assert.equal(f.calls[0].init.headers["Content-Type"], "application/json");
  });

  test("서버 오류 메시지를 그대로 던진다", async () => {
    await assert.rejects(new ApiClient(new FetchTransport(fakeFetch(500, "ffmpeg 터짐"))).render({}), /ffmpeg 터짐/);
  });
});

describe("BridgeTransport (앱 창 모드)", () => {
  const fakeApi = result => {
    const calls = [];
    return { calls, call: async (path, payload) => { calls.push([path, payload]); return result; } };
  };

  test("Python 함수를 직접 부르고 ok 를 떼고 돌려준다", async () => {
    const api = fakeApi({ ok: true, models: ["m"] });
    const data = await new ApiClient(new BridgeTransport(() => api, Promise.resolve())).llmModels("x");
    assert.deepEqual(data, { models: ["m"] });
    assert.deepEqual(api.calls[0], ["/api/llm-models", { base: "x" }]);
  });

  test("실패 결과는 오류로 던진다", async () => {
    const t = new BridgeTransport(() => fakeApi({ ok: false, error: "망함", status: 500 }), Promise.resolve());
    await assert.rejects(t.post("/api/render", {}), /망함/);
  });

  test("브리지가 준비될 때까지 기다린다", async () => {
    let ready;
    const api = fakeApi({ ok: true });
    const t = new BridgeTransport(() => api, new Promise(r => { ready = r; }));
    const pending = t.post("/api/ollama/status", {});
    await new Promise(r => setTimeout(r, 10));
    assert.equal(api.calls.length, 0);
    ready();
    await pending;
    assert.equal(api.calls.length, 1);
  });
});

describe("pickTransport", () => {
  const fakeWindow = (search, pywebview) => {
    const listeners = {};
    return { location: { search }, pywebview, addEventListener: (n, fn) => { listeners[n] = fn; }, listeners };
  };

  test("?native=1 이면 브리지, 아니면 fetch", () => {
    assert.ok(pickTransport(fakeWindow("?native=1", { api: {} }), fakeFetch(200, "{}")) instanceof BridgeTransport);
    assert.ok(pickTransport(fakeWindow("", undefined), fakeFetch(200, "{}")) instanceof FetchTransport);
  });

  test("브리지가 아직 없으면 pywebviewready 이벤트를 기다린다", async () => {
    const win = fakeWindow("?native=1", undefined);
    const t = pickTransport(win, fakeFetch(200, "{}"));
    const pending = t.post("/api/ollama/status", {});
    win.pywebview = { api: { call: async () => ({ ok: true, running: true }) } };
    win.listeners.pywebviewready();
    assert.deepEqual(await pending, { running: true });
  });
});

describe("ApiClient", () => {
  test("기능별 경로", async () => {
    const f = fakeFetch(200, "{}");
    const api = new ApiClient(new FetchTransport(f));
    await api.pickSave("a.mp4");
    await api.llmModels("http://x");
    await api.generate({ prompt: "p" });
    await api.ollama("pull", { model: "m" });
    await api.pickImage();
    await api.registerImage("C:/s.png");
    assert.deepEqual(f.calls.map(c => c.url), ["/api/pick-save", "/api/llm-models", "/api/generate", "/api/ollama/pull",
      "/api/pick-image", "/api/register-image"]);
    assert.deepEqual(JSON.parse(f.calls[5].init.body), { path: "C:/s.png" });
    assert.deepEqual(JSON.parse(f.calls[0].init.body), { suggest: "a.mp4" });
    assert.deepEqual(JSON.parse(f.calls[3].init.body), { model: "m" });
  });
});

describe("PrefsStore", () => {
  test("저장하고 불러온다", () => {
    const mem = new Map();
    const storage = { getItem: k => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, v) };
    const store = new PrefsStore(storage, "k");
    store.save({ a: 1 });
    assert.deepEqual(store.load(), { a: 1 });
  });

  test("저장소가 막혀 있어도 터지지 않는다", () => {
    const broken = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };
    const store = new PrefsStore(broken, "k");
    assert.deepEqual(store.load(), {});
    store.save({ a: 1 });
    assert.deepEqual(new PrefsStore(null, "k").load(), {});
  });

  test("깨진 JSON 은 빈 값", () => {
    assert.deepEqual(new PrefsStore({ getItem: () => "{oops", setItem() {} }, "k").load(), {});
  });
});

describe("FormMemory", () => {
  const memStore = () => {
    const mem = new Map();
    return new PrefsStore({ getItem: k => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, v) }, "k");
  };

  test("고른 칸만 기억하고, 다른 저장값(스티커 등)은 건드리지 않는다", () => {
    const prefs = memStore();
    prefs.save({ stickers: [1] });
    const memory = new FormMemory(prefs, "deco", ["platform", "donationUnit"]);
    memory.save({ platform: "youtube", donationUnit: "₩", nicks: "많은 닉" });
    assert.deepEqual(memory.restore(), { platform: "youtube", donationUnit: "₩" });
    assert.deepEqual(prefs.load().stickers, [1]);
  });

  test("기억한 게 없거나 이상한 값이면 빈 값", () => {
    const prefs = memStore();
    assert.deepEqual(new FormMemory(prefs, "deco", ["platform"]).restore(), {});
    prefs.save({ deco: { platform: 3, other: "x" } });
    assert.deepEqual(new FormMemory(prefs, "deco", ["platform"]).restore(), {});
    prefs.save({ deco: "깨짐" });
    assert.deepEqual(new FormMemory(prefs, "deco", ["platform"]).restore(), {});
  });
});

describe("OllamaViewModel", () => {
  const idleJob = { kind: "", status: "idle", message: "", completed: 0, total: 0 };

  test("설치 안 됨", () => {
    const vm = OllamaViewModel.from({ installed: false, running: false, version: null, models: [], job: idleJob });
    assert.equal(vm.statusKind, "warn");
    assert.match(vm.statusText, /설치돼 있지 않습니다/);
    assert.equal(vm.installLabel, "Ollama 설치");
    assert.equal(vm.showStart, false);
    assert.equal(vm.job.visible, false);
  });

  test("설치됐지만 꺼져 있음: 창 없이 자동으로 켜진다고 안내", () => {
    const vm = OllamaViewModel.from({ installed: true, running: false, version: null, models: [], job: idleJob });
    assert.equal(vm.installLabel, "Ollama 업데이트");
    assert.equal(vm.showStart, true);
    assert.equal(vm.statusKind, "");
    assert.match(vm.statusText, /자동으로/);
    assert.match(vm.statusText, /창 없이/);
  });

  test("실행 중: 추천 모델 설치 여부, 임베딩 모델은 사용 불가", () => {
    const name = MODEL_CATALOG[0].name;
    const vm = OllamaViewModel.from({ installed: true, running: true, version: "0.17.1",
      models: [{ name, size: 1 }, { name: "nomic-embed-text:latest", size: 2 }], job: idleJob });
    assert.equal(vm.statusKind, "ok");
    assert.match(vm.statusText, /v0\.17\.1/);
    assert.equal(vm.catalog[0].installed, true);
    assert.equal(vm.catalog[1].installed, false);
    assert.deepEqual(vm.installed.map(m => m.usable), [true, false]);
    assert.deepEqual(vm.usableModels, [name]);
  });

  test("작업 진행률", () => {
    const job = { kind: "pull", status: "running", message: "받는 중", completed: 50, total: 200 };
    const vm = OllamaViewModel.from({ installed: true, running: true, version: "1", models: [], job });
    assert.deepEqual([vm.job.visible, vm.job.percent, vm.job.cancellable, vm.busy], [true, 25, true, true]);
    assert.match(vm.job.text, /50MB|200MB|받는 중/);
  });

  test("켜기 작업은 취소 불가, 끝난 작업은 100%", () => {
    const start = OllamaViewModel.from({ installed: true, running: false, version: null, models: [],
      job: { kind: "start", status: "running", message: "", completed: 0, total: 0 } });
    assert.equal(start.job.cancellable, false);
    const done = OllamaViewModel.from({ installed: true, running: true, version: "1", models: [],
      job: { kind: "pull", status: "done", message: "완료", completed: 0, total: 0 } });
    assert.equal(done.job.percent, 100);
    assert.equal(done.job.kind, "ok");
  });

  test("카탈로그 항목은 이름·크기·설명·태그를 가진다", () => {
    for (const m of MODEL_CATALOG) {
      assert.ok(m.name && m.size && m.title && m.note);
      assert.equal(typeof m.uncensored, "boolean");
    }
  });
});
