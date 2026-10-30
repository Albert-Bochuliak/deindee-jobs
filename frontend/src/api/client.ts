import type { AppSettings, Job, JobFilters, ScrapeReport, Stats } from "../types/job";

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

// scam params included: the by_source chips must narrow to the selected
// scam level (level cells themselves ignore them on the backend)
export const fetchStats = (filters: JobFilters) =>
  get<Stats>(`/stats?${filterParams(filters, true)}`);

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
  get<{ running: boolean; new: number; stopped?: boolean }>("/scrape/status");

/** Cooperative stop — the run halts at the next completed fetch. */
export async function stopScrape(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/scrape/stop`, { method: "POST" });
  if (!res.ok) throw new Error(`stop failed: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

/** Error carrying the HTTP status so callers can branch on 401 etc. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const fetchSettings = () => get<AppSettings>("/settings");

export async function saveSettings(
  values: Record<string, string>
): Promise<AppSettings> {
  const res = await fetch(`${BASE}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values }),
  });
  if (!res.ok) throw new ApiError(res.status, `settings save failed: ${res.status}`);
  return res.json() as Promise<AppSettings>;
}

async function adminPost(path: string, body?: unknown): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? "{}" : JSON.stringify(body),
  });
  if (!res.ok) {
    // FastAPI puts a human-readable reason in `detail` — surface it
    let msg = `${path} failed: ${res.status}`;
    try {
      msg = ((await res.json()) as { detail?: string }).detail || msg;
    } catch {
      /* non-json error body */
    }
    throw new ApiError(res.status, msg);
  }
}

export const adminLogin = (username: string, password: string) =>
  adminPost("/admin/login", { username, password });

export const adminLogout = () => adminPost("/admin/logout");

export const adminChangePassword = (current: string, next: string) =>
  adminPost("/admin/password", { current, new: next });
