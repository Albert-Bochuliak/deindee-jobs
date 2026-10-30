import { useState } from "react";
import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

export interface DropdownOption<T extends string = string> {
  value: T;
  label: ReactNode;
}

interface Props<T extends string = string> {
  /** plain string (value === label) or {value, label} */
  options: (T | DropdownOption<T>)[];
  selected: T[];
  onChange: (next: T[]) => void;
  /** text on the trigger button — caller decides what it means */
  label: string;
  /** optional icon rendered before the label */
  icon?: ReactNode;
  /** extra classes on the outer relative wrapper (sizing, e.g. w-44) */
  className?: string;
  /** lay options in N columns — wide short panel for long option lists */
  columns?: 1 | 2 | 3;
}

const BTN =
  "rounded-lg border border-slate-700 bg-slate-800 px-2 pr-2 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-sky-600 inline-flex w-full items-center justify-between gap-2";

// static map — Tailwind can't see template-built classes like `grid-cols-${n}`
const COL_CLASSES: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
};

/** Button that opens a checkbox list; outside click closes. */
export function CheckboxDropdown<T extends string = string>({
  options, selected, onChange, label, icon, className, columns,
}: Props<T>) {
  const [open, setOpen] = useState(false);
  const cols = columns ?? 1;
  const multi = cols > 1;
  const toggle = (v: T) =>
    onChange(
      selected.includes(v)
        ? selected.filter((x) => x !== v)
        : [...selected, v]
    );
  return (
    <div className={`relative ${className ?? ""}`}>
      <button type="button" className={BTN} onClick={() => setOpen((v) => !v)}>
        <span className="inline-flex min-w-0 items-center gap-2">
          {icon}
          <span className="truncate">{label}</span>
        </span>
        <ChevronDown
          size={14}
          strokeWidth={3}
          className={`shrink-0 text-slate-100 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div
            className={`absolute left-0 top-full z-20 mt-1 rounded-lg border border-slate-700 bg-slate-800 p-2 shadow-xl ${
              multi
                ? `grid ${COL_CLASSES[cols]} w-max min-w-full gap-0.5`
                : "w-full space-y-1"
            } max-h-[60vh] overflow-y-auto`}
          >
            {options.map((o) => {
              const value = typeof o === "string" ? o : o.value;
              const text = typeof o === "string" ? o : o.label;
              return (
                <label
                  key={value}
                  className="flex cursor-pointer items-center gap-2 whitespace-nowrap rounded px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-700"
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-sky-500"
                    checked={selected.includes(value)}
                    onChange={() => toggle(value)}
                  />
                  {text}
                </label>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
