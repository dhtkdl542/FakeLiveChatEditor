// 상태가 바뀌면 구독자에게 알리는 기본 클래스
export class Observable {
  #listeners = new Set();

  subscribe(fn) {
    this.#listeners.add(fn);
    return () => this.#listeners.delete(fn);
  }

  emit(value) {
    for (const fn of [...this.#listeners]) fn(value);
  }
}
