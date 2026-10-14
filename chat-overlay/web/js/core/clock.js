// 미리보기의 '지금 시각'. 영상이 있으면 영상 시간을, 없거나 재생이 안 되면 흉내 낸 시간을 쓴다.
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export class SimulatedClock {
  now = 0;
  playing = false;

  constructor(length, loop) {
    this.length = length;
    this.loop = loop;
  }

  play() {
    if (this.now >= this.length - 0.05) this.now = 0;
    this.playing = true;
  }

  pause() {
    this.playing = false;
  }

  seek(t) {
    this.now = clamp(t, 0, this.length);
  }

  tick(dt) {
    if (!this.playing) return;
    this.now += dt;
    if (this.now >= this.length) {
      if (this.loop) this.now %= this.length;
      else { this.now = this.length; this.playing = false; }
    }
  }
}

export class VideoClock {
  constructor(video) {
    this.video = video;
  }

  get now() {
    return this.video.currentTime;
  }

  get playing() {
    return !this.video.paused && !this.video.ended;
  }

  play() {
    if (this.video.ended) this.video.currentTime = 0;
    const p = this.video.play();
    if (p && p.catch) p.catch(() => {});
  }

  pause() {
    this.video.pause();
  }

  seek(t) {
    const end = Number.isFinite(this.video.duration) ? this.video.duration : Infinity;
    this.video.currentTime = clamp(t, 0, end);
  }

  tick() {}
}
