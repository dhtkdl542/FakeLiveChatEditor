// 객체를 만들고 서로 연결한다. 기능은 core(계산·상태)와 ui(화면)에 있다.
import { ApiClient, pickTransport } from "./core/api.js";
import { linesOf, mergeLines } from "./core/lines.js";
import { Palette } from "./core/palette.js";
import { FormMemory, PrefsStore } from "./core/prefs.js";
import { Mulberry32 } from "./core/rng.js";
import { SectionList } from "./core/sections.js";
import { Settings } from "./core/settings.js";
import { VideoSource } from "./core/video.js";
import { wrapText } from "./core/text.js";
import { ICON_LABELS, ICON_NAMES } from "./core/icons.js";
import { CHAT_TEMPLATES } from "./core/presets.js";
import { StickerList } from "./core/stickerList.js";
import { $, h } from "./ui/dom.js";
import { FontMetrics } from "./ui/FontMetrics.js";
import { ExportController } from "./ui/ExportController.js";
import { FontsView } from "./ui/FontsView.js";
import { FormView } from "./ui/FormView.js";
import { LlmView } from "./ui/LlmView.js";
import { OllamaView } from "./ui/OllamaView.js";
import { PaletteView } from "./ui/PaletteView.js";
import { PreviewController } from "./ui/PreviewController.js";
import { SectionsView } from "./ui/SectionsView.js";
import { StickerLayer } from "./ui/StickerLayer.js";
import { StickerPanel } from "./ui/StickerPanel.js";
import { TemplatePanel } from "./ui/TemplatePanel.js";
import { StageView } from "./ui/StageView.js";
import { TabsView } from "./ui/TabsView.js";
import { TimelineView } from "./ui/TimelineView.js";

let storage = null;
try { storage = window.localStorage; } catch { /* 막힌 환경에서도 동작 */ }
const prefs = new PrefsStore(storage, "chatOverlay");
const api = new ApiClient(pickTransport(window));

const form = new FormView($("#form"));
const source = new VideoSource();
const sections = new SectionList(source.length);
const palette = new Palette(["#47b3ff", "#ffff00", "#ffffff", "#ff80ff", "#a0ffa0", "#ffb347"], new Mulberry32(Mulberry32.randomSeed()));

let preview;
const metrics = new FontMetrics();
const fonts = new FontsView(() => { metrics.forget(); preview?.invalidate(); });
document.fonts.addEventListener("loadingdone", () => { metrics.forget(); preview?.invalidate(); });
const getSettings = () => Settings.fromForm(form.values(), {
  colors: palette.colors, phases: preview.phases, sections: sections.toSettings(), loadedFonts: fonts.loaded,
});

const video = $("#video");
const stickerList = new StickerList();
const stickerLayer = new StickerLayer({ stage: $("#stage"), below: $("#stickers"), above: $("#alerts"), hit: $("#stickerHit"),
  list: stickerList, metrics, onChange: () => preview.invalidate() });
preview = new PreviewController({
  source, sections, video, getSettings, stickers: stickerLayer,
  stage: new StageView({ box: $("#stageBox"), stage: $("#stage"), video, overlay: $("#overlay"), badge: $("#stageBadge"), metrics }),
  timeline: new TimelineView($("#timeline"), {
    onSeek: t => preview.seek(t),
    onCreateSection: (a, b) => sections.add(a, b, 2),
    onChange: () => preview.invalidate(),
  }),
  ui: { playButton: $("#btnPlay"), timeText: $("#timeText"), speedText: $("#speedText") },
});

new SectionsView($("#sections"), sections, { onPlayFrom: t => preview.playFrom(t) });
new PaletteView(palette, () => linesOf(form.get("nicks")).length);
palette.subscribe(() => preview.invalidate());
new ExportController({ api, source, video, preview, getSettings, stickers: stickerList });

// 꾸미기: 플랫폼 · 후원 설정과 스티커 목록은 브라우저에 저장하고, 그림 스티커는 다시 열 때 서버에 다시 등록한다
const decoMemory = new FormMemory(prefs, "deco",
  ["platform", "donationsOn", "donationEvery", "donationUnit", "donationAmounts", "donationMsgChance"]);
new TemplatePanel({ form, list: stickerList });  // 플랫폼 보기를 먼저 만들어야 기억한 플랫폼을 고를 수 있다
form.apply(decoMemory.restore());
new StickerPanel({ list: stickerList, api, onChange: () => preview.invalidate() });
stickerList.load(prefs.load().stickers || []);
for (const s of stickerList.items.filter(i => i.type === "image" && i.path)) {
  api.registerImage(s.path).then(({ url }) => stickerList.update(s.id, { url }))
    .catch(() => stickerList.update(s.id, { url: "" }));
}
stickerList.subscribe(() => {
  prefs.save({ ...prefs.load(), stickers: stickerList.toJSON() });
  preview.invalidate();
});

const tabs = new TabsView($("#tabs"), $("#form"), name => {
  prefs.save({ ...prefs.load(), tab: name });
  if (name === "lines") $("#linesDot").classList.remove("on");
});
tabs.select(prefs.load().tab || "style");

const llm = new LlmView(api, prefs, {
  onLines: (msgs, nicks, mode) => {
    form.set("msgs", mergeLines(linesOf(form.get("msgs")), msgs, mode).join("\n"));
    if (nicks) form.set("nicks", mergeLines(linesOf(form.get("nicks")), nicks, mode).join("\n"));
    if (tabs.current !== "lines") $("#linesDot").classList.add("on");
  },
});
const ollama = new OllamaView(api, { onUse: name => llm.useModel(name) });
ollama.call("status");

// 채팅 모양: 아이콘 목록과 프리셋 버튼
$("#iconSelect").append(...ICON_NAMES.map(n => h("option", { value: n }, ICON_LABELS[n])));
$("#presets").replaceChildren(...Object.values(CHAT_TEMPLATES).map(p =>
  h("button", { type: "button", className: "btn ghost", onclick: () => form.apply(p.fields) }, p.label)));

function refreshFormExtras() {
  form.refreshLabels();
  decoMemory.save(form.values());
  const s = getSettings();
  const longest = s.MSGS.reduce((a, b) => (a.length >= b.length ? a : b), "");
  $("#wrapDemo").textContent = `한 줄 ${s.MAX_CHARS_PER_LINE}자:\n` +
    wrapText(longest, s.MAX_CHARS_PER_LINE).map((t, i) => `${i + 1}줄: ${t}`).join("\n");
  preview.invalidate();
}
form.onChange(refreshFormExtras);
refreshFormExtras();

$("#btnPlay").onclick = () => preview.toggle();
$("#stage").onclick = () => preview.toggle();
$("#btnReshuffle").onclick = () => preview.reshuffle();
$("#btnReroll").onclick = () => preview.rerollPattern();
$("#btnAddSection").onclick = () => preview.addSectionAtNow();
window.addEventListener("resize", () => preview.invalidate());
document.addEventListener("keydown", e => {
  if (e.code !== "Space" || /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(e.target.tagName)) return;
  e.preventDefault();
  preview.toggle();
});

preview.start();
window.__chatApp = { preview, stickers: stickerList, layer: stickerLayer };  // 화면 테스트용 연결점
document.body.dataset.ready = "1";
