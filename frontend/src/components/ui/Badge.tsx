import type { ReactNode } from "react";

type Tone = "gray" | "green" | "yellow" | "red" | "blue";

const TONES: Record<Tone, string> = {
  gray: "bg-slate-700 text-slate-200",
  green: "bg-emerald-900/60 text-emerald-300 border border-emerald-700",
  yellow: "bg-amber-900/60 text-amber-300 border border-amber-700",
  red: "bg-red-900/60 text-red-300 border border-red-700",
  blue: "bg-sky-900/60 text-sky-300 border border-sky-700",
};

export function Badge({ tone = "gray", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}
