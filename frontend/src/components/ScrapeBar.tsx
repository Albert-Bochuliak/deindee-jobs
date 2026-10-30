import { MapPin, Play, Square } from "lucide-react";
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
  /** side-effect on every location toggle (e.g. sync the countries filter) */
  onLocations?: (locs: string[]) => void;
  reload: (opts?: { silent?: boolean }) => Promise<void>;
  /** wipe the visible list when a fresh run starts */
  clear: () => void;
}

/** Header scrape controls: keywords input, location multi-select, run button. */
export function ScrapeBar({ scrape, remoteOnly, onLocations, reload, clear }: Props) {
  const { keywords, setKeywords, locations, setLocations, scraping, start, stop } =
    scrape;
  const run = () => {
    if (!scraping) start({ remoteOnly, reload, clear });
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
        onClick={scraping ? stop : run}
        className={
          scraping
            ? "inline-flex items-center gap-2 rounded-lg bg-red-700 px-4 py-2 text-sm font-medium hover:bg-red-600"
            : "inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500"
        }
      >
        {scraping ? (
          <>
            <Square size={14} />
            Зупинити
          </>
        ) : (
          <>
            <Play size={16} />
            Запустити скрапінг
          </>
        )}
      </button>
    </>
  );
}
