// 스타일 탭 '닉네임 배지' 카드: 배지 모양 고르기와 지금 닉네임 중 누가 어떤 배지인지 보여 주기
import { badgeSummary, DEFAULT_BADGES } from "../core/badges.js";
import { ICON_LABELS, ICON_NAMES } from "../core/icons.js";
import { Settings } from "../core/settings.js";
import { $, h, setStatus } from "./dom.js";

export class BadgesView {
  constructor(form) {
    this.form = form;
    for (const b of DEFAULT_BADGES) {
      const field = Settings.badgeField(b.key, "Icon");
      const select = document.querySelector(`[data-field="${field}"]`);
      select.replaceChildren(...ICON_NAMES.map(n => h("option", { value: n }, ICON_LABELS[n])));
      select.value = b.icon;
    }
  }

  refresh(settings) {
    if (!settings.BADGES_ON) return setStatus($("#badgeSummary"), "배지가 꺼져 있습니다.");
    const { groups, none } = badgeSummary(settings.NICKS, settings.BADGES, settings.BADGE_OVERRIDES);
    const parts = groups.map(g => `${g.label}: ${g.nicks.join(", ")}`);
    parts.push(`배지 없음 ${none.length}명`);
    setStatus($("#badgeSummary"), "지금 닉네임 → " + parts.join(" · "));
  }
}
