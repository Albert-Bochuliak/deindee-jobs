import { useCallback, useEffect, useRef, useState } from "react";
import { fetchJobs, fetchLocations, fetchSources, fetchStats } from "../api/client";
import type { Job, JobFilters, Stats } from "../types/job";
import { useDebounce } from "./useDebounce";
import { storageRead, storageReadJSON, storageWrite } from "../utils/storage";

const FILTERS_KEY = "jobFilters";
const PER_PAGE_KEY = "jobsPerPage";
const COLS_KEY = "jobCols";
const FETCH_ALL = 2000; // cap: pull everything that matches, paginate client-side

/** Per-page options per column count — every value fills grid rows evenly. */
export const PER_PAGE_OPTIONS: Record<number, number[]> = {
  1: [10, 20, 30, 40, 50],
  2: [10, 20, 30, 40, 50],
  3: [9, 15, 21, 30, 54],
  4: [8, 16, 24, 32, 48],
};

function loadPerPage(): number {
  const n = Number(storageRead(PER_PAGE_KEY));
  return n >= 1 && n <= 60 ? n : 20;
}

function loadCols(): number {
  const n = Number(storageRead(COLS_KEY));
  return n >= 1 && n <= 4 ? n : 3;
}

function loadFilters(): JobFilters {
  const saved = storageReadJSON<Partial<JobFilters> & { source?: string }>(FILTERS_KEY);
  if (!saved) return DEFAULT_FILTERS;
  const merged = { ...DEFAULT_FILTERS, ...saved };
  // migrate legacy single-source string
  if (typeof saved.source === "string" && saved.source && !merged.sources.length) {
    merged.sources = [saved.source];
  }
  delete (merged as { source?: string }).source;
  return merged;
}

//default filters
const DEFAULT_FILTERS: JobFilters = {
  q: "",
  sources: [],
  maxScam: 100,
  scamLevel: "",
  remoteOnly: false,
  minSalary: null,
  currency: "",
  level: "",
  years: "",
  lang: "",
  workplace: [],
  countries: [],
  sort: "score",
};


// loading filters from local storage
export function useJobs(initialCountries?: string[]) {
  const [filters, setFilters] = useState<JobFilters>(() => {
    const loaded = loadFilters();
    // scrape location selection wins over stale saved countries
    if (initialCountries?.length) loaded.countries = initialCountries;
    return loaded;
  });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [countries, setCountries] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(loadPerPage);
  const [cols, setCols] = useState(loadCols);
  const debouncedFilters = useDebounce(filters);

  // latest debounced filters via ref — keeps `reload` STABLE so callers
  // (the scrape poll loop) always read fresh filters, not a stale closure
  const filtersRef = useRef(debouncedFilters);
  filtersRef.current = debouncedFilters;

  const reload = useCallback(
    async (opts?: { silent?: boolean; append?: boolean }) => {
      if (!opts?.silent) setLoading(true);
      setError(null);
      try {
        const [jobsData, statsData] = await Promise.all([
          fetchJobs(filtersRef.current, FETCH_ALL),
          fetchStats(filtersRef.current),
        ]);
        setJobs((prev) => {
          // scrape poll passes append — card positions stay put, new
          // arrivals go to the END of the queue. Replacing the array with
          // a freshly relevance-sorted list every 1.5s made the grid jump.
          if (!opts?.append || !prev.length) return jobsData;
          const seen = new Set(prev.map((j) => j.id));
          const fresh = jobsData.filter((j) => !seen.has(j.id));
          return fresh.length ? [...prev, ...fresh] : prev;
        });
        setStats(statsData);
      } catch (e) {
        setError(e instanceof Error ? e.message : "API недоступне — запустіть uvicorn на :8001");
      } finally {
        if (!opts?.silent) setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    reload();
  }, [reload, debouncedFilters]);

  // wipe the visible list + stale keyword filter — new scrape runs start
  // from an empty board (the live repo already IS this run's results)
  const clear = useCallback(() => {
    setJobs([]);
    setStats(null);
    setPage(1);
    setFilters((f) => (f.q ? { ...f, q: "" } : f));
  }, []);

  useEffect(() => {
    storageWrite(FILTERS_KEY, JSON.stringify(filters));
  }, [filters]);

  // sources + locations live outside filters — refetched on demand
  // (e.g. after credentials change enables a new source)
  const refreshMeta = useCallback(() => {
    fetchSources()
      .then((s) =>
        setSources([...new Set([...s.configured, ...s.with_data])].sort())
      )
      .catch((e) => {
        console.warn("[jobs] sources fetch failed:", e);
        setSources([]);
      });
    fetchLocations()
      .then(setCountries)
      .catch((e) => {
        console.warn("[jobs] locations fetch failed:", e);
        setCountries([]);
      });
  }, []);

  useEffect(() => {
    refreshMeta();
  }, [refreshMeta]);

  // any filter change -> back to page 1
  useEffect(() => {
    setPage(1);
  }, [debouncedFilters]);

  useEffect(() => {
    storageWrite(PER_PAGE_KEY, String(perPage));
    setPage(1);
  }, [perPage]);

  // column change: persist + snap perPage to a valid option for this layout
  useEffect(() => {
    storageWrite(COLS_KEY, String(cols));
    const opts = PER_PAGE_OPTIONS[cols];
    setPerPage((pp) => (opts.includes(pp) ? pp : opts[2]));
  }, [cols]);

  // derived: page SIZE capped by result count; page POSITION clamped to valid
  const effectivePerPage = Math.min(perPage, Math.max(1, jobs.length));
  const totalPages = Math.max(1, Math.ceil(jobs.length / effectivePerPage));
  const safePage = Math.min(page, totalPages);
  const pagedJobs = jobs.slice(
    (safePage - 1) * effectivePerPage,
    safePage * effectivePerPage
  );

  // the hook's public API — named so the shape reads as a contract
  const api = {
    // fetched data
    jobs, sources, countries, stats,
    // request state
    loading, error,
    // filters + refresh
    filters, setFilters, reload, refreshMeta, clear,
    // pagination (derived values + setters)
    pagedJobs, safePage, setPage,
    effectivePerPage, totalPages, setPerPage,
    cols, setCols,
  };
  return api;
}
