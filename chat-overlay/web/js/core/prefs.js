// 브라우저에 작은 설정(서버 주소, 모델, 펼친 카드 등)을 기억한다. 막혀 있어도 앱은 그대로 동작.
export class PrefsStore {
  constructor(storage, key) {
    this.storage = storage;
    this.key = key;
  }

  load() {
    try {
      const v = JSON.parse(this.storage.getItem(this.key) || "{}");
      return v && typeof v === "object" ? v : {};
    } catch {
      return {};
    }
  }

  save(value) {
    try {
      this.storage.setItem(this.key, JSON.stringify(value));
    } catch {
      /* 저장 못 해도 동작에는 지장 없음 */
    }
  }
}

/** 입력칸 몇 개(플랫폼 · 후원 설정)를 다음에 열 때도 그대로 쓰도록 기억한다. 값은 문자열만. */
export class FormMemory {
  constructor(prefs, key, fields) {
    Object.assign(this, { prefs, key, fields });
  }

  #pick(values) {
    const out = {};
    if (!values || typeof values !== "object") return out;
    for (const f of this.fields) if (typeof values[f] === "string") out[f] = values[f];
    return out;
  }

  restore() {
    return this.#pick(this.prefs.load()[this.key]);
  }

  save(values) {
    this.prefs.save({ ...this.prefs.load(), [this.key]: this.#pick(values) });
  }
}
