import { Inbox } from "lucide-react";
import type { Job } from "../../types/job";
import { JobCardSkeleton } from "../ui/Skeleton";
import { JobCard } from "./JobCard";

interface Props {
  jobs: Job[];
  loading: boolean;
  error: string | null;
  cols?: number;
}

const GRID: Record<number, string> = {
  1: "grid-cols-1",
  2: "md:grid-cols-2",
  3: "md:grid-cols-2 xl:grid-cols-3",
  4: "md:grid-cols-2 xl:grid-cols-4",
};

export function JobList({ jobs, loading, error, cols = 3 }: Props) {
  if (error) {
    return (
      <div className="rounded-xl border border-red-900 bg-red-950/40 p-6 text-center text-red-300">
        {error}
      </div>
    );
  }
  // skeletons only when there's nothing to show — on refetch the old grid
  // stays (dimmed) and new cards fade in, no skeleton flash per filter tick
  if (loading && jobs.length === 0) {
    return (
      <div className={`grid auto-rows-fr gap-4 ${GRID[cols] ?? GRID[3]}`}>
        {Array.from({ length: 6 }, (_, i) => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    );
  }
  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 p-12 text-slate-400">
        <Inbox size={32} />
        <p>Вакансій поки немає. Натисніть «Запустити скрапінг» щоб зібрати дані.</p>
      </div>
    );
  }
  return (
    <div
      className={`grid auto-rows-fr gap-4 transition-opacity duration-200 ${GRID[cols] ?? GRID[3]} ${
        loading ? "opacity-50" : ""
      }`}
    >
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
}
