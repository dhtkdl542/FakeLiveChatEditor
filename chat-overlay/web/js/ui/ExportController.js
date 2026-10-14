// 영상 불러오기와 mp4 저장
import { buildRenderRequest, suggestOutputName } from "../core/export.js";
import { fmtTime } from "../core/format.js";
import { $, setStatus } from "./dom.js";

export class ExportController {
  constructor({ api, source, video, preview, getSettings, stickers }) {
    Object.assign(this, { api, source, video, preview, getSettings, stickers });
    this.status = $("#exportStatus");
    $("#btnPick").onclick = () => this.pick();
    $("#btnRender").onclick = () => this.render();
    video.addEventListener("loadedmetadata", () => source.onMetadata(video));
    video.addEventListener("error", () => { if (source.url) source.onError(); });
    source.subscribe(() => this.#showMeta());
  }

  #showMeta() {
    const s = this.source, meta = $("#videoMeta");
    if (!s.path) meta.textContent = "영상 없이 샘플 화면으로 보는 중";
    else if (s.hasVideo) meta.textContent = `${s.name} · ${s.width}×${s.height} · ${fmtTime(s.duration)}`;
    else meta.textContent = `${s.name} · 영상 정보를 읽는 중...`;
    if (s.error === "codec") setStatus(this.status, "이 영상 형식(코덱)은 브라우저에서 재생할 수 없습니다. 검은 화면 위에서 채팅과 구간을 확인할 수 있고, mp4 저장은 정상적으로 됩니다.", "warn");
    if (s.error === "unreadable") setStatus(this.status, "영상을 읽지 못했습니다. ffmpeg가 설치돼 있는지 확인하세요.", "warn");
  }

  async pick() {
    try {
      const data = await this.api.pickVideo();
      if (!data.path) return setStatus(this.status, "선택을 취소했습니다.");
      setStatus(this.status, "");
      this.source.load(data);
      this.video.src = data.url;
      this.video.load();
    } catch (e) {
      setStatus(this.status, "탐색기를 열 수 없습니다. 시작.bat 으로 연 페이지에서 사용하세요. " + e.message, "warn");
    }
  }

  async render() {
    const settings = this.getSettings();
    if (!this.source.path) return setStatus(this.status, "먼저 [영상 불러오기]로 영상을 고르세요.", "warn");
    if (!settings.NICKS.length || !settings.MSGS.length) return setStatus(this.status, "대사 탭에서 닉네임과 대사를 적으세요.", "warn");
    const btn = $("#btnRender");
    btn.disabled = true;
    try {
      const save = await this.api.pickSave(suggestOutputName(this.source.path));
      if (!save.path) return setStatus(this.status, "저장을 취소했습니다.");
      setStatus(this.status, "FFmpeg 로 영상을 만드는 중... 영상 길이에 따라 몇 분 걸릴 수 있습니다.", "warn");
      const data = await this.api.render(buildRenderRequest({
        videoPath: this.source.path, outputPath: save.path, settings,
        events: this.preview.events(settings), previewMatchesVideo: this.source.hasVideo,
        stickers: this.stickers.toJSON(), donations: this.preview.donations(settings),
      }));
      setStatus(this.status, "저장 완료: " + data.output, "ok");
    } catch (e) {
      setStatus(this.status, "실패: " + e.message, "warn");
    } finally {
      btn.disabled = false;
    }
  }
}
