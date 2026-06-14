import { SectionShell } from "@/landing/components/SectionShell";

type LogoStripSectionProps = {
  items: string[];
};

export function LogoStripSection({ items }: LogoStripSectionProps) {
  return (
    <SectionShell className="pt-6">
      <div className="panel-soft overflow-hidden px-6 py-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <p className="text-sm uppercase tracking-[0.28em] text-slate-500">
            pensado para equipos que convierten territorio en decisión
          </p>
          <div className="grid flex-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {items.map((item) => (
              <div
                key={item}
                className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-center text-sm font-medium text-slate-200"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}
