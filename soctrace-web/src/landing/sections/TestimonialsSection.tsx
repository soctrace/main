import { SectionHeading } from "@/landing/components/SectionHeading";
import { SectionShell } from "@/landing/components/SectionShell";
import { SurfaceCard } from "@/landing/components/SurfaceCard";
import type { Testimonial } from "@/landing/data/content";

type TestimonialsSectionProps = {
  items: Testimonial[];
};

export function TestimonialsSection({ items }: TestimonialsSectionProps) {
  return (
    <SectionShell id="testimonials">
      <SectionHeading
        eyebrow="Testimonials"
        title="Prueba social preparada para aparecer cuando toque."
        description="El bloque queda construido aunque oculto por defecto, listo para incorporar citas de clientes o partners sin tocar la composición general."
      />
      <div className="mt-10 grid gap-4 lg:grid-cols-2">
        {items.map((item) => (
          <SurfaceCard key={item.quote} className="p-6">
            <p className="text-lg leading-8 text-slate-100">“{item.quote}”</p>
            <p className="mt-6 text-sm font-semibold text-white">{item.name}</p>
            <p className="mt-1 text-sm text-slate-500">{item.role}</p>
          </SurfaceCard>
        ))}
      </div>
    </SectionShell>
  );
}
