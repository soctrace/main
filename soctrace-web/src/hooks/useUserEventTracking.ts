import { useEffect, useRef } from "react";
import { trackEvent } from "@/analytics/trackEvent";
import { useAuth } from "@/auth/AuthProvider";
import { getAnalyticsYearForLayer } from "@/lib/dashboardAnalytics";
import { useDashboardStore } from "@/store/useDashboardStore";

export function useUserEventTracking() {
  const { loading, user } = useAuth();
  const selectedMunicipalityId = useDashboardStore((state) => state.selectedMunicipalityId);
  const selectedSectionId = useDashboardStore((state) => state.selectedSectionId);
  const activeLayer = useDashboardStore((state) => state.activeLayer);
  const activeSubLayer = useDashboardStore((state) => state.activeSubLayer);
  const filters = useDashboardStore((state) => state.filters);
  const sectionFeatureById = useDashboardStore((state) => state.sectionFeatureById);
  const dashboardTrackedRef = useRef(false);
  const analyticsLayer = activeSubLayer && activeSubLayer !== activeLayer
    ? `${activeLayer}:${activeSubLayer}`
    : activeLayer;
  const previousLayerRef = useRef(analyticsLayer);
  const previousSectionRef = useRef(selectedSectionId);
  const year = getAnalyticsYearForLayer(activeLayer, filters);

  useEffect(() => {
    if (loading || !user || dashboardTrackedRef.current) return;
    dashboardTrackedRef.current = true;

    void trackEvent({
      event_type: "dashboard_view",
      layer: analyticsLayer,
      year,
      metadata: {
        municipality_id: selectedMunicipalityId,
      },
    });
  }, [analyticsLayer, loading, selectedMunicipalityId, user, year]);

  useEffect(() => {
    if (loading || !user) return;

    if (previousLayerRef.current === analyticsLayer) return;
    previousLayerRef.current = analyticsLayer;

    void trackEvent({
      event_type: "layer_change",
      layer: analyticsLayer,
      year,
      metadata: {
        municipality_id: selectedMunicipalityId,
      },
    });
  }, [analyticsLayer, loading, selectedMunicipalityId, user, year]);

  useEffect(() => {
    if (loading || !user) return;

    if (!selectedSectionId || previousSectionRef.current === selectedSectionId) {
      previousSectionRef.current = selectedSectionId;
      return;
    }
    previousSectionRef.current = selectedSectionId;

    const properties = sectionFeatureById[selectedSectionId]?.properties;

    void trackEvent({
      event_type: "section_view",
      section_id: selectedSectionId,
      section_name: properties?.section_name ?? properties?.label_cliente ?? properties?.label ?? null,
      layer: analyticsLayer,
      year,
      metadata: {
        municipality_id: selectedMunicipalityId,
      },
    });
  }, [analyticsLayer, loading, sectionFeatureById, selectedMunicipalityId, selectedSectionId, user, year]);
}
