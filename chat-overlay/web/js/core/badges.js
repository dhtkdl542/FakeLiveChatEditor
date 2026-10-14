// 닉네임 배지(매니저 · 열혈팬 · 구독자). 닉네임 해시로 정하므로 같은 닉은 영상 내내 같은 배지(또는 없음).
// chatov/badges.py 와 같은 계산이다. 실제 플랫폼 배지 그림 대신 직접 그린 도형을 쓴다.
const FNV_OFFSET = 0x811C9DC5, FNV_PRIME = 16777619;
const NO_BADGE = ["없음", "none", "-"];

export const DEFAULT_BADGES = Object.freeze([
  Object.freeze({ key: "manager", label: "매니저", icon: "shield", color: "#22c55e", share: 0.08 }),
  Object.freeze({ key: "fan", label: "열혈팬", icon: "heart", color: "#ff4d6d", share: 0.12 }),
  Object.freeze({ key: "sub", label: "구독자", icon: "star", color: "#ffb300", share: 0.25 }),
]);

/** FNV-1a 32비트. 바이트 대신 코드 포인트를 넣어서 Python(ord)과 같은 값이 나온다. */
export function nickHash(nick) {
  let h = FNV_OFFSET;
  for (const ch of nick) h = Math.imul((h ^ ch.codePointAt(0)) >>> 0, FNV_PRIME) >>> 0;
  return h;
}

/** 직접 지정한 배지가 먼저(빈 값 = 없음), 아니면 해시 위치가 들어가는 비율 구간의 배지 */
export function badgeFor(nick, badges, overrides) {
  const byKey = new Map(badges.map(b => [b.key, b]));
  if (Object.hasOwn(overrides, nick) && (overrides[nick] === "" || byKey.has(overrides[nick]))) {
    return byKey.get(overrides[nick]) || null;
  }
  const u = nickHash(nick) / 2 ** 32;
  let edge = 0;
  for (const b of badges) {
    edge += b.share;
    if (u < edge) return b;
  }
  return null;
}

/** "별빛여우 매니저" 처럼 한 줄에 '닉네임 배지이름'. 닉에 띄어쓰기가 있어도 마지막 낱말이 배지. */
export function parseBadgeOverrides(text, badges) {
  const out = {};
  for (const line of String(text || "").split(/\r?\n/)) {
    const m = line.trim().match(/^(.+?)\s+(\S+)$/);
    if (!m) continue;
    const [, nick, name] = m;
    if (NO_BADGE.includes(name)) { out[nick.trim()] = ""; continue; }
    const b = badges.find(x => x.label === name || x.key === name);
    if (b) out[nick.trim()] = b.key;
  }
  return out;
}

/** 지금 닉네임 목록에서 배지별로 누가 받는지 (화면에 보여 주는 용도) */
export function badgeSummary(nicks, badges, overrides) {
  const groups = badges.map(b => ({ label: b.label, nicks: [] }));
  const none = [];
  for (const nick of nicks) {
    const b = badgeFor(nick, badges, overrides);
    if (b) groups[badges.indexOf(b)].nicks.push(nick);
    else none.push(nick);
  }
  return { groups: groups.filter(g => g.nicks.length), none };
}
