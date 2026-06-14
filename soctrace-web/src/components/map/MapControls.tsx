import { Focus, Layers3, Minus, Plus } from "lucide-react";

type MapControlsProps = {
  mode: "map" | "satellite";
  scale: {
    label: string;
    widthPx: number;
  };
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFocus: () => void;
  onToggleMode: () => void;
};

export function MapControls({
  mode,
  scale,
  onZoomIn,
  onZoomOut,
  onFocus,
  onToggleMode,
}: MapControlsProps) {
  return (
    <>
      <div className="absolute bottom-4 right-4 z-10 inline-flex rounded-2xl border border-white/10 bg-[#09111d]/88 p-1 backdrop-blur-xl">
        <button
          type="button"
          onClick={onToggleMode}
          className={`rounded-xl px-4 py-2 text-sm transition ${
            mode === "map" ? "bg-white/[0.08] text-white" : "text-slate-400 hover:text-white"
          }`}
        >
          Dark
        </button>
        <button
          type="button"
          onClick={onToggleMode}
          className={`rounded-xl px-4 py-2 text-sm transition ${
            mode === "satellite" ? "bg-white/[0.08] text-white" : "text-slate-400 hover:text-white"
          }`}
        >
          Context
        </button>
      </div>

      <div className="absolute right-4 top-4 z-10 flex flex-col gap-2">
        {[{ icon: Plus, onClick: onZoomIn }, { icon: Minus, onClick: onZoomOut }].map(
          ({ icon: Icon, onClick }, index) => (
            <button
              key={index}
              type="button"
              onClick={onClick}
              className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-[#09111d]/90 text-slate-200 backdrop-blur-xl transition hover:border-cyan-300/20 hover:text-white"
            >
              <Icon className="h-4 w-4" />
            </button>
          ),
        )}
        <button
          type="button"
          onClick={onFocus}
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-[#09111d]/90 text-slate-200 backdrop-blur-xl transition hover:border-cyan-300/20 hover:text-white"
        >
          <Focus className="h-4 w-4" />
        </button>
      </div>

      <div className="absolute bottom-4 left-4 z-10 flex items-center gap-2 rounded-xl border border-white/10 bg-[#09111d]/88 px-3 py-2 text-[0.7rem] font-medium text-slate-300 shadow-[0_14px_34px_rgba(0,0,0,0.28)] backdrop-blur-xl transition">
        <span
          className="relative block h-3 border-b border-l border-r border-cyan-100/70 transition-[width]"
          style={{ width: `${scale.widthPx}px` }}
          aria-hidden="true"
        />
        <span className="tabular-nums">{scale.label}</span>
      </div>
    </>
  );
}
