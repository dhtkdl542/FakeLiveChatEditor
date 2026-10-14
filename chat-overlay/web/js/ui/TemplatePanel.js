// 꾸미기 탭 '템플릿' 카드: 플랫폼 · 방송 템플릿 · 채팅창 템플릿을 따로 고른다.
import { PLATFORMS, platformFields } from "../core/platforms.js";
import { CHAT_TEMPLATES } from "../core/presets.js";
import { TEMPLATES } from "../core/templates.js";
import { $, h, setStatus } from "./dom.js";

const options = entries => entries.map(([key, t]) => h("option", { value: key }, t.label));

export class TemplatePanel {
  constructor({ form, list }) {
    Object.assign(this, { form, list });
    this.#platforms();
    this.#broadcast();
    this.#chat();
  }

  #platforms() {
    const select = $("#platformSelect");
    select.replaceChildren(...options(Object.entries(PLATFORMS)));
    // 고를 때만 단위 · 금액을 플랫폼 기본값으로 바꾼다. 그 뒤로 사용자가 고친 단위는 그대로 둔다.
    select.addEventListener("change", () => this.setPlatform(select.value));
    this.form.onChange(() => this.#platformNote());
    this.#platformNote();
  }

  setPlatform(key) {
    this.form.apply(platformFields(key));
  }

  #platformNote() {
    const p = PLATFORMS[this.form.get("platform")] || PLATFORMS.panda;
    setStatus($("#platformNote"), `기본 단위 '${p.unit}', 후원창은 ${p.label} 모양. 단위는 아래 가짜 후원 칸에서 바꿀 수 있습니다.`);
  }

  #broadcast() {
    const select = $("#templateSelect");
    select.replaceChildren(...options(Object.entries(TEMPLATES)));
    const note = () => setStatus($("#templateNote"), TEMPLATES[select.value]?.note || "");
    select.onchange = note;
    note();
    $("#btnApplyTemplate").onclick = () => this.applyTemplate(select.value);
  }

  /** 스티커를 통째로 바꾸고, 후원 빈도와 템플릿의 기본 플랫폼(단위 · 금액)을 넣는다 */
  applyTemplate(key) {
    const t = TEMPLATES[key];
    if (!t) return;
    this.list.replaceAll(t.stickers);
    const d = t.donation;
    this.form.apply({ donationsOn: d.on ? "1" : "", donationEvery: String(d.every), donationMsgChance: String(d.msgChance) });
    this.setPlatform(t.platform);
    setStatus($("#templateNote"), `${t.label} 템플릿을 넣었습니다 (플랫폼: ${PLATFORMS[t.platform].label}). ` +
      "미리보기에서 스티커를 끌어 옮겨 보세요.", "ok");
  }

  #chat() {
    const select = $("#chatTemplateSelect");
    select.replaceChildren(...options(Object.entries(CHAT_TEMPLATES)));
    $("#btnApplyChatTemplate").onclick = () => this.applyChat(select.value);
  }

  applyChat(key) {
    const t = CHAT_TEMPLATES[key];
    if (!t) return;
    this.form.apply(t.fields);
    setStatus($("#chatTemplateNote"), `채팅창을 '${t.label}' 모양으로 바꿨습니다. 스타일 탭의 '채팅 모양'에서 더 고칠 수 있습니다.`, "ok");
  }
}
