export interface Job {
  id: string;
  source: string;
  url: string;
  title: string;
  company: string | null;
  location: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  remote: boolean;
  description: string;
  published_at: string | null;
  external_id: string | null;
  scam_score: number;
  scam_reasons: string[];
  /** keyword-match rank for the current run; server sorts direct hits first */
  relevance: number;
}

export type JobLevel = "" | "junior" | "middle" | "senior";
export type ExpYears = "" | "0-1" | "1-3" | "3-5" | "5-10" | "10+";
export type JobLang =
  | ""
  | "en"
  | "uk"
  | "pl"
  | "de"
  | "fr"
  | "es"
  | "it"
  | "pt"
  | "nl"
  | "cs";
export type WorkplaceKind = "remote" | "hybrid" | "office";
export type JobSort = "score" | "newest";
export type ScamLevel = "" | "safe" | "suspicious" | "scam";
export type JobCurrency = "" | "USD" | "EUR" | "UAH" | "GBP";

export interface JobFilters {
  q: string;
  sources: string[];
  maxScam: number | null;
  scamLevel: ScamLevel;
  remoteOnly: boolean;
  minSalary: number | null;
  currency: JobCurrency;
  level: JobLevel;
  years: ExpYears;
  lang: JobLang;
  workplace: WorkplaceKind[];
  countries: string[];
  sort: JobSort;
}

export interface Stats {
  total: number;
  safe: number;
  suspicious: number;
  scam: number;
  by_source: Record<string, number>;
}

export interface ScrapeReport {
  status: string;
  total_new?: number;
  per_source?: Record<string, { fetched: number; new: number; duplicates: number; error: string | null }>;
}

export interface SettingKey {
  name: string;
  label: string;
  hint: string;
  /** masked in GET; non-secret values (e.g. adzuna country) come back plain */
  secret: boolean;
  set: boolean;
  /** "db" = saved via admin panel; "env" = fallback from .env */
  origin: string;
  /** stored value — prefilled into the input (admin-only endpoint) */
  value: string | null;
  masked: string | null;
}

export interface AppSettings {
  keys: SettingKey[];
  /** key-gated sources and whether their credentials are complete */
  sources: Record<string, boolean>;
}
