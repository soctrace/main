import { SectionHeading } from "@/landing/components/SectionHeading";
import { SectionShell } from "@/landing/components/SectionShell";
import { SurfaceCard } from "@/landing/components/SurfaceCard";
import type { ChangelogItem } from "@/landing/data/content";

type ChangelogSectionProps = {
  items: ChangelogItem[];
};

export function ChangelogSection({ items }: ChangelogSectionProps) {
  return (
    <SectionShell id="changelog">
      <SectionHeading
        eyebrow="Changelog"
        title="Un bloque listo para producto vivo y evolución pública."
        description="La referencia larga sugiere continuidad; esta sección ya queda preparada para contar releases, mejoras y milestones sin rediseñar."
      />
      <div className="mt-10 grid gap-4">
        {items.map((item) => (
          <SurfaceCard
            key={item.version}
            className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="text-sm font-semibold text-white">{item.version}</p>
              <p className="mt-2 text-sm text-slate-300">{item.summary}</p>
            </div>
            <p className="text-sm uppercase tracking-[0.18em] text-slate-500">{item.date}</p>
          </SurfaceCard>
        ))}
      </div>
    </SectionShell>
  );
}
