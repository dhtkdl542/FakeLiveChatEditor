// 방송 플랫폼: 후원 단위 · 자주 나오는 금액 · 후원창(알림) 모양. 실제 로고 · 상표는 쓰지 않는다.
export const PLATFORMS = Object.freeze({
  panda: Object.freeze({ label: "팬더티비", unit: "하트", alert: "panda",
    amounts: Object.freeze([10, 30, 50, 100, 300, 550, 1000]) }),
  afreeca: Object.freeze({ label: "아프리카TV (숲)", unit: "별풍선", alert: "afreeca",
    amounts: Object.freeze([1, 10, 50, 100, 333, 486, 500, 999, 1000, 2871, 4860]) }),
  youtube: Object.freeze({ label: "유튜브", unit: "₩", alert: "youtube",
    amounts: Object.freeze([1000, 2000, 5000, 10000, 20000, 50000, 100000]) }),
});

export const DEFAULT_PLATFORM = "panda";

export function platformKey(key) {
  return Object.hasOwn(PLATFORMS, key) ? key : DEFAULT_PLATFORM;
}

export function platformOf(key) {
  return PLATFORMS[platformKey(key)];
}

/** 플랫폼을 고르면 바뀌는 입력칸 값. 그 뒤로 단위 · 금액은 사용자가 마음대로 고칠 수 있다. */
export function platformFields(key) {
  const k = platformKey(key);
  return { platform: k, donationUnit: PLATFORMS[k].unit, donationAmounts: PLATFORMS[k].amounts.join(", ") };
}
