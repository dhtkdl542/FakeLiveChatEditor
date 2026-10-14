// 미리보기 진행: 시계 · 채팅/후원 타임라인 · 화면 · 스티커 · 타임라인 그리기를 매 프레임 묶어서 돌린다
import { SimulatedClock, VideoClock } from "../core/clock.js";
import { DonationCache, mergeIntoChat } from "../core/donations.js";
import { EventCache } from "../core/events.js";
import { ChatLayout, OverlayStyle } from "../core/layout.js";
import { Mulberry32 } from "../core/rng.js";
import { SpeedCurve } from "../core/speed.js";
import { fmtTime } from "../core/format.js";

const SAMPLE_START = 8;  // 샘플 화면은 채팅이 어느 정도 쌓인 시점부터 보여준다

export class PreviewController {
  phases = SpeedCurve.randomPhases();
  seed = Mulberry32.randomSeed();
  #cache = new EventCache();
  #donationCache = new DonationCache();
  #merged = { chat: null, donations: null, unit: null, value: [] };
  #dirty = true;
  #last = 0;

  constructor({ source, sections, video, stage, stickers, timeline, getSettings, ui }) {
    Object.assign(this, { source, sections, video, stage, stickers, timeline, getSettings, ui });
    this.clock = this.#makeClock();
    this.clock.seek(SAMPLE_START);
    source.subscribe(() => this.#onSourceChanged());
    sections.subscribe(() => this.invalidate());
    for (const ev of ["play", "pause", "seeked", "ended", "loadeddata"]) video.addEventListener(ev, () => this.invalidate());
  }

  #makeClock() {
    return this.source.playable ? new VideoClock(this.video) : new SimulatedClock(this.source.length, !this.source.hasVideo);
  }

  #onSourceChanged() {
    const wasPlaying = this.clock.playing;
    this.clock.pause();
    this.clock = this.#makeClock();
    if (!this.source.hasVideo) this.clock.seek(SAMPLE_START);
    this.sections.setLength(this.source.length);
    if (wasPlaying && !this.source.playable) this.clock.play();
    this.invalidate();
  }

  invalidate() { this.#dirty = true; }
  toggle() { this.clock.playing ? this.clock.pause() : this.clock.play(); this.invalidate(); }
  seek(t) { this.clock.seek(t); this.invalidate(); }
  playFrom(t) { this.clock.seek(t); this.clock.play(); this.invalidate(); }
  reshuffle() { this.seed = Mulberry32.randomSeed(); this.invalidate(); }
  rerollPattern() { this.phases = SpeedCurve.randomPhases(); this.invalidate(); }

  addSectionAtNow() {
    const len = this.source.length;
    let start = this.clock.now;
    if (start > len - 1) start = Math.max(0, len - 5);
    this.sections.add(start, Math.min(len, start + 5), 2);
  }

  /** 가짜 후원 목록 (설정이 그대로면 같은 목록) */
  donations(settings = this.getSettings()) {
    return this.#donationCache.get(settings, this.seed, this.source.length);
  }

  /** 채팅 타임라인 + 후원 강조 줄 (저장할 때도 이걸 보낸다) */
  events(settings = this.getSettings()) {
    const chat = this.#cache.get(settings, this.seed, this.source.length);
    const donations = this.donations(settings);
    const m = this.#merged;
    if (m.chat !== chat || m.donations !== donations || m.unit !== settings.DONATION_UNIT) {
      Object.assign(m, { chat, donations, unit: settings.DONATION_UNIT,
        value: donations.length ? mergeIntoChat(chat, donations, settings.COLORS, settings.DONATION_UNIT) : chat });
    }
    return m.value;
  }

  start() {
    const loop = ts => {
      this.clock.tick(this.#last ? Math.min(0.1, (ts - this.#last) / 1000) : 0);
      this.#last = ts;
      if (this.#dirty || this.clock.playing) {
        this.#dirty = false;
        this.draw();
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  draw() {
    const settings = this.getSettings();
    const events = this.events(settings);
    const donations = this.donations(settings);
    const now = this.clock.now;
    const length = this.source.length;
    const layout = new ChatLayout(OverlayStyle.fromSettings(settings));
    const curve = SpeedCurve.fromSettings(settings);
    this.stage.render({ source: this.source, layout, frame: layout.frameAt(events, now, length), now });
    this.stickers.render({ source: this.source, now, donations, length,
      unit: settings.DONATION_UNIT, platform: settings.PLATFORM });
    this.timeline.draw({ curve, length, now, events, donations, sections: this.sections.items, selected: this.sections.selected });
    this.ui.playButton.textContent = this.clock.playing ? "❚❚" : "▶";
    this.ui.timeText.textContent = `${fmtTime(now)} / ${fmtTime(length)}`;
    this.ui.speedText.textContent = `지금 속도 ×${curve.at(now).toFixed(2)} · 채팅 ${events.length}개` +
      (donations.length ? ` · 후원 ${donations.length}번` : "");
  }
}
