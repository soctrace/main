import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { ActionButton } from "@/landing/components/ActionButton";
import { SectionShell } from "@/landing/components/SectionShell";

export function CTASection() {
  return (
    <SectionShell id="cta">
      <div className="panel-dark overflow-hidden">
        <div className="relative px-6 py-12 sm:px-10 sm:py-14 lg:px-14 lg:py-16">
          <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(circle_at_center,rgba(74,111,165,0.18),transparent_44%),radial-gradient(circle_at_70%_55%,rgba(244,124,42,0.12),transparent_36%)] lg:block" />
          <div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <span className="chip">Final CTA</span>
              <h2 className="mt-6 text-balance text-4xl font-semibold text-white sm:text-5xl">
                Lanza una primera impresión fuerte hoy y activa nuevos módulos cuando el producto lo pida.
              </h2>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300">
                El MVP ya comunica con peso visual y deja resuelta la arquitectura futura. La siguiente fase no exige rehacer la landing: solo encender bloques.
              </p>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row lg:flex-col lg:items-end">
              <Link
                to="/request-demo"
                className="inline-flex items-center justify-center rounded-full border border-[rgba(244,124,42,0.38)] bg-[linear-gradient(135deg,#f1f5f9_0%,#f47c2a_18%,#4a6fa5_100%)] px-5 py-3 text-sm font-semibold text-white shadow-[0_0_0_1px_rgba(255,255,255,0.08),0_20px_70px_rgba(74,111,165,0.22)] transition duration-200 hover:-translate-y-0.5 hover:brightness-110"
              >
                Solicitar demo
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <ActionButton href="#hero" variant="secondary">
                Volver arriba
              </ActionButton>
            </div>
          </div>
        </div>
      </div>
    </SectionShell>
  );
}
