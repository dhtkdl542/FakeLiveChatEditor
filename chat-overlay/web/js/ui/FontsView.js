// 글꼴 목록과 ttf 올리기
import { $, setStatus } from "./dom.js";

const DEFAULT_FONTS = ["Malgun Gothic", "Malgun Gothic Bold", "Gulim", "Dotum", "Batang", "Microsoft YaHei",
  "Segoe UI", "Arial", "윤고딕320", "윤고딕330", "윤고딕340", "윤고딕350", "Noto Sans KR", "Pretendard", "NanumGothic"];

export class FontsView {
  /** loaded: ttf 를 올렸으면 그 글꼴 이름 (Settings.fromForm 의 loadedFonts) */
  loaded = { nick: null, msg: null };

  constructor(onChange) {
    this.onChange = onChange;
    this.status = $("#fontStatus");
    this.#fill(DEFAULT_FONTS);
    $("#btnFonts").onclick = () => this.#loadSystemFonts();
    $("#nickTtf").addEventListener("change", e => this.#loadTtf(e.target, "nick"));
    $("#msgTtf").addEventListener("change", e => this.#loadTtf(e.target, "msg"));
  }

  #fill(names) {
    const list = $("#fontList");
    list.replaceChildren(...[...new Set(names)].sort((a, b) => a.localeCompare(b, "ko"))
      .map(n => Object.assign(document.createElement("option"), { value: n })));
  }

  async #loadSystemFonts() {
    if (!window.queryLocalFonts) {
      setStatus(this.status, "목록은 Chrome/Edge에서만 됩니다. 이름을 직접 적거나 ttf를 올리세요.", "warn");
      return;
    }
    try {
      const fonts = await window.queryLocalFonts();
      this.#fill([...DEFAULT_FONTS, ...fonts.map(f => f.family)]);
      setStatus(this.status, "글꼴 목록을 불러왔습니다.", "ok");
    } catch {
      setStatus(this.status, "권한이 거부되었습니다. 이름을 직접 적거나 ttf를 올리세요.", "warn");
    }
  }

  async #loadTtf(input, key) {
    const file = input.files[0];
    if (!file) {
      this.loaded[key] = null;
      this.onChange();
      return;
    }
    try {
      const family = "ChatFont_" + key;
      const face = new FontFace(family, await file.arrayBuffer());
      await face.load();
      document.fonts.add(face);
      this.loaded[key] = family;
      setStatus(this.status, `${file.name} 글꼴을 불러왔습니다. 결과 영상에 쓰려면 ttf를 이 앱 폴더나 영상 폴더에도 두세요.`, "ok");
    } catch {
      setStatus(this.status, `${file.name} 을(를) 글꼴로 읽지 못했습니다.`, "warn");
    }
    this.onChange();
  }
}
