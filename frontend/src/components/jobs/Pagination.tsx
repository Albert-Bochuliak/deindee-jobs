import { ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  total: number;
  page: number;
  perPage: number;
  perPageOptions: number[];
  cols: number;
  onCols: (n: number) => void;
  onPage: (p: number) => void;
  onPerPage: (n: number) => void;
}

const COL_OPTIONS = [1, 2, 3, 4];
const WINDOW = 2; // page buttons shown around current

const BTN =
  "min-w-8 rounded-lg border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-300 transition hover:border-sky-600 disabled:opacity-40 disabled:hover:border-slate-700";

function pageNumbers(current: number, totalPages: number): (number | "…")[] {
  const pages = new Set<number>([1, totalPages]);
  for (let i = current - WINDOW; i <= current + WINDOW; i++) {
    if (i >= 1 && i <= totalPages) pages.add(i);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const out: (number | "…")[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) out.push("…");
    out.push(p);
    prev = p;
  }
  return out;
}

export function Pagination({
  total, page, perPage, perPageOptions, cols, onCols, onPage, onPerPage,
}: Props) {
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  if (total <= 1) return null;
  // no sense offering page sizes bigger than the result count
  const ppOpts = perPageOptions.filter((n) => n <= total);
  if (!ppOpts.includes(total)) ppOpts.push(total);
  const shownPerPage = ppOpts.includes(perPage) ? perPage : ppOpts[ppOpts.length - 1];
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-slate-400">
          Стовпців
          <select
            className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-sky-600"
            value={cols}
            onChange={(e) => onCols(Number(e.target.value))}
          >
            {COL_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-400">
          Показувати по
          <select
            className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-sky-600"
            value={shownPerPage}
            onChange={(e) => onPerPage(Number(e.target.value))}
          >
            {ppOpts.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          <button
            className={BTN}
            disabled={page <= 1}
            onClick={() => onPage(page - 1)}
            aria-label="Попередня"
          >
            <ChevronLeft size={15} />
          </button>
          {pageNumbers(page, totalPages).map((p, i) =>
            p === "…" ? (
              <span key={`e${i}`} className="px-1 text-slate-500">
                …
              </span>
            ) : (
              <button
                key={p}
                className={`${BTN} ${p === page ? "border-sky-600 bg-sky-900/40 text-sky-300" : ""}`}
                onClick={() => onPage(p)}
              >
                {p}
              </button>
            )
          )}
          <button
            className={BTN}
            disabled={page >= totalPages}
            onClick={() => onPage(page + 1)}
            aria-label="Наступна"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
