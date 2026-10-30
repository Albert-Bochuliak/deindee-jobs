import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { ScamLevel, Stats } from "../types/job";

interface Props {
  stats: Stats | null;
  active: ScamLevel;
  onSelect: (level: ScamLevel) => void;
  activeSources: string[];
  onSelectSource: (source: string) => void;
}

const CELLS: {
  key: keyof Pick<Stats, "total" | "safe" | "suspicious" | "scam">;
  label: string;
  cls: string;
  level: ScamLevel;
}[] = [
  { key: "total", label: "Всього", cls: "text-slate-100", level: "" },
  { key: "safe", label: "Безпечні", cls: "text-emerald-400", level: "safe" },
  { key: "suspicious", label: "Підозрілі", cls: "text-amber-400", level: "suspicious" },
  { key: "scam", label: "Скам", cls: "text-red-400", level: "scam" },
];

export function StatsBar({ stats, active, onSelect, activeSources, onSelectSource }: Props) {
  const [srcOpen, setSrcOpen] = useState(false);
  if (!stats) return null;
  return (
    <div className="flex flex-wrap gap-6 rounded-xl border border-slate-800 bg-slate-900 px-5 py-3">
      {CELLS.map(({ key, label, cls, level }) => {
        const isActive = active === level;
        return (
          <button
            key={key}
            type="button"
            onClick={() => onSelect(level)}
            title={level ? `Показати лише: ${label}` : "Показати всі"}
            className={`rounded-lg px-2 py-1 text-center transition ${
              isActive ? "bg-slate-800 ring-1 ring-sky-600" : "hover:bg-slate-800/60"
            }`}
          >
            <div className={`text-xl font-bold ${cls}`}>{stats[key]}</div>
            <div className="text-xs text-slate-500">{label}</div>
          </button>
        );
      })}
      {/* sources live in a hover panel — the flat chip row ate a whole
          line of the bar once the platform list grew past a dozen */}
      <div
        className="relative ml-auto"
        onMouseEnter={() => setSrcOpen(true)}
        onMouseLeave={() => setSrcOpen(false)}
      >
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-slate-800/60"
        >
          Джерела{activeSources.length ? ` (${activeSources.length})` : ""}
          <ChevronDown
            size={12}
            className={`transition-transform ${srcOpen ? "rotate-180" : ""}`}
          />
        </button>
        {srcOpen && (
          // pt-1 wrapper bridges the 4px gap — the cursor must never leave
          // the hover zone between the trigger and the panel
          <div className="absolute right-0 top-full z-20 pt-1">
            {/* column stacks: i % 3 keeps the same visual order as a 3-col
                grid, and border-l on the stack gives ONE solid line — not
                per-cell segments broken by the row gap */}
            <div className="flex max-h-[60vh] w-max overflow-y-auto rounded-lg border border-slate-700 bg-slate-800 p-2 text-xs shadow-xl">
              {[0, 1, 2].map((col) => (
                <div
                  key={col}
                  className={`flex flex-col gap-1 ${
                    col > 0 ? "ml-1 border-l border-slate-600 pl-1" : ""
                  }`}
                >
                  {Object.entries(stats.by_source)
                    .filter((_, i) => i % 3 === col)
                    .map(([src, n]) => {
                      const isActive = activeSources.includes(src);
                      return (
                        <button
                          key={src}
                          type="button"
                          onClick={() => onSelectSource(src)}
                          title={isActive ? "Прибрати з вибраних" : `Додати до вибраних: ${src}`}
                          className={`flex items-center justify-between gap-2 whitespace-nowrap rounded-lg px-2 py-1 text-left transition ${
                            isActive
                              ? "bg-slate-700 text-sky-300 ring-1 ring-sky-600"
                              : "text-slate-400 hover:bg-slate-700"
                          }`}
                        >
                          <span>{src}</span>
                          <span className="text-slate-200">{n}</span>
                        </button>
                      );
                    })}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
