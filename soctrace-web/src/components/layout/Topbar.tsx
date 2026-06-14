import {
  Bell,
  Command,
  LogOut,
  Shield,
  Zap,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import soctraceBrandIcon from "@/assets/soctrace-brand-icon.png";
import { DashboardSearch } from "@/components/dashboard/DashboardSearch";
import { Button } from "@/components/ui/Button";
import { HoverTooltip } from "@/components/ui/HoverTooltip";
import { Panel } from "@/components/ui/Panel";
import { useDashboardStore } from "@/store/useDashboardStore";

function BetaTooltip() {
  return (
    <div className="w-max rounded-xl border border-white/10 bg-[#070b14]/95 px-3 py-2 text-xs font-medium text-slate-200 shadow-[0_16px_40px_rgba(0,0,0,0.36)]">
      No disponible en la versión beta
    </div>
  );
}

export function Topbar() {
  const navigate = useNavigate();
  const { email, role, access, signOut } = useAuth();
  const municipality = useDashboardStore((state) => state.selectedMunicipality);
  const dataSource = useDashboardStore((state) => state.dataSource);

  async function handleLogout() {
    await signOut();
    navigate("/login", { replace: true });
  }

  return (
    <Panel
      tone="elevated"
      className="grid grid-cols-[minmax(0,1fr)] items-center gap-4 px-5 py-4 lg:grid-cols-[260px_minmax(0,1fr)_auto]"
    >
      <button
        type="button"
        onClick={() => navigate("/")}
        className="flex items-center gap-3 rounded-2xl text-left transition hover:bg-white/[0.035] focus:outline-none focus:ring-2 focus:ring-cyan-400/30"
        aria-label="Volver a Inicio"
      >
        <img
          src={soctraceBrandIcon}
          alt=""
          className="h-10 w-10 rounded-lg object-contain"
        />
        <div>
          <p className="brand-mark text-[1.15rem] font-semibold leading-none tracking-[-0.04em] text-white">
            soctrace
          </p>
          <p className="text-[0.72rem] uppercase tracking-[0.18em] text-slate-500">
            Inteligencia urbana
          </p>
        </div>
      </button>

      <div className="grid gap-3 xl:grid-cols-[220px_minmax(0,1fr)]">
        <button
          type="button"
          className="flex h-12 items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 text-left"
        >
          <div className="flex items-center gap-3">
            <Shield className="h-4 w-4 text-slate-400" />
            <span className="text-sm text-slate-200">{municipality}</span>
          </div>
        </button>

        <DashboardSearch />
      </div>

      <div className="flex items-center justify-end gap-2">
        <div
          className={`rounded-xl border px-3 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.16em] ${
            dataSource === "api"
              ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
              : dataSource === "mock"
                ? "border-amber-400/20 bg-amber-400/10 text-amber-200"
                : "border-rose-400/20 bg-rose-400/10 text-rose-200"
          }`}
        >
          {dataSource === "api"
            ? "API en directo"
            : dataSource === "mock"
              ? "Datos de prueba"
              : "Backend desconectado"}
        </div>
        <HoverTooltip content={<BetaTooltip />} tooltipClassName="w-max" autoFlip placement="bottom">
          <Button variant="secondary" size="sm">
            <Zap className="h-4 w-4" />
            Acciones rápidas
          </Button>
        </HoverTooltip>
        <button
          type="button"
          aria-label="Menú de comandos"
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-slate-300 transition hover:border-cyan-300/16 hover:text-white"
        >
          <Command className="h-4 w-4" />
        </button>
        <HoverTooltip content={<BetaTooltip />} tooltipClassName="w-max" autoFlip placement="bottom">
          <button
            type="button"
            aria-label="Alertas"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-slate-300 transition hover:border-cyan-300/16 hover:text-white"
          >
            <Bell className="h-4 w-4" />
          </button>
        </HoverTooltip>
        <button
          type="button"
          onClick={handleLogout}
          className="flex h-10 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 text-sm text-slate-300 transition hover:border-cyan-300/16 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Salir
        </button>
        <div className="ml-2 flex h-10 items-center gap-2 rounded-full border border-cyan-300/20 bg-[linear-gradient(135deg,#1d4ed8,#0f172a)] px-3 text-sm font-semibold text-white">
          <span>{(email?.slice(0, 2) || "ST").toUpperCase()}</span>
          {role ? <span className="hidden text-[0.62rem] uppercase tracking-[0.12em] text-cyan-100/70 sm:inline">{role} · {access}</span> : null}
        </div>
      </div>
    </Panel>
  );
}
