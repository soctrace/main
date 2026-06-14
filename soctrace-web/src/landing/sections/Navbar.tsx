import { Link } from "react-router-dom";
import { Menu } from "lucide-react";
import type { NavItem } from "@/landing/data/content";
import { t } from "@/i18n";
import soctraceBrandIcon from "@/assets/soctrace-brand-icon.png";

type NavbarProps = {
  items: NavItem[];
};

export function Navbar({ items }: NavbarProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.05] bg-[#07090d]/92 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4 sm:px-8 lg:px-10">
        <Link to="/" className="flex items-center gap-3" aria-label="Ir al inicio de soctrace">
          <img
            src={soctraceBrandIcon}
            alt=""
            className="h-10 w-10 rounded-lg object-contain"
          />
          <p className="brand-mark text-[1.9rem] font-semibold leading-none tracking-[-0.04em] text-white">
            soctrace
          </p>
        </Link>

        <nav className="hidden items-center gap-10 text-[0.95rem] text-slate-400 lg:flex">
          {items.map((item) => (
            <Link key={item.href} to={item.href} className="transition hover:text-slate-200">
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-6 lg:flex">
          <div className="h-6 w-px bg-white/[0.09]" />
          <Link
            to="/login"
            className="rounded-xl border border-[rgba(74,111,165,0.24)] bg-[linear-gradient(135deg,rgba(74,111,165,0.08),rgba(244,124,42,0.05))] px-4 py-2 text-[0.95rem] text-slate-100 transition hover:-translate-y-0.5 hover:border-[rgba(244,124,42,0.28)] hover:text-white"
          >
            {t.nav.demo}
          </Link>
          <Link to="/login" className="text-[0.95rem] text-slate-300 transition hover:text-white">
            {t.nav.login}
          </Link>
          <Link
            to="/request-demo"
            className="rounded-xl bg-white px-5 py-3 text-[0.95rem] font-medium text-slate-950 transition hover:bg-slate-100"
          >
            {t.nav.requestDemo}
          </Link>
        </div>

        <button
          type="button"
          aria-label="Abrir navegación"
          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-slate-200 md:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}
