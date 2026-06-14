type PreviewFrameProps = {
  title?: string;
  lines?: string[];
  accent?: string;
};

export function PreviewFrame({
  title = "soctrace.product.capabilities",
  lines = [],
  accent = "from-soc-accent/30 via-slate-950 to-soc-warm/12",
}: PreviewFrameProps) {
  return (
    <div className="panel-dark overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-soc-warm/85" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#b58b63]/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-soc-accent/85" />
        </div>
        <span className="text-xs text-slate-400">{title}</span>
      </div>

      <div className={`relative bg-gradient-to-br ${accent} p-5`}>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.12),transparent_24%)]" />
        <div className="relative grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[1.4rem] border border-white/[0.08] bg-slate-950/70 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                  orquestación
                </p>
                <p className="mt-2 text-sm font-medium text-slate-200">
                  Espacio de inteligencia electoral
                </p>
              </div>
              <span className="rounded-full border border-soc-warm/20 bg-soc-warm/10 px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-[#f5b489]">
                en directo
              </span>
            </div>
            <div className="space-y-3">
              {lines.map((line, index) => (
                <div
                  key={line}
                  className="flex items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.03] px-3 py-2"
                >
                  <span className="text-xs text-slate-500">{String(index + 1).padStart(2, "0")}</span>
                  <div className="h-2 w-full rounded-full bg-[linear-gradient(90deg,rgba(244,124,42,0.75),rgba(74,111,165,0.85),rgba(255,255,255,0.16))]" />
                  <span className="min-w-fit text-xs text-slate-300">{line}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4">
            <div className="rounded-[1.4rem] border border-white/[0.08] bg-slate-950/70 p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">territorios</p>
              <div className="mt-4 grid grid-cols-2 gap-3">
                {["Centro", "Litoral", "Norte", "Rural"].map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-3 py-4 text-center text-sm text-slate-200"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-[1.4rem] border border-white/[0.08] bg-slate-950/70 p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">signal delta</p>
              <div className="mt-4 flex h-28 items-end gap-3">
                {[42, 68, 38, 84, 56, 72].map((height) => (
                  <div
                    key={height}
                    className="flex-1 rounded-t-[1rem] bg-[linear-gradient(180deg,rgba(255,255,255,0.15),rgba(244,124,42,0.55),rgba(74,111,165,0.88))]"
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
