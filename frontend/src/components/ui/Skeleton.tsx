export function JobCardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="h-5 w-2/3 rounded bg-slate-700" />
      <div className="mt-2 h-4 w-1/3 rounded bg-slate-800" />
      <div className="mt-4 h-3 w-full rounded bg-slate-800" />
      <div className="mt-2 h-3 w-4/5 rounded bg-slate-800" />
      <div className="mt-4 flex gap-2">
        <div className="h-5 w-16 rounded-full bg-slate-800" />
        <div className="h-5 w-20 rounded-full bg-slate-800" />
      </div>
    </div>
  );
}
