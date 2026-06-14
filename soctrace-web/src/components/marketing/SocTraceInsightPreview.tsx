import { Activity, Gauge, MapPinned, UsersRound } from "lucide-react";
import { t } from "@/i18n";

type SocTraceInsightPreviewProps = {
  eyebrow?: string;
  title?: string;
};

const ageBars = [
  { label: "0-18", value: 42 },
  { label: "19-35", value: 76 },
  { label: "36-55", value: 63 },
  { label: "56+", value: 38 },
];

const urbanMetrics = [
  { label: t.marketing.income, value: 72, color: "bg-soc-warm/75" },
  { label: t.marketing.density, value: 58, color: "bg-soc-accent/75" },
  { label: t.marketing.services, value: 81, color: "bg-emerald-300/75" },
  { label: t.marketing.housing, value: 66, color: "bg-violet-300/75" },
];

export function SocTraceInsightPreview({
  eyebrow = t.marketing.demoPreview,
  title = t.marketing.insightPreview,
}: SocTraceInsightPreviewProps) {
  return (
    <aside className="panel-dark relative overflow-hidden p-5 sm:p-6">
      <div className="absolute inset-x-0 top-0 h-28 bg-[radial-gradient(circle_at_top,rgba(74,111,165,0.22),transparent_55%)]" />
      <div className="absolute -left-16 bottom-8 h-36 w-36 rounded-full bg-soc-accent/10 blur-3xl" />
      <div className="relative flex items-start justify-between gap-4 border-b border-white/[0.08] pb-4">
        <div>
          <p className="chip">{eyebrow}</p>
          <h2 className="mt-4 text-2xl font-semibold text-white">{title}</h2>
          <p className="mt-3 max-w-lg text-sm leading-6 text-slate-400">
            Lectura compacta de secciones, población, renta y señales urbanas para decisiones territoriales.
          </p>
        </div>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-soc-warm">
          <MapPinned className="h-6 w-6" />
        </div>
      </div>

      <div className="relative mt-5 grid gap-4">
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.035] p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <UsersRound className="h-4 w-4 text-cyan-200" />
              <p className="text-xs font-semibold text-slate-300">{t.marketing.ageStructure}</p>
            </div>
            <span className="text-[0.68rem] text-slate-500">2025</span>
          </div>
          <div className="mt-4 grid gap-3">
            {ageBars.map((bar) => (
              <div key={bar.label} className="grid grid-cols-[2.6rem_1fr_2.2rem] items-center gap-3">
                <span className="text-[0.68rem] text-slate-500">{bar.label}</span>
                <div className="h-2 rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,rgba(45,212,191,0.75),rgba(59,130,246,0.78))]"
                    style={{ width: `${bar.value}%` }}
                  />
                </div>
                <span className="text-right text-[0.68rem] tabular-nums text-slate-400">{bar.value}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-[rgba(244,124,42,0.18)] bg-white/[0.035] p-4">
            <div className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-soc-warm" />
              <p className="text-xs font-semibold text-slate-300">{t.marketing.qualityLife}</p>
            </div>
            <div className="relative mx-auto mt-5 h-28 w-28">
              <div className="absolute inset-0 rounded-full border-[10px] border-white/[0.06]" />
              <div className="absolute inset-0 rounded-full border-[10px] border-transparent border-t-soc-warm border-r-soc-accent rotate-45" />
              <div className="absolute inset-5 flex items-center justify-center rounded-full border border-white/[0.08] bg-[#08111f]">
                <span className="text-2xl font-semibold text-white">7,6</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-[rgba(74,111,165,0.18)] bg-white/[0.035] p-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-soc-accent" />
              <p className="text-xs font-semibold text-slate-300">{t.marketing.urbanIndicators}</p>
            </div>
            <div className="mt-4 space-y-3">
              {urbanMetrics.map((metric) => (
                <div key={metric.label}>
                  <div className="mb-1 flex items-center justify-between text-[0.68rem] text-slate-500">
                    <span>{metric.label}</span>
                    <span>{metric.value}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/[0.06]">
                    <div className={`h-full rounded-full ${metric.color}`} style={{ width: `${metric.value}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-6 gap-2 rounded-2xl border border-white/[0.06] bg-[#07101b]/70 p-3">
          {Array.from({ length: 24 }).map((_, index) => (
            <span
              key={index}
              className={`aspect-square rounded-md border border-white/[0.04] ${
                index % 7 === 0
                  ? "bg-soc-warm/75"
                  : index % 5 === 0
                    ? "bg-emerald-300/55"
                    : index % 3 === 0
                      ? "bg-soc-accent/55"
                      : "bg-white/[0.055]"
              }`}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
