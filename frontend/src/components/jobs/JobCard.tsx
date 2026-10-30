import { Building2, ExternalLink, MapPin, Wifi } from "lucide-react";
import type { Job } from "../../types/job";
import { Badge } from "../ui/Badge";
import { ScoreBadge } from "../ui/ScoreBadge";

function formatSalary(job: Job): string | null {
  if (job.salary_min == null && job.salary_max == null) return null;
  const cur = job.currency ?? "";
  if (job.salary_min === job.salary_max) return `${job.salary_min} ${cur}`;
  const lo = job.salary_min != null ? `${job.salary_min}` : "?";
  const hi = job.salary_max != null ? `${job.salary_max}` : "?";
  return `${lo}–${hi} ${cur}`;
}

/** Rule-key prefix -> Ukrainian label for scam_reason strings stored as "key: detail". */
const REASON_MAP: [RegExp, (detail: string) => string][] = [
  [/^missing_company: no company name$/, () => "Немає назви компанії"],
  [/^missing_company: vague company '(.*)'$/, (d) => `Розмита назва компанії: ${d}`],
  [/^missing_company: /, () => "Немає назви компанії"],
  [/^(payment_demand|asks for payment): /, (d) => `Просять оплату: ${d}`],
  [/^(messenger_contact): /, () => "Контакт лише через месенджер, без сайту"],
  [/^unrealistic_salary: /, (d) => `Нереалістична зарплата: ${d}`],
  [/^urgency_pressure: /, () => "Тиск терміновості"],
  [/^vague_role: /, () => "Розпливчата / надто гарна вакансія"],
  [/^mlm_pattern: /, () => "Ознаки MLM / піраміди"],
  [/^(blacklist|company_blacklist): /, (d) => `Компанія у чорному списку${d ? ": " + d : ""}`],
  [/^(free_email|free_email_domain): /, (d) => `Безкоштовна пошта${d ? ": " + d : ""}`],
  [/^shouty_text: /, () => "Крикливий текст (CAPS, емодзі, !!!)"],
];

function humanizeReason(raw: string): string {
  for (const [re, fmt] of REASON_MAP) {
    const m = re.exec(raw);
    if (m) return fmt(m[1] ?? "");
  }
  return raw;
}

// Old scraped rows sometimes stored "90 000 грн.Договірна" as company — hide it.
const META_RE = /грн|договірн|зарплат|\d[\d\s]*\s*(?:UAH|USD|EUR|\$|€)/i;

const MISSING_COMPANY_UA = "Немає назви компанії";

export function JobCard({ job }: { job: Job }) {
  const salary = formatSalary(job);
  const company = job.company && !META_RE.test(job.company) ? job.company : null;
  const snippet = job.description.slice(0, 220);
  const reasons = job.scam_reasons.map(humanizeReason);
  // sanitized-away company (old "90 000 грн." garbage) still means no company
  if (!company && !reasons.some((r) => r.startsWith(MISSING_COMPANY_UA) || r.startsWith("Розмита назва"))) {
    reasons.unshift(MISSING_COMPANY_UA);
  }
  return (
    <article className="animate-fade-in flex h-full min-h-[270px] flex-col rounded-xl border border-slate-800 bg-slate-900 p-4 transition hover:border-slate-600">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold leading-snug text-slate-100">
          <a href={job.url} target="_blank" rel="noreferrer" className="hover:text-sky-400">
            {job.title}
          </a>
        </h3>
        <ScoreBadge score={job.scam_score} />
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-400">
        {company && (
          <span className="inline-flex items-center gap-1">
            <Building2 size={14} /> {company}
          </span>
        )}
        {job.location && (
          <span className="inline-flex items-center gap-1">
            <MapPin size={14} /> {job.location}
          </span>
        )}
      </div>

      {snippet && (
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          {snippet}
          {job.description.length > 220 ? "…" : ""}
        </p>
      )}

      <div className="mt-auto pt-4">
      {reasons.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {reasons.map((r, i) => (
            <Badge key={i} tone="yellow">{r}</Badge>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="blue">{job.source}</Badge>
        {job.remote && (
          <Badge tone="gray">
            <Wifi size={12} /> remote
          </Badge>
        )}
        {salary && <Badge tone="green">{salary}</Badge>}
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          className="ml-auto inline-flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300"
        >
          Відкрити <ExternalLink size={12} />
        </a>
      </div>
      </div>
    </article>
  );
}
