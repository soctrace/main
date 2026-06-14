import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Search } from "lucide-react";
import { dashboardSearchIndex, type DashboardSearchItem } from "@/config/searchIndex";
import { applyDashboardSearchItem } from "@/lib/dashboardSearch";

function normalizeSearchText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function itemSearchText(item: DashboardSearchItem) {
  return normalizeSearchText([item.label, item.description, item.category, ...(item.aliases ?? [])].filter(Boolean).join(" "));
}

export function DashboardSearch() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const suggestions = useMemo(() => {
    const normalizedQuery = normalizeSearchText(query);
    if (!normalizedQuery) {
      return [];
    }

    return dashboardSearchIndex
      .filter((item) => itemSearchText(item).includes(normalizedQuery))
      .slice(0, 8);
  }, [query]);

  const selectSuggestion = (item: DashboardSearchItem) => {
    applyDashboardSearchItem(item);
    setQuery("");
    setOpen(false);
    setHighlightedIndex(0);
  };

  useEffect(() => {
    setHighlightedIndex(0);
  }, [query]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      setOpen(true);
    }

    if (event.key === "Escape") {
      setOpen(false);
      return;
    }

    if (suggestions.length === 0) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightedIndex((index) => (index + 1) % suggestions.length);
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightedIndex((index) => (index - 1 + suggestions.length) % suggestions.length);
    }

    if (event.key === "Enter") {
      event.preventDefault();
      selectSuggestion(suggestions[highlightedIndex]);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <label className="flex h-12 items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 transition hover:border-cyan-300/16 hover:bg-white/[0.05] focus-within:border-cyan-300/20 focus-within:bg-white/[0.055]">
        <Search className="h-4 w-4 text-slate-500" />
        <input
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Buscar secciones, barrios, variables..."
          className="w-full border-none bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
          aria-autocomplete="list"
          aria-expanded={open && suggestions.length > 0}
          aria-controls="dashboard-search-suggestions"
        />
        <span className="hidden rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1 text-[0.65rem] text-slate-500 sm:inline-flex">
          ⌘ K
        </span>
      </label>

      {open && query.trim() ? (
        <div
          id="dashboard-search-suggestions"
          role="listbox"
          className="absolute left-0 right-0 top-[calc(100%+0.45rem)] z-40 overflow-hidden rounded-2xl border border-white/10 bg-[#070b14]/95 shadow-[0_22px_70px_rgba(0,0,0,0.48)] backdrop-blur-xl"
        >
          {suggestions.length > 0 ? (
            suggestions.map((item, index) => (
              <button
                key={item.id}
                type="button"
                role="option"
                aria-selected={highlightedIndex === index}
                onMouseEnter={() => setHighlightedIndex(index)}
                onClick={() => selectSuggestion(item)}
                className={`flex w-full items-center justify-between gap-3 border-b border-white/[0.045] px-3.5 py-2.5 text-left last:border-b-0 transition ${
                  highlightedIndex === index ? "bg-cyan-300/[0.075]" : "hover:bg-white/[0.045]"
                }`}
              >
                <span className="min-w-0">
                  <span className="block truncate text-[0.82rem] font-semibold text-slate-100">{item.label}</span>
                  {item.description ? (
                    <span className="mt-0.5 block truncate text-[0.68rem] text-slate-500">{item.description}</span>
                  ) : null}
                </span>
                <span className="shrink-0 rounded-md border border-white/[0.07] bg-white/[0.035] px-1.5 py-1 text-[0.56rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  {item.category}
                </span>
              </button>
            ))
          ) : (
            <div className="px-3.5 py-3 text-[0.78rem] text-slate-500">No se han encontrado variables del panel</div>
          )}
        </div>
      ) : null}
    </div>
  );
}
