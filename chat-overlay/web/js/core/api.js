// Python 쪽 기능 호출. 앱 창에서는 pywebview 브리지로, 브라우저(개발용)에서는 HTTP 로 부른다.

/** 브라우저 모드: 로컬 서버에 POST */
export class FetchTransport {
  #fetch;

  constructor(fetchFn = (...a) => globalThis.fetch(...a)) {
    this.#fetch = fetchFn;
  }

  async post(path, body = {}) {
    const res = await this.#fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
    const { ok, ...data } = text ? JSON.parse(text) : {};
    return data;
  }
}

/** 앱 창 모드: window.pywebview.api.call(path, payload) 로 Python 을 직접 부른다 */
export class BridgeTransport {
  #getApi; #ready;

  constructor(getApi, ready) {
    this.#getApi = getApi;
    this.#ready = ready;
  }

  async post(path, body = {}) {
    await this.#ready;
    const { ok, error, status, ...data } = await this.#getApi().call(path, body);
    if (!ok) throw new Error(error || `오류 ${status}`);
    return data;
  }
}

/** 앱 창은 주소에 ?native=1 을 붙여 연다 */
export function pickTransport(win, fetchFn) {
  if (new URLSearchParams(win.location.search).get("native") !== "1") return new FetchTransport(fetchFn);
  const ready = win.pywebview?.api
    ? Promise.resolve()
    : new Promise(resolve => win.addEventListener("pywebviewready", resolve));
  return new BridgeTransport(() => win.pywebview.api, ready);
}

export class ApiClient {
  #transport;

  constructor(transport) {
    this.#transport = transport;
  }

  post(path, body = {}) { return this.#transport.post(path, body); }
  pickVideo() { return this.post("/api/pick-video"); }
  pickSave(suggest) { return this.post("/api/pick-save", { suggest }); }
  render(payload) { return this.post("/api/render", payload); }
  llmModels(base) { return this.post("/api/llm-models", { base }); }
  generate(payload) { return this.post("/api/generate", payload); }
  ollama(action, payload = {}) { return this.post(`/api/ollama/${action}`, payload); }
  pickImage() { return this.post("/api/pick-image"); }
  registerImage(path) { return this.post("/api/register-image", { path }); }
}
