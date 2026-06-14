import { Link } from "react-router-dom";
import { SectionShell } from "@/landing/components/SectionShell";
import soctraceBrandIcon from "@/assets/soctrace-brand-icon.png";

export function Footer() {
  return (
    <SectionShell id="footer" className="pb-10 pt-4">
      <footer className="flex flex-col gap-5 border-t border-white/[0.08] pt-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <Link to="/" className="flex items-center gap-4 transition hover:opacity-90" aria-label="Ir al inicio de soctrace">
          <img src={soctraceBrandIcon} alt="" className="h-10 w-10 rounded-lg object-contain" />
          <div className="flex flex-col gap-1">
            <p className="brand-mark text-[1.7rem] font-semibold leading-none tracking-[-0.04em] text-white">
              soctrace
            </p>
            <p className="max-w-xl text-sm leading-6 text-slate-400">
              Convierte datos geográficos, demográficos y electorales en decisiones estratégicas claras.
            </p>
          </div>
        </Link>
        <div className="flex flex-wrap gap-5">
          <Link to="/" className="transition hover:text-white">
            Inicio
          </Link>
          <a href="mailto:hola@soctrace.com" className="transition hover:text-white">
            hola@soctrace.com
          </a>
        </div>
      </footer>
    </SectionShell>
  );
}
