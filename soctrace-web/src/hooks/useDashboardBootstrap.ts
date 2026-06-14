import { useEffect, useState } from "react";
import {
  fetchApiHealth,
  getApiBaseUrl,
  fetchMunicipalities,
  fetchSectionDetail,
  fetchSectionsGeoJson,
} from "@/lib/api";
import { getActiveLayer } from "@/lib/sectionPresentation";
import { useDashboardStore } from "@/store/useDashboardStore";
import {
  ageStructureYears,
  incomeYears,
  electionContests,
  populationYears,
  SOCIAL_DEVELOPMENT_UI_YEAR,
  type IncomeSourceKey,
  type AgeCohortPoint,
  type MunicipalityAgeStructureSummary,
  type MunicipalityIncomeSummary,
  type MunicipalityPopulationSummary,
  type SectionFeatureCollection,
} from "@/types/api";

const OPERATIONAL_DATA_YEAR = "2023";
const incomeSourceKeys = [
  "income_salary",
  "income_pension",
  "income_unemployment",
  "income_social_benefits",
  "income_other",
] as const satisfies readonly IncomeSourceKey[];

function finiteNumber(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function buildMunicipalityPopulationSummary(
  year: string,
  collection: SectionFeatureCollection,
): MunicipalityPopulationSummary {
  const totals = collection.features.reduce(
    (accumulator, feature) => {
      const properties = feature.properties;
      const population = finiteNumber(properties.population_total) ?? 0;
      const men =
        finiteNumber(properties.population_male) ??
        (finiteNumber(properties.pct_male) != null ? population * Number(properties.pct_male) : 0);
      const women =
        finiteNumber(properties.population_female) ??
        (finiteNumber(properties.pct_female) != null ? population * Number(properties.pct_female) : 0);
      const density = finiteNumber(properties.population_density);
      const explicitArea = finiteNumber(properties.area_km2);
      // Temporary compatibility fallback for older API payloads before area_km2 was exposed.
      const derivedArea = explicitArea ?? (density && population > 0 ? population / density : 0);

      return {
        populationTotal: accumulator.populationTotal + population,
        menTotal: accumulator.menTotal + men,
        womenTotal: accumulator.womenTotal + women,
        areaKm2: accumulator.areaKm2 + derivedArea,
      };
    },
    { populationTotal: 0, menTotal: 0, womenTotal: 0, areaKm2: 0 },
  );
  const genderTotal = totals.menTotal + totals.womenTotal;

  return {
    year: Number(year),
    populationTotal: Math.round(totals.populationTotal),
    menTotal: Math.round(totals.menTotal),
    womenTotal: Math.round(totals.womenTotal),
    menPct: genderTotal > 0 ? totals.menTotal / genderTotal : 0,
    womenPct: genderTotal > 0 ? totals.womenTotal / genderTotal : 0,
    areaKm2: totals.areaKm2,
    density: totals.areaKm2 > 0 ? totals.populationTotal / totals.areaKm2 : null,
  };
}

const municipalAgeCohortFields = [
  { cohort: "0-14", field: "population_0_14" },
  { cohort: "15-29", field: "population_15_29" },
  { cohort: "30-44", field: "population_30_44" },
  { cohort: "45-64", field: "population_45_64" },
  { cohort: "65+", field: "population_65_plus" },
] as const;

function buildMunicipalityAgeStructureSummary(
  year: string,
  collection: SectionFeatureCollection,
): MunicipalityAgeStructureSummary {
  const totals = collection.features.reduce(
    (accumulator, feature) => {
      const properties = feature.properties;
      const population = finiteNumber(properties.population_total) ?? 0;
      const averageAge = finiteNumber(properties.average_age);
      const men =
        finiteNumber(properties.population_male) ??
        (finiteNumber(properties.pct_male) != null ? population * Number(properties.pct_male) : 0);
      const women =
        finiteNumber(properties.population_female) ??
        (finiteNumber(properties.pct_female) != null ? population * Number(properties.pct_female) : 0);
      const foreignBornPct = finiteNumber(properties.pct_foreign_born);

      municipalAgeCohortFields.forEach(({ cohort, field }) => {
        accumulator.cohorts[cohort] =
          (accumulator.cohorts[cohort] ?? 0) + (finiteNumber(properties[field]) ?? 0);
      });

      return {
        totalPopulation: accumulator.totalPopulation + population,
        weightedAge:
          accumulator.weightedAge + (averageAge != null ? averageAge * population : 0),
        weightedAgePopulation:
          accumulator.weightedAgePopulation + (averageAge != null ? population : 0),
        populationMale: accumulator.populationMale + men,
        populationFemale: accumulator.populationFemale + women,
        weightedForeignBorn:
          accumulator.weightedForeignBorn + (foreignBornPct != null ? foreignBornPct * population : 0),
        weightedForeignBornPopulation:
          accumulator.weightedForeignBornPopulation + (foreignBornPct != null ? population : 0),
        cohorts: accumulator.cohorts,
      };
    },
    {
      totalPopulation: 0,
      weightedAge: 0,
      weightedAgePopulation: 0,
      populationMale: 0,
      populationFemale: 0,
      weightedForeignBorn: 0,
      weightedForeignBornPopulation: 0,
      cohorts: {} as Record<string, number>,
    },
  );
  const cohorts: AgeCohortPoint[] = municipalAgeCohortFields.map(({ cohort }) => ({
    cohort,
    population: Math.round(totals.cohorts[cohort] ?? 0),
  }));
  const under30 = (totals.cohorts["0-14"] ?? 0) + (totals.cohorts["15-29"] ?? 0);
  const over65 = totals.cohorts["65+"] ?? 0;

  return {
    year: Number(year),
    totalPopulation: Math.round(totals.totalPopulation),
    populationMale: Math.round(totals.populationMale),
    populationFemale: Math.round(totals.populationFemale),
    cohorts,
    averageAge:
      totals.weightedAgePopulation > 0 ? totals.weightedAge / totals.weightedAgePopulation : null,
    over65Pct: totals.totalPopulation > 0 ? over65 / totals.totalPopulation : null,
    under30Pct: totals.totalPopulation > 0 ? under30 / totals.totalPopulation : null,
    foreignBornPct:
      totals.weightedForeignBornPopulation > 0
        ? totals.weightedForeignBorn / totals.weightedForeignBornPopulation
        : null,
  };
}

function average(values: number[]) {
  return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
}

function buildMunicipalityIncomeSummary(
  year: string,
  collection: SectionFeatureCollection,
): MunicipalityIncomeSummary {
  // TODO: replace section means with weighted municipal aggregates when household
  // counts or a stable population weighting contract is available for every year.
  const individualValues: number[] = [];
  const householdValues: number[] = [];
  const sourceValues = Object.fromEntries(incomeSourceKeys.map((key) => [key, [] as number[]])) as Record<
    IncomeSourceKey,
    number[]
  >;

  collection.features.forEach((feature) => {
    const properties = feature.properties;
    const individualIncome = finiteNumber(properties.renta_media_persona);
    const householdIncome = finiteNumber(properties.renta_media_hogar);
    if (individualIncome != null) {
      individualValues.push(individualIncome);
    }
    if (householdIncome != null) {
      householdValues.push(householdIncome);
    }
    incomeSourceKeys.forEach((key) => {
      const value = finiteNumber(properties[key]);
      if (value != null) {
        sourceValues[key].push(value);
      }
    });
  });

  return {
    year: Number(year),
    individualIncome: average(individualValues),
    householdIncome: average(householdValues),
    sources: Object.fromEntries(
      incomeSourceKeys.map((key) => [key, average(sourceValues[key])]),
    ) as Record<IncomeSourceKey, number | null>,
  };
}

export function useDashboardBootstrap() {
  const [retryTick, setRetryTick] = useState(0);
  const selectedMunicipalityId = useDashboardStore((state) => state.selectedMunicipalityId);
  const selectedSectionId = useDashboardStore((state) => state.selectedSectionId);
  const electionContestId = useDashboardStore((state) => state.filters.electionContestId);
  const populationYear = useDashboardStore((state) => state.filters.populationYear);
  const ageStructureYear = useDashboardStore((state) => state.filters.ageStructureYear);
  const incomeYear = useDashboardStore((state) => state.filters.incomeYear);
  const layers = useDashboardStore((state) => state.layers);
  const sectionDetailsById = useDashboardStore((state) => state.sectionDetailsById);
  const municipalityPopulationByYear = useDashboardStore((state) => state.municipalityPopulationByYear);
  const municipalityAgeStructureByYear = useDashboardStore((state) => state.municipalityAgeStructureByYear);
  const municipalityIncomeByYear = useDashboardStore((state) => state.municipalityIncomeByYear);
  const electoralCollectionsByContest = useDashboardStore((state) => state.electoralCollectionsByContest);
  const setMunicipalities = useDashboardStore((state) => state.setMunicipalities);
  const setSectionCollection = useDashboardStore((state) => state.setSectionCollection);
  const setSectionDetail = useDashboardStore((state) => state.setSectionDetail);
  const setMunicipalityPopulationSummaries = useDashboardStore(
    (state) => state.setMunicipalityPopulationSummaries,
  );
  const setMunicipalityAgeStructureSummaries = useDashboardStore(
    (state) => state.setMunicipalityAgeStructureSummaries,
  );
  const setMunicipalityIncomeSummaries = useDashboardStore((state) => state.setMunicipalityIncomeSummaries);
  const setElectoralContestCollection = useDashboardStore(
    (state) => state.setElectoralContestCollection,
  );
  const setMapLoading = useDashboardStore((state) => state.setMapLoading);
  const setDetailLoading = useDashboardStore((state) => state.setDetailLoading);
  const dataSource = useDashboardStore((state) => state.dataSource);
  const setDataSource = useDashboardStore((state) => state.setDataSource);
  const setStatus = useDashboardStore((state) => state.setStatus);
  const setError = useDashboardStore((state) => state.setError);
  const activeLayer = getActiveLayer(layers);
  const selectedElectionContest =
    electionContests.find((contest) => contest.id === electionContestId) ?? electionContests[0];
  const dataYear =
    activeLayer === "population"
      ? populationYear
      : activeLayer === "ageStructure"
        ? ageStructureYear
        : activeLayer === "incomeLevel"
          ? incomeYear
          : activeLayer === "socioeconomicIntelligence"
            ? SOCIAL_DEVELOPMENT_UI_YEAR
            : activeLayer === "electoralBehavior"
              ? selectedElectionContest.year
              : OPERATIONAL_DATA_YEAR;
  const electionId = activeLayer === "electoralBehavior" ? selectedElectionContest.electionId : null;
  const requestLayer = activeLayer;
  const requestElectionId =
    activeLayer === "electoralForecasting" ? null : electionId;

  useEffect(() => {
    let active = true;

    void fetchMunicipalities()
      .then((response) => {
        if (!active) {
          return;
        }
        setMunicipalities(response.items);
      })
      .catch((error) => {
        if (active) {
          setError(error instanceof Error ? error.message : "Unable to load municipalities");
        }
      });

    return () => {
      active = false;
    };
  }, [setError, setMunicipalities]);

  useEffect(() => {
    let active = true;
    setMapLoading(true);
    setError(null);
    setStatus(null);

    void (async () => {
      try {
        const collection = await fetchSectionsGeoJson(
          selectedMunicipalityId,
          dataYear,
          requestLayer,
          requestElectionId,
        );
        if (!active) {
          return;
        }
        console.debug("[soctrace] sections GeoJSON loaded", {
          apiBaseUrl: getApiBaseUrl(),
          municipalityId: selectedMunicipalityId,
          layer: activeLayer,
          year: dataYear,
          electionId: requestElectionId,
          type: collection.type,
          features: collection.features.length,
          bbox: collection.bbox,
          firstGeometryType: collection.features[0]?.geometry?.type,
          firstSectionId: collection.features[0]?.properties.section_id,
          firstDensity: collection.features[0]?.properties.population_density,
        });
          setDataSource("api");
          setSectionCollection(collection);
          if (activeLayer === "electoralBehavior" || activeLayer === "electoralForecasting") {
            setElectoralContestCollection(selectedElectionContest.id, collection);
          }
          setStatus(null);
        } catch (error) {
        if (active) {
          console.error("[soctrace] sections GeoJSON failed", error);
          let backendMessage = `Backend unavailable at ${getApiBaseUrl()}.`;
          try {
            const health = await fetchApiHealth();
            backendMessage = `Backend reachable at ${getApiBaseUrl()} (health: ${health.status}), but the map endpoint failed.`;
          } catch {
            // Keep the offline message when health is not reachable.
          }

          setDataSource("unavailable");
          setSectionCollection(null);
          setStatus(`${backendMessage} The map stays on the Mijas viewport, but no sections are drawn until the backend is available.`, "warning");
          setError(null);
        }
      } finally {
        if (active) {
          setMapLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [
    selectedMunicipalityId,
    activeLayer,
    dataYear,
    electionId,
    requestLayer,
    requestElectionId,
    selectedElectionContest,
    electionContestId,
    retryTick,
    setDataSource,
    setError,
    setMapLoading,
    setElectoralContestCollection,
    setSectionCollection,
    setStatus,
  ]);

  useEffect(() => {
    if (activeLayer !== "electoralBehavior" || dataSource === "mock") {
      return;
    }

    const contestsToLoad = electionContests.filter(
      (contest) =>
        contest.type === selectedElectionContest.type &&
        contest.electionId != null &&
        !electoralCollectionsByContest[contest.id],
    );
    if (contestsToLoad.length === 0) {
      return;
    }

    let active = true;

    void Promise.all(
      contestsToLoad.map(async (contest) => {
        const collection = await fetchSectionsGeoJson(
          selectedMunicipalityId,
          contest.year,
          "electoralBehavior",
          contest.electionId,
        );
        return { contestId: contest.id, collection };
      }),
    )
      .then((items) => {
        if (!active) {
          return;
        }
        items.forEach(({ contestId, collection }) => {
          setElectoralContestCollection(contestId, collection);
        });
      })
      .catch((error) => {
        if (active) {
          console.error("[soctrace] electoral history preload failed", error);
          setStatus("Electoral history is partially unavailable for this election type.", "warning");
        }
      });

    return () => {
      active = false;
    };
  }, [
    activeLayer,
    dataSource,
    electoralCollectionsByContest,
    selectedElectionContest,
    selectedMunicipalityId,
    setElectoralContestCollection,
    setStatus,
  ]);

  useEffect(() => {
    if (activeLayer !== "incomeLevel" || dataSource === "mock") {
      return;
    }

    const missingYears = incomeYears.filter((yearToLoad) => !municipalityIncomeByYear[yearToLoad]);
    if (missingYears.length === 0) {
      return;
    }

    let active = true;

    void Promise.all(
      missingYears.map(async (yearToLoad) => {
        const collection = await fetchSectionsGeoJson(selectedMunicipalityId, yearToLoad, "incomeLevel");
        return buildMunicipalityIncomeSummary(yearToLoad, collection);
      }),
    )
      .then((summaries) => {
        if (active) {
          setMunicipalityIncomeSummaries(summaries);
        }
      })
      .catch((error) => {
        if (active) {
          console.error("[soctrace] municipality income summaries failed", error);
          setStatus("Municipality income overview is temporarily unavailable.", "warning");
        }
      });

    return () => {
      active = false;
    };
  }, [
    activeLayer,
    dataSource,
    municipalityIncomeByYear,
    selectedMunicipalityId,
    setMunicipalityIncomeSummaries,
    setStatus,
  ]);

  useEffect(() => {
    if (activeLayer !== "ageStructure" || dataSource === "mock") {
      return;
    }

    const missingYears = ageStructureYears.filter(
      (yearToLoad) => !municipalityAgeStructureByYear[yearToLoad],
    );
    if (missingYears.length === 0) {
      return;
    }

    let active = true;

    void Promise.all(
      missingYears.map(async (yearToLoad) => {
        const collection = await fetchSectionsGeoJson(selectedMunicipalityId, yearToLoad, "ageStructure");
        return buildMunicipalityAgeStructureSummary(yearToLoad, collection);
      }),
    )
      .then((summaries) => {
        if (active) {
          setMunicipalityAgeStructureSummaries(summaries);
        }
      })
      .catch((error) => {
        if (active) {
          console.error("[soctrace] municipality age structure summaries failed", error);
          setStatus("Municipality age structure overview is temporarily unavailable.", "warning");
        }
      });

    return () => {
      active = false;
    };
  }, [
    activeLayer,
    dataSource,
    municipalityAgeStructureByYear,
    selectedMunicipalityId,
    setMunicipalityAgeStructureSummaries,
    setStatus,
  ]);

  useEffect(() => {
    if (activeLayer !== "population" || dataSource === "mock") {
      return;
    }

    const missingYears = populationYears.filter((yearToLoad) => !municipalityPopulationByYear[yearToLoad]);
    if (missingYears.length === 0) {
      return;
    }

    let active = true;

    void Promise.all(
      missingYears.map(async (yearToLoad) => {
        const collection = await fetchSectionsGeoJson(selectedMunicipalityId, yearToLoad, "population");
        return buildMunicipalityPopulationSummary(yearToLoad, collection);
      }),
    )
      .then((summaries) => {
        if (active) {
          setMunicipalityPopulationSummaries(summaries);
        }
      })
      .catch((error) => {
        if (active) {
          console.error("[soctrace] municipality population summaries failed", error);
          setStatus("Municipality population overview is temporarily unavailable.", "warning");
        }
      });

    return () => {
      active = false;
    };
  }, [
    activeLayer,
    dataSource,
    municipalityPopulationByYear,
    selectedMunicipalityId,
    setMunicipalityPopulationSummaries,
    setStatus,
  ]);

  useEffect(() => {
    if (dataSource !== "unavailable") {
      return;
    }

    const retryTimer = window.setTimeout(() => {
      setRetryTick((value) => value + 1);
    }, 5000);

    return () => {
      window.clearTimeout(retryTimer);
    };
  }, [dataSource]);

  useEffect(() => {
    if (dataSource === "mock" || !selectedSectionId) {
      return;
    }

    const yearsToLoad =
      activeLayer === "population"
        ? populationYears
        : activeLayer === "ageStructure"
          ? ageStructureYears
          : activeLayer === "incomeLevel"
            ? incomeYears
            : [dataYear];
    const missingDetailYears = yearsToLoad.filter(
      (detailYear) => !sectionDetailsById[`${detailYear}:${selectedSectionId}`],
    );

    if (missingDetailYears.length === 0) {
      return;
    }

    let active = true;
    setDetailLoading(true);

    void Promise.all(
      missingDetailYears.map(async (detailYear) => {
        try {
          const detail = await fetchSectionDetail(selectedSectionId, detailYear);
          return { detailYear, detail, error: null };
        } catch (error) {
          return { detailYear, detail: null, error };
        }
      }),
    )
      .then((details) => {
        const unexpectedErrors: unknown[] = [];

        details.forEach(({ detailYear, detail }) => {
          if (!active) {
            return;
          }

          if (!detail) {
            const error = details.find((item) => item.detailYear === detailYear)?.error;
            const message = error instanceof Error ? error.message : "";
            const isExpectedTemporalGap =
              (activeLayer === "population" || activeLayer === "ageStructure" || activeLayer === "incomeLevel") &&
              message.includes("(404)");

            if (isExpectedTemporalGap) {
              console.debug("[soctrace] section detail not available for year", {
                sectionId: selectedSectionId,
                year: detailYear,
              });
              return;
            }

            unexpectedErrors.push(error);
            return;
          }

          console.debug("[soctrace] section detail loaded", {
            sectionId: selectedSectionId,
            year: detailYear,
            label: detail.display.label,
          });
          setSectionDetail(`${detailYear}:${selectedSectionId}`, detail);
        });

        if (unexpectedErrors.length > 0) {
          const [firstError] = unexpectedErrors;
          throw firstError;
        }
      })
      .catch((error) => {
        if (active) {
          console.error("[soctrace] section detail failed", error);
          setError(error instanceof Error ? error.message : "Unable to load section detail");
        }
      })
      .finally(() => {
        if (active) {
          setDetailLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [
    activeLayer,
    sectionDetailsById,
    selectedSectionId,
    dataYear,
    dataSource,
    setDetailLoading,
    setError,
    setSectionDetail,
  ]);
}
