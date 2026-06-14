import { PreviewFrame } from "@/landing/components/PreviewFrame";
import { SectionHeading } from "@/landing/components/SectionHeading";
import { SectionShell } from "@/landing/components/SectionShell";
import type { ScreenshotShowcase } from "@/landing/data/content";

type ScreenshotsSectionProps = {
  items: ScreenshotShowcase[];
};

export function ScreenshotsSection({ items }: ScreenshotsSectionProps) {
  return (
    <SectionShell id="screenshots">
      <SectionHeading
        eyebrow="Screenshots"
        title="Zona preparada para enseñar producto real con una narrativa visual consistente."
        description="Cuando llegue el momento, este bloque puede alternar entre mock previews y capturas reales sin tocar el resto de la arquitectura."
      />

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        {items.map((item, index) => (
          <div key={item.id} className="space-y-5">
            <PreviewFrame
              title={`soctrace.screen.${index + 1}`}
              accent={
                index % 2 === 0
                  ? "from-soc-accent/28 via-slate-950 to-soc-warm/12"
                  : "from-soc-warm/14 via-slate-950 to-soc-accent/22"
              }
              lines={item.points}
            />
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-soc-accent">{item.eyebrow}</p>
              <h3 className="mt-3 text-2xl font-semibold text-white">{item.title}</h3>
              <p className="mt-4 text-sm leading-7 text-slate-300">{item.description}</p>
            </div>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}
