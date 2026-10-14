// AI 탭: sLLM 으로 대사 만들기
import { OLLAMA_BASE } from "../core/ollama.js";
import { $, h, setStatus } from "./dom.js";

const FIELDS = ["llmBase", "llmModel", "llmPrompt", "llmCount", "llmNickCount", "llmTemp"];

export class LlmView {
  constructor(api, prefs, { onLines }) {
    this.api = api;
    this.prefs = prefs;
    this.onLines = onLines;
    this.status = $("#llmStatus");
    this.#restore();
    $("#llmPreset").onchange = () => {
      if ($("#llmPreset").value) $("#llmBase").value = $("#llmPreset").value;
      this.#save();
    };
    $("#llmBase").addEventListener("input", () => this.#syncPreset());
    const card = $("#llmPrompt").closest(".card");
    card.addEventListener("input", () => { this.#save(); this.#labels(); });
    card.addEventListener("change", () => this.#save());
    $("#btnModels").onclick = () => this.loadModels();
    $("#btnGenerate").onclick = () => this.generate();
    this.#labels();
  }

  #restore() {
    const p = this.prefs.load().llm || {};
    for (const id of FIELDS) if (p[id] != null) $("#" + id).value = p[id];
    if (p.llmNicks != null) $("#llmNicks").checked = p.llmNicks;
    this.#syncPreset();
  }

  #save() {
    const llm = Object.fromEntries(FIELDS.map(id => [id, $("#" + id).value]));
    llm.llmNicks = $("#llmNicks").checked;
    this.prefs.save({ ...this.prefs.load(), llm });
  }

  #syncPreset() {
    const v = $("#llmBase").value.trim();
    const known = [...$("#llmPreset").options].some(o => o.value && o.value === v);
    $("#llmPreset").value = known ? v : "";
  }

  #labels() {
    $("#llmTempVal").textContent = Number($("#llmTemp").value).toFixed(1);
  }

  useModel(name) {
    $("#llmPreset").value = OLLAMA_BASE;
    $("#llmBase").value = OLLAMA_BASE;
    $("#llmModel").value = name;
    this.#save();
    setStatus(this.status, `${name} 모델을 골랐습니다. 주제를 적고 [대사 생성]을 누르세요.`, "ok");
    $("#llmPrompt").focus();
  }

  async loadModels() {
    try {
      const { models } = await this.api.llmModels($("#llmBase").value);
      $("#modelList").replaceChildren(...models.map(n => h("option", { value: n })));
      if (!$("#llmModel").value && models.length) $("#llmModel").value = models[0];
      if (models.length) setStatus(this.status, `모델 ${models.length}개: ${models.join(", ")}`, "ok");
      else setStatus(this.status, "설치된 모델이 없습니다. 위에서 모델을 받으세요.", "warn");
      this.#save();
    } catch (e) {
      setStatus(this.status, "모델 목록을 못 불러왔습니다: " + e.message, "warn");
    }
  }

  async generate() {
    const prompt = $("#llmPrompt").value.trim();
    const model = $("#llmModel").value.trim();
    if (!prompt) return setStatus(this.status, "주제나 분위기를 적으세요.", "warn");
    if (!model) return setStatus(this.status, "모델을 고르세요. 위에서 받은 모델의 [사용]을 누르면 됩니다.", "warn");
    const btn = $("#btnGenerate");
    btn.disabled = true;
    const t0 = Date.now();
    const tick = () => setStatus(this.status,
      `생성 중... ${Math.floor((Date.now() - t0) / 1000)}초 (처음 한 번은 모델을 불러오느라 더 걸립니다)`, "warn");
    tick();
    const timer = setInterval(tick, 500);
    try {
      const d = await this.api.generate({
        base: $("#llmBase").value, model, prompt,
        count: Number($("#llmCount").value),
        temperature: Number($("#llmTemp").value),
        nickCount: $("#llmNicks").checked ? Number($("#llmNickCount").value) : 0,
      });
      const mode = document.querySelector('input[name="llmMode"]:checked').value;
      this.onLines(d.msgs, d.nicks || null, mode);
      setStatus(this.status, `대사 ${d.msgs.length}개${d.nicks ? `, 닉네임 ${d.nicks.length}개` : ""}를 대사 탭에 넣었습니다. 마음에 안 드는 줄은 직접 고치세요.`, "ok");
    } catch (e) {
      setStatus(this.status, "실패: " + e.message, "warn");
    } finally {
      clearInterval(timer);
      btn.disabled = false;
    }
  }
}
