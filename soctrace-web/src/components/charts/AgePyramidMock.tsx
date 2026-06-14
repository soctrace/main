import { Panel } from "@/components/ui/Panel";
import type { AgePyramidDatum } from "@/data/mockSectionDetails";

type AgePyramidMockProps = {
  data: AgePyramidDatum[];
};

export function AgePyramidMock({ data }: AgePyramidMockProps) {
  const max = Math.max(...data.map((item) => Math.max(item.men, item.women)));

  return (
    <Panel className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Age Pyramid
          </p>
        </div>
        <div className="flex items-center gap-3 text-[0.72rem] text-slate-400">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-pink-400" />
            Women
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-blue-400" />
            Men
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {data.map((item) => (
          <div key={item.label} className="grid grid-cols-[40px_1fr_40px_1fr] items-center gap-2">
            <div className="text-right text-[0.7rem] text-slate-500">{item.label}</div>
            <div className="flex justify-end">
              <div
                className="h-4 rounded-l-full bg-[linear-gradient(90deg,rgba(244,114,182,0.28),rgba(236,72,153,0.92))]"
                style={{ width: `${(item.women / max) * 100}%` }}
              />
            </div>
            <div className="border-l border-white/10 pl-2 text-[0.68rem] text-slate-500"> </div>
            <div>
              <div
                className="h-4 rounded-r-full bg-[linear-gradient(90deg,rgba(59,130,246,0.9),rgba(96,165,250,0.35))]"
                style={{ width: `${(item.men / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex justify-between text-[0.68rem] text-slate-500">
        <span>6%</span>
        <span>0</span>
        <span>6%</span>
      </div>
    </Panel>
  );
}
