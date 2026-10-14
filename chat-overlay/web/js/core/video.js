// 불러온 영상의 상태. 영상이 없거나 못 읽으면 1920×1080 60초짜리 샘플 화면을 쓴다.
import { Observable } from "./observable.js";

export class VideoSource extends Observable {
  static SAMPLE = Object.freeze({ width: 1920, height: 1080, duration: 60 });

  path = "";
  url = "";
  width = 0;
  height = 0;
  duration = 0;
  playable = false;
  error = null;  // null | "codec" | "unreadable"

  load({ path, url, width = 0, height = 0, duration = 0 }) {
    Object.assign(this, { path, url, width, height, duration, playable: false, error: null });
    this.emit();
  }

  /** 브라우저 <video> 가 영상 정보를 읽었을 때 */
  onMetadata({ videoWidth, videoHeight, duration }) {
    this.playable = true;
    if (videoWidth > 0 && videoHeight > 0) {
      this.width = videoWidth;
      this.height = videoHeight;
    }
    if (Number.isFinite(duration) && duration > 0) this.duration = duration;
    this.emit();
  }

  /** 브라우저가 재생하지 못할 때 (코덱 미지원 등) */
  onError() {
    this.playable = false;
    this.error = this.#hasInfo() ? "codec" : "unreadable";
    this.emit();
  }

  #hasInfo() {
    return this.width > 0 && this.height > 0 && this.duration > 0;
  }

  get hasVideo() {
    return Boolean(this.path) && this.#hasInfo();
  }

  get length() {
    return this.hasVideo ? this.duration : VideoSource.SAMPLE.duration;
  }

  get resolution() {
    return this.hasVideo ? { width: this.width, height: this.height }
      : { width: VideoSource.SAMPLE.width, height: VideoSource.SAMPLE.height };
  }

  get name() {
    return this.path.split(/[\\/]/).pop();
  }
}
