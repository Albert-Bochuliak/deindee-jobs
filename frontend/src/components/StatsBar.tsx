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
      <div className="ml-auto flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {Object.entries(stats.by_source).map(([src, n]) => {
          const isActive = activeSources.includes(src);
          return (
            <button
              key={src}
              type="button"
              onClick={() => onSelectSource(src)}
              title={isActive ? "Прибрати з вибраних" : `Додати до вибраних: ${src}`}
              className={`rounded-lg px-2 py-1 transition ${
                isActive ? "bg-slate-800 text-sky-300 ring-1 ring-sky-600" : "hover:bg-slate-800/60"
              }`}
            >
              {src}: <span className="text-slate-300">{n}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
