import type { Job, JobFilters, ScrapeReport, Stats } from "../types/job";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const endpoint = path.split("?")[0];
    throw new Error(`Ой лишенько, технічна помилка (${res.status} ${endpoint})`);
  }
  return res.json() as Promise<T>;
}

function filterParams(filters: JobFilters, includeScam: boolean): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.sources.length) params.set("source", filters.sources.join(","));
  if (includeScam) {
    if (filters.maxScam !== null) params.set("max_scam", String(filters.maxScam));
    if (filters.scamLevel) params.set("scam_level", filters.scamLevel);
  }
  if (filters.remoteOnly) params.set("remote_only", "true");
  if (filters.minSalary) params.set("min_salary", String(filters.minSalary));
  if (filters.currency) params.set("currency", filters.currency);
  if (filters.level) params.set("level", filters.level);
  if (filters.years) params.set("years", filters.years);
  if (filters.lang) params.set("lang", filters.lang);
  if (filters.workplace.length) {
    params.set("workplace", filters.workplace.join(","));
  }
  if (filters.countries.length) {
    params.set("countries", filters.countries.join(","));
  }
  return params;
}

export function fetchJobs(filters: JobFilters, limit = 50, offset = 0): Promise<Job[]> {
  const params = filterParams(filters, true);
  if (filters.sort !== "score") params.set("sort", filters.sort);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return get<Job[]>(`/jobs?${params}`);
}

export const fetchSources = () =>
  get<{ configured: string[]; with_data: string[] }>("/sources");

export const fetchLocations = () => get<string[]>("/locations");

export const fetchStats = (filters: JobFilters) =>
  get<Stats>(`/stats?${filterParams(filters, false)}`);

export async function runScrape(
  keywords: string,
  remoteOnly: boolean,
  location: string
): Promise<ScrapeReport> {
  const res = await fetch(`${BASE}/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keywords, remote_only: remoteOnly, location }),
  });
  if (!res.ok) throw new Error(`scrape failed: ${res.status}`);
  return res.json() as Promise<ScrapeReport>;
}

export const fetchScrapeStatus = () =>
  get<{ running: boolean; new: number }>("/scrape/status");
