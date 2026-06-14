import { Panel } from "@/components/ui/Panel";
import type { PartyResult } from "@/data/mockSectionDetails";

type BarChartMockProps = {
  data: PartyResult[];
};

export function BarChartMock({ data }: BarChartMockProps) {
  const max = Math.max(...data.map((item) => item.value));

  return (
    <Panel className="p-4">
      <div className="mb-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Party Results 2023
        </p>
      </div>

      <div className="space-y-3">
        {data.map((item) => (
          <div key={item.party} className="grid grid-cols-[70px_1fr_52px] items-center gap-3">
            <div className="text-sm text-slate-300">{item.party}</div>
            <div className="h-3 rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(item.value / max) * 100}%`,
                  background: `linear-gradient(90deg, ${item.color}, color-mix(in srgb, ${item.color} 35%, white))`,
                }}
              />
            </div>
            <div className="text-right text-sm text-slate-400">{item.value}%</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
