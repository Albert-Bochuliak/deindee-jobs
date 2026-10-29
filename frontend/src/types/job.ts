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
