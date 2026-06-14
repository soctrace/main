import { Check } from "lucide-react";
import { ActionButton } from "@/landing/components/ActionButton";
import { SectionHeading } from "@/landing/components/SectionHeading";
import { SectionShell } from "@/landing/components/SectionShell";
import { SurfaceCard } from "@/landing/components/SurfaceCard";
import type { PricingPlan } from "@/landing/data/content";

type PricingSectionProps = {
  items: PricingPlan[];
};

export function PricingSection({ items }: PricingSectionProps) {
  return (
    <SectionShell id="pricing">
      <SectionHeading
        eyebrow="Pricing"
        title="Una tabla simple, seria y lista para cuando el producto quiera explicitar oferta."
        description="Oculta en el MVP, pero conectada a la misma arquitectura para activar una fase más comercial sin reconstrucción."
      />
      <div className="mt-10 grid gap-4 lg:grid-cols-2">
        {items.map((item) => (
          <SurfaceCard
            key={item.name}
            className={`p-6 ${item.featured ? "border-[rgba(244,124,42,0.28)] bg-[linear-gradient(135deg,rgba(74,111,165,0.12),rgba(244,124,42,0.08))]" : ""}`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xl font-semibold text-white">{item.name}</p>
                <p className="mt-3 text-3xl font-semibold text-white">{item.price}</p>
              </div>
              {item.featured ? (
                <span className="chip border-[rgba(244,124,42,0.28)] bg-[linear-gradient(90deg,rgba(74,111,165,0.12),rgba(244,124,42,0.12))] text-white">
                  Recommended
                </span>
              ) : null}
            </div>
            <p className="mt-4 text-sm leading-7 text-slate-300">{item.description}</p>
            <div className="mt-6 grid gap-3">
              {item.features.map((feature) => (
                <div key={feature} className="flex items-center gap-3 text-sm text-slate-200">
                  <Check className="h-4 w-4 text-soc-warm" />
                  <span>{feature}</span>
                </div>
              ))}
            </div>
            <ActionButton href="#cta" variant={item.featured ? "primary" : "secondary"} className="mt-8">
              Hablar con nosotros
            </ActionButton>
          </SurfaceCard>
        ))}
      </div>
    </SectionShell>
  );
}
