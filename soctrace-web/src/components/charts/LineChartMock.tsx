import { Panel } from "@/components/ui/Panel";
import type { LinePoint } from "@/data/mockSectionDetails";

type LineChartMockProps = {
  data: LinePoint[];
};

export function LineChartMock({ data }: LineChartMockProps) {
  const values = data.map((item) => item.value);
  const min = Math.min(...values) - 1;
  const max = Math.max(...values) + 1;
  const points = data
    .map((item, index) => {
      const x = (index / Math.max(data.length - 1, 1)) * 100;
      const y = 100 - ((item.value - min) / (max - min || 1)) * 100;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <Panel className="p-4">
      <div className="mb-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Turnout Evolution
        </p>
      </div>

      <svg viewBox="0 0 100 100" className="h-36 w-full overflow-visible">
        {[0, 25, 50, 75, 100].map((tick) => (
          <line key={tick} x1="0" y1={tick} x2="100" y2={tick} stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
        ))}
        <polyline
          fill="none"
          stroke="url(#turnoutGradient)"
          strokeWidth="2.6"
          points={points}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {data.map((item, index) => {
          const x = (index / Math.max(data.length - 1, 1)) * 100;
          const y = 100 - ((item.value - min) / (max - min || 1)) * 100;
          return <circle key={item.label} cx={x} cy={y} r="2.4" fill="#60A5FA" stroke="#081018" strokeWidth="1.2" />;
        })}
        <defs>
          <linearGradient id="turnoutGradient" x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#2563EB" />
          </linearGradient>
        </defs>
      </svg>

      <div className="mt-3 flex justify-between text-[0.72rem] text-slate-500">
        {data.map((item) => (
          <span key={item.label}>{item.label}</span>
        ))}
      </div>
    </Panel>
  );
}
