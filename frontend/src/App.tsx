import { Briefcase } from "lucide-react";
import { ScrapeBar } from "./components/ScrapeBar";
import { JobFiltersBar } from "./components/jobs/JobFilters";
import { JobList } from "./components/jobs/JobList";
import { Pagination } from "./components/jobs/Pagination";
import { StatsBar } from "./components/StatsBar";
import { useJobs, PER_PAGE_OPTIONS } from "./hooks/useJobs";
import { useScrape } from "./hooks/useScrape";

export default function App() {
  const scrape = useScrape();
  // scrape locations initialize the countries filter — one data source,
  // later changes go through the ScrapeBar onLocations action (no sync effect)
  const {
    jobs, sources, countries, stats, loading, error,
    filters, setFilters, reload,
    pagedJobs, safePage, setPage,
    effectivePerPage, setPerPage, cols, setCols,
  } = useJobs(scrape.locations);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/60">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-4">
          <h1 className="flex items-center gap-2 text-xl font-bold">
            <Briefcase className="text-sky-400" /> Job Scraper
          </h1>
          <div className="ml-auto flex items-center gap-2">
            <ScrapeBar
              scrape={scrape}
              remoteOnly={filters.remoteOnly}
              applyQuery={(q) => setFilters((f) => ({ ...f, q }))}
              onLocations={(locs) =>
                setFilters((f) => ({ ...f, countries: locs }))
              }
              reload={reload}
            />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-6">
        {scrape.msg && (
          <div className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-300">
            {scrape.msg}
          </div>
        )}
        <StatsBar
          stats={stats}
          active={filters.scamLevel}
          onSelect={(scamLevel) =>
            setFilters({ ...filters, scamLevel, maxScam: 100 })
          }
          activeSources={filters.sources}
          onSelectSource={(source) =>
            setFilters({
              ...filters,
              sources: filters.sources.includes(source)
                ? filters.sources.filter((s) => s !== source)
                : [...filters.sources, source],
            })
          }
        />
        <JobFiltersBar filters={filters} sources={sources} countries={scrape.locations.length ? scrape.locations : countries} onChange={setFilters} />
        <div className="text-sm text-slate-400">
          {loading ? "Завантаження…" : `Знайдено: ${jobs.length}`}
        </div>
        <JobList jobs={pagedJobs} loading={loading} error={error} cols={cols} />
        {!loading && !error && (
          <Pagination
            total={jobs.length}
            page={safePage}
            perPage={effectivePerPage}
            perPageOptions={PER_PAGE_OPTIONS[cols]}
            cols={cols}
            onCols={setCols}
            onPage={setPage}
            onPerPage={setPerPage}
          />
        )}
      </main>
    </div>
  );
}
