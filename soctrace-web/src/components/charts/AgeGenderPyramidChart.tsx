export type AgeGenderPyramidRow = {
  cohort: string;
  women: number;
  men: number;
};

export type AgeStructureInsightInput = {
  totalPopulation?: number | null;
  averageAge?: number | null;
  pct65Plus?: number | null;
  pctUnder30?: number | null;
  dominantCohort?: string | null;
  genderBalance?: number | null;
};

const formatCompact = (value: number) =>
  value >= 1000 ? `${Math.round(value / 100) / 10}k` : Math.round(value).toLocaleString("es-ES");

export function generateAgeStructureInsight({
  totalPopulation,
  averageAge,
  pct65Plus,
  pctUnder30,
  dominantCohort,
  genderBalance,
}: AgeStructureInsightInput) {
  if (!totalPopulation || totalPopulation <= 0) {
    return "Age structure data is limited for this view, so interpretation remains intentionally cautious.";
  }

  const over65 = pct65Plus ?? 0;
  const under30 = pctUnder30 ?? 0;
  const womenLean = genderBalance != null && genderBalance > 0.54;
  const menLean = genderBalance != null && genderBalance < 0.46;

  if (over65 >= 0.24 || (averageAge != null && averageAge >= 44.5)) {
    return "Senior cohorts are prominent, indicating stronger ageing pressure in this area.";
  }

  if (under30 >= 0.34 || dominantCohort === "0-14" || dominantCohort === "15-29") {
    return "Younger and working-age groups dominate, suggesting a more family-oriented residential profile.";
  }

  if (womenLean) {
    return "Women slightly outnumber men, while working-age cohorts carry most demographic weight.";
  }

  if (menLean) {
    return "Men slightly outnumber women, with working-age cohorts remaining the main population base.";
  }

  return "Older cohorts remain visible, while working-age groups concentrate most of the population.";
}

export function AgeGenderPyramidChart({
  rows,
  estimated = false,
  isLoading = false,
}: {
  rows: AgeGenderPyramidRow[];
  estimated?: boolean;
  isLoading?: boolean;
}) {
  const maxValue = Math.max(...rows.flatMap((row) => [row.women, row.men]), 0);

  if (maxValue <= 0) {
    return (
      <div className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 text-sm text-slate-500">
        {isLoading ? "Loading pyramid..." : "No gender-age structure available."}
      </div>
    );
  }

  return (
    <div className="h-full rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Pirámide de población
          </p>
          <p className="mt-1 text-xs font-medium text-slate-400">Mujeres y hombres por edad</p>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-[10px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#c084fc]" />
            Mujeres
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#67e8f9]" />
            Hombres
          </span>
        </div>
      </div>

      <div className="mt-4 space-y-2.5">
        {[...rows].reverse().map((row) => {
          const womenWidth = `${Math.max(3, (row.women / maxValue) * 100)}%`;
          const menWidth = `${Math.max(3, (row.men / maxValue) * 100)}%`;

          return (
            <div key={row.cohort} className="grid grid-cols-[minmax(0,1fr)_42px_minmax(0,1fr)] items-center gap-2">
              <div className="flex items-center justify-end gap-2">
                <span className="hidden text-[10px] tabular-nums text-slate-500 sm:inline">
                  {formatCompact(row.women)}
                </span>
                <div className="flex h-4 w-full items-center justify-end rounded-l-full bg-white/[0.025]">
                  <div
                    className="h-4 rounded-l-full border border-white/10 bg-[linear-gradient(90deg,rgba(76,29,149,0.42),rgba(192,132,252,0.78))]"
                    style={{ width: womenWidth }}
                  />
                </div>
              </div>
              <div className="relative text-center">
                <span className="relative z-10 rounded-full bg-[#0b1220] px-1.5 text-[10px] font-semibold text-slate-400">
                  {row.cohort}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex h-4 w-full items-center rounded-r-full bg-white/[0.025]">
                  <div
                    className="h-4 rounded-r-full border border-white/10 bg-[linear-gradient(90deg,rgba(103,232,249,0.78),rgba(14,116,144,0.36))]"
                    style={{ width: menWidth }}
                  />
                </div>
                <span className="hidden text-[10px] tabular-nums text-slate-500 sm:inline">
                  {formatCompact(row.men)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex items-center justify-center gap-3 border-t border-white/[0.06] pt-3 text-[10px] text-slate-500">
        <span>Women</span>
        <span className="h-6 w-px bg-slate-600/50" />
        <span>Men</span>
      </div>
      {estimated ? (
        <p className="mt-2 text-[10px] leading-4 text-slate-600">
          Split by cohort estimated from available gender totals.
        </p>
      ) : null}
    </div>
  );
}
