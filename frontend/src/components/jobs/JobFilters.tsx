import { Search } from "lucide-react";
import type { JobFilters } from "../../types/job";
import { CheckboxDropdown } from "../ui/CheckboxDropdown";
import { ClearableInput } from "../ui/ClearableInput";

interface Props {
  filters: JobFilters;
  sources: string[];
  countries: string[];
  /** per-source job counts (stats.by_source) — shown next to each option */
  sourceCounts?: Record<string, number>;
  onChange: (next: JobFilters) => void;
}

const SCAM_OPTIONS = [
  { value: "100", label: "Всі" },
  { value: "60", label: "Без явного скаму" },
  { value: "30", label: "Тільки безпечні" },
];

const LEVEL_OPTIONS = [
  { value: "", label: "Будь-який рівень" },
  { value: "junior", label: "Junior" },
  { value: "middle", label: "Middle" },
  { value: "senior", label: "Senior" },
];

const YEARS_OPTIONS = [
  { value: "", label: "Досвід, роки" },
  { value: "0-1", label: "0–1 рік" },
  { value: "1-3", label: "1–3 роки" },
  { value: "3-5", label: "3–5 років" },
  { value: "5-10", label: "5–10 років" },
  { value: "10+", label: "10+ років" },
];

const LANG_OPTIONS = [
  { value: "", label: "Будь-яка мова" },
  { value: "en", label: "English" },
  { value: "pl", label: "Polski" },
  { value: "de", label: "Deutsch" },
  { value: "fr", label: "Français" },
  { value: "es", label: "Español" },
  { value: "it", label: "Italiano" },
  { value: "uk", label: "Українська" },
  { value: "pt", label: "Português" },
  { value: "nl", label: "Nederlands" },
  { value: "cs", label: "Čeština" },
];

const WORKPLACE_OPTIONS: { value: JobFilters["workplace"][number]; label: string }[] = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Гібрид" },
  { value: "office", label: "Офіс" },
];

const SORT_OPTIONS = [
  { value: "score", label: "Найбезпечніші" },
  { value: "newest", label: "Найновіші" },
];

const CURRENCY_OPTIONS = [
  { value: "", label: "Валюта: будь-яка" },
  { value: "USD", label: "USD ($)" },
  { value: "EUR", label: "EUR (€)" },
  { value: "UAH", label: "UAH (₴)" },
  { value: "GBP", label: "GBP (£)" },
];

const INPUT =
  "rounded-lg border border-slate-700 bg-slate-800 px-2 pr-2 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-sky-600";

export function JobFiltersBar({ filters, sources, countries, sourceCounts, onChange }: Props) {
  const set = (patch: Partial<JobFilters>) => onChange({ ...filters, ...patch });
  const srcLabel =
    filters.sources.length === 0
      ? "Всі джерела"
      : filters.sources.join(", ");
  const ctrLabel =
    filters.countries.length === 0
      ? "Всі країни"
      : filters.countries.join(", ");
  const wpLabel =
    filters.workplace.length === 0
      ? "Тип роботи"
      : filters.workplace.length === WORKPLACE_OPTIONS.length
        ? "Всі типи"
        : WORKPLACE_OPTIONS.filter((o) => filters.workplace.includes(o.value))
            .map((o) => o.label)
            .join(", ");
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative min-w-52 flex-1">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <ClearableInput
          wrapperClassName="w-full"
          className={`${INPUT} pl-3`}
          placeholder="Пошук за назвою, компанією, описом…"
          value={filters.q}
          onChange={(e) => set({ q: e.target.value })}
          onClear={() => set({ q: "" })}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
        />
      </div>

      <CheckboxDropdown
        className="w-44"
        label={srcLabel}
        options={sources
          .filter(
            // hide dead sources (0 jobs) — but keep selected ones visible
            // so the user can still uncheck them
            (s) =>
              !sourceCounts ||
              (sourceCounts[s] ?? 0) > 0 ||
              filters.sources.includes(s)
          )
          .map((s) => ({
            value: s,
            label: (
              <>
                <span className="flex-1">{s}</span>
                <span className="text-slate-500">{sourceCounts?.[s] ?? 0}</span>
              </>
            ),
          }))}
        selected={filters.sources}
        onChange={(next) => set({ sources: next })}
        columns={3}
      />

      <CheckboxDropdown
        className="w-44"
        label={ctrLabel}
        options={countries}
        selected={filters.countries}
        onChange={(next) => set({ countries: next })}
        columns={3}
      />

      <select
        className={INPUT}
        value={String(filters.maxScam ?? 100)}
        onChange={(e) =>
          set({ maxScam: Number(e.target.value), scamLevel: "" })
        }
      >
        {SCAM_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <CheckboxDropdown
        className="w-44"
        label={wpLabel}
        options={WORKPLACE_OPTIONS}
        selected={filters.workplace}
        onChange={(next) =>
          set({
            workplace: next,
            remoteOnly: next.includes("remote"),
          })
        }
      />

      <select
        className={INPUT}
        value={filters.level}
        onChange={(e) => set({ level: e.target.value as JobFilters["level"] })}
      >
        {LEVEL_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={INPUT}
        value={filters.years}
        onChange={(e) => set({ years: e.target.value as JobFilters["years"] })}
      >
        {YEARS_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={INPUT}
        value={filters.lang}
        onChange={(e) => set({ lang: e.target.value as JobFilters["lang"] })}
      >
        {LANG_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <ClearableInput
        type="number"
        min={0}
        wrapperClassName="w-32"
        className={INPUT}
        placeholder={`ЗП від, ${filters.currency}`}
        value={filters.minSalary ?? ""}
        onClear={() => set({ minSalary: null })}
        onChange={(e) =>
          set({ minSalary: e.target.value ? Number(e.target.value) : null })
        }
      />

      <select
        className={INPUT}
        value={filters.currency}
        onChange={(e) => set({ currency: e.target.value as JobFilters["currency"] })}
      >
        {CURRENCY_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className={INPUT}
        value={filters.sort}
        onChange={(e) => set({ sort: e.target.value as JobFilters["sort"] })}
      >
        {SORT_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
