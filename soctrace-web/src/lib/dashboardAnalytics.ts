import { electionContests, SOCIAL_DEVELOPMENT_UI_YEAR, type LayerKey } from "@/types/api";

const OPERATIONAL_DATA_YEAR = "2023";

export function getAnalyticsYearForLayer(
  layer: LayerKey,
  filters: {
    populationYear: string;
    ageStructureYear: string;
    incomeYear: string;
    socioeconomicYear: string;
    electionContestId: string;
  },
) {
  if (layer === "population") return filters.populationYear;
  if (layer === "ageStructure") return filters.ageStructureYear;
  if (layer === "incomeLevel") return filters.incomeYear;
  if (layer === "socioeconomicIntelligence") return filters.socioeconomicYear || SOCIAL_DEVELOPMENT_UI_YEAR;
  if (layer === "electoralBehavior") {
    return electionContests.find((contest) => contest.id === filters.electionContestId)?.year ?? OPERATIONAL_DATA_YEAR;
  }
  return OPERATIONAL_DATA_YEAR;
}
