import type { DashboardSearchItem } from "@/config/searchIndex";
import { SOCIAL_DEVELOPMENT_UI_YEAR } from "@/types/api";
import { useDashboardStore } from "@/store/useDashboardStore";

export function applyDashboardSearchItem(item: DashboardSearchItem) {
  const store = useDashboardStore.getState();

  if (item.targetLayer) {
    store.selectLayer(item.targetLayer, item.targetSubLayer);
  }

  if (item.targetLandMetric) {
    store.setLandBuiltEnvironmentMetric(item.targetLandMetric);
  }

  if (item.targetTerritorialMetric) {
    store.setTerritorialMetric(item.targetTerritorialMetric);
  }

  if (item.targetSocioeconomicMetric) {
    store.setSocioeconomicView(SOCIAL_DEVELOPMENT_UI_YEAR);
    store.setSocioeconomicMetric(item.targetSocioeconomicMetric);
  }

  if (item.targetCampaignMetric) {
    store.setCampaignForecastMetric(item.targetCampaignMetric);
  }

  const focusElementId = item.focusElementId;
  if (!focusElementId) {
    return;
  }

  window.requestAnimationFrame(() => {
    const element = document.getElementById(focusElementId);
    element?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLButtonElement) {
      element.focus({ preventScroll: true });
    }
  });
}
