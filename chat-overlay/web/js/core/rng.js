// chatov/rng.py 와 똑같은 수열을 내는 시드 난수
export class Mulberry32 {
  constructor(seed) {
    this.state = seed >>> 0;
  }

  next() {
    this.state = (this.state + 0x6D2B79F5) >>> 0;
    let t = this.state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t = ((t + Math.imul(t ^ (t >>> 7), t | 61)) ^ t) >>> 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  uniform(lo, hi) {
    return lo + this.next() * (hi - lo);
  }

  below(n) {
    return Math.floor(this.next() * n);
  }

  static randomSeed() {
    return Math.floor(Math.random() * 4294967296);
  }
}
