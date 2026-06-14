import { ArrowUpRight } from "lucide-react";
import { PreviewFrame } from "@/landing/components/PreviewFrame";
import { SectionHeading } from "@/landing/components/SectionHeading";
import { SectionShell } from "@/landing/components/SectionShell";
import { SurfaceCard } from "@/landing/components/SurfaceCard";
import type { Capability } from "@/landing/data/content";

type CapabilitiesSectionProps = {
  items: Capability[];
};

export function CapabilitiesSection({ items }: CapabilitiesSectionProps) {
  return (
    <SectionShell id="capabilities">
      <div className="grid gap-12 lg:grid-cols-[0.92fr_minmax(0,1.08fr)]">
        <div>
          <SectionHeading
            eyebrow="Producto / Capabilities"
            title="Un único módulo visible hoy, pero construido como el primer ladrillo de una landing larga."
            description="El MVP concentra el mensaje esencial y al mismo tiempo deja listas las piezas narrativas que más adelante podrán mostrar historia, pantallas, prueba social, changelog y pricing."
          />

          <div className="mt-10 grid gap-4">
            {items.map((item) => {
              const Icon = item.icon;

              return (
                <SurfaceCard key={item.title} className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.22em] text-soc-accent">
                        {item.eyebrow}
                      </p>
                      <h3 className="mt-3 text-2xl font-semibold text-white">{item.title}</h3>
                    </div>
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
                      <Icon className="h-5 w-5 text-soc-accent" />
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-slate-300">{item.description}</p>
                  <div className="mt-5 grid gap-3 sm:grid-cols-3">
                    {item.bullets.map((bullet) => (
                      <div
                        key={bullet}
                        className="rounded-2xl border border-white/[0.08] bg-slate-950/50 px-4 py-3 text-sm text-slate-300"
                      >
                        {bullet}
                      </div>
                    ))}
                  </div>
                </SurfaceCard>
              );
            })}
          </div>
        </div>

        <div className="space-y-6">
          <PreviewFrame
            title="soctrace.sections.intro"
            accent="from-soc-accent/24 via-slate-900 to-soc-warm/14"
            lines={["segment municipalities", "score friction points", "compare adjacent zones", "prepare decision brief"]}
          />

          <SurfaceCard className="p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                  why this matters
                </p>
                <h3 className="mt-2 text-xl font-semibold text-white">
                  La home ya nace con mentalidad de sistema.
                </h3>
              </div>
              <ArrowUpRight className="h-5 w-5 text-soc-accent" />
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {[
                "Config centralizada para activar y desactivar bloques.",
                "Secciones con contratos simples y reutilizables.",
                "Preparada para contenido real sin tocar la estructura base.",
                "Escalable hacia ventas, demos o verticales específicas.",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-4 text-sm leading-6 text-slate-300"
                >
                  {item}
                </div>
              ))}
            </div>
          </SurfaceCard>
        </div>
      </div>
    </SectionShell>
  );
}
