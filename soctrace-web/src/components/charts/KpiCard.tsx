import { Building2, ChartSpline, Globe2, UsersRound } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import type { KpiMetric } from "@/data/mockSectionDetails";

const iconRegistry = [UsersRound, ChartSpline, Globe2, Building2];

const toneClass = {
  violet: "from-violet-500/18 to-violet-400/6 text-violet-300",
  cyan: "from-cyan-500/18 to-cyan-400/6 text-cyan-300",
  green: "from-emerald-500/18 to-emerald-400/6 text-emerald-300",
  orange: "from-orange-500/18 to-orange-400/6 text-orange-300",
};

type KpiCardProps = {
  metric: KpiMetric;
  index: number;
};

export function KpiCard({ metric, index }: KpiCardProps) {
  const Icon = iconRegistry[index % iconRegistry.length];

  return (
    <Panel
      className={`bg-gradient-to-br p-4 ${toneClass[metric.tone]}`}
      tone="default"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[1.55rem] font-semibold text-white">{metric.value}</p>
          <p className="mt-1 text-xs tracking-[0.03em] text-slate-400">{metric.label}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2">
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </Panel>
  );
}
