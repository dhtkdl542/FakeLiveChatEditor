// AI 탭: Ollama 설치 · 실행 · 모델 받기
import { OllamaViewModel } from "../core/ollama.js";
import { $, h, setStatus } from "./dom.js";

export class OllamaView {
  #poll = null;

  constructor(api, { onUse, confirm = msg => window.confirm(msg) }) {
    this.api = api;
    this.onUse = onUse;
    this.confirm = confirm;
    $("#btnOlInstall").onclick = () => {
      const what = $("#btnOlInstall").textContent.includes("업데이트") ? "최신 버전으로 업데이트" : "설치";
      if (this.confirm(`ollama.com에서 공식 Ollama 설치 파일을 받아 ${what}합니다.\n설치 창이 잠깐 뜰 수 있습니다. 진행할까요?`)) this.call("install");
    };
    $("#btnOlStart").onclick = () => this.call("start");
    $("#btnOlRefresh").onclick = () => this.call("status");
    $("#btnOlCancel").onclick = () => this.call("cancel");
    $("#btnOlPull").onclick = () => {
      const name = $("#olCustom").value.trim();
      if (name) this.pull(name, "");
    };
  }

  async call(action, payload) {
    try {
      this.render(OllamaViewModel.from(await this.api.ollama(action, payload)));
    } catch (e) {
      setStatus($("#olStatus"), "오류: " + e.message, "warn");
      this.#stopPolling();
    }
  }

  pull(name, size) {
    if (this.confirm(`${name}${size ? ` (${size})` : ""} 모델을 받을까요?\n크기가 커서 몇 분 걸릴 수 있습니다.`)) this.call("pull", { model: name });
  }

  remove(name) {
    if (this.confirm(`${name} 모델을 삭제할까요? 다시 쓰려면 새로 받아야 합니다.`)) this.call("delete", { model: name });
  }

  #stopPolling() {
    clearInterval(this.#poll);
    this.#poll = null;
  }

  render(vm) {
    setStatus($("#olStatus"), vm.statusText, vm.statusKind);
    $("#btnOlInstall").textContent = vm.installLabel;
    $("#btnOlStart").hidden = !vm.showStart;
    for (const id of ["#btnOlInstall", "#btnOlStart", "#btnOlPull"]) $(id).disabled = vm.busy;

    $("#olJob").hidden = !vm.job.visible;
    setStatus($("#olJobText"), vm.job.text, vm.job.kind);
    $("#olBar").style.width = vm.job.percent + "%";
    $("#btnOlCancel").hidden = !vm.job.cancellable;

    $("#olCatalog").replaceChildren(...vm.catalog.map(m => this.#item(
      [m.title, " · ", m.size, m.recommended && tag("rec", "추천"), m.uncensored && tag("unc", "검열 해제"), m.installed && tag("have", "설치됨")],
      `${m.note}\n${m.name}`,
      m.installed ? [["사용", () => this.onUse(m.name), false, true]] : [["받기", () => this.pull(m.name, m.size), vm.busy]])));

    $("#olInstalled").replaceChildren(...(vm.installed.length ? vm.installed.map(m => this.#item(
      [m.name],
      m.usable ? m.sizeText : `${m.sizeText} · 검색용 모델이라 대사 생성에는 못 씁니다`,
      [...(m.usable ? [["사용", () => this.onUse(m.name), false, true]] : []), ["삭제", () => this.remove(m.name), vm.busy]]))
      : [h("p", { className: "status" }, vm.running ? "아직 받은 모델이 없습니다." : "Ollama가 켜져 있어야 목록이 보입니다.")]));

    $("#modelList").replaceChildren(...vm.usableModels.map(n => h("option", { value: n })));

    if (vm.busy && !this.#poll) this.#poll = setInterval(() => this.call("status"), 1000);
    if (!vm.busy) this.#stopPolling();
  }

  #item(title, meta, buttons) {
    return h("div", { className: "model-item" },
      h("div", {}, h("div", { className: "title" }, ...title), h("div", { className: "meta" }, meta)),
      h("div", { className: "btns" }, ...buttons.map(([label, onclick, disabled, main]) =>
        h("button", { type: "button", className: main ? "btn primary small" : "btn ghost small", onclick, disabled }, label))));
  }
}

function tag(kind, text) {
  return h("span", { className: "tag " + kind }, text);
}
