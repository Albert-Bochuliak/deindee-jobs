import { Loader2, MapPin, Play } from "lucide-react";
import { CheckboxDropdown } from "./ui/CheckboxDropdown";
import { ClearableInput } from "./ui/ClearableInput";
import type { useScrape } from "../hooks/useScrape";

const REGION_PRESETS = [
  "Ukraine", "Europe", "United States", "Canada",
  "Latin America", "Asia", "Australia", "New Zealand",
];

interface Props {
  scrape: ReturnType<typeof useScrape>;
  remoteOnly: boolean;
  /** push keywords into the jobs search box when a run starts */
  applyQuery: (q: string) => void;
  /** side-effect on every location toggle (e.g. sync the countries filter) */
  onLocations?: (locs: string[]) => void;
  reload: (opts?: { silent?: boolean }) => Promise<void>;
}

/** Header scrape controls: keywords input, location multi-select, run button. */
export function ScrapeBar({ scrape, remoteOnly, applyQuery, onLocations, reload }: Props) {
  const { keywords, setKeywords, locations, setLocations, scraping, start } =
    scrape;
  const run = () => {
    if (!scraping) start({ remoteOnly, applyQuery, reload });
  };
  return (
    <>
      <ClearableInput
        wrapperClassName="w-64"
        className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-600"
        placeholder="Ключові слова (напр. python)"
        value={keywords}
        onClear={() => setKeywords("")}
        onChange={(e) => setKeywords(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && run()}
      />
      <CheckboxDropdown
        className="w-44"
        icon={<MapPin size={15} className="shrink-0 text-slate-500" />}
        label={locations.length ? locations.join(", ") : "Де шукати…"}
        options={REGION_PRESETS}
        selected={locations}
        onChange={(locs) => {
          setLocations(locs);
          onLocations?.(locs);
        }}
      />
      <button
        onClick={run}
        disabled={scraping}
        className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
      >
        {scraping ? (
          <Loader2 size={16} className="animate-spin" />
        ) : (
          <Play size={16} />
        )}
        Запустити скрапінг
      </button>
    </>
  );
}
