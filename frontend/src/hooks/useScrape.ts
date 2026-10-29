import { useEffect, useState } from "react";
import { fetchScrapeStatus, runScrape } from "../api/client";
import { storageRead, storageReadJSON, storageWrite } from "../utils/storage";

const POLL_MS = 1500;
const KEY_KEYWORDS = "scrapeKeywords";
const KEY_LOCATIONS = "scrapeLocations";
const KEY_LOCATIONS_LEGACY = "scrapeLocation"; // pre-multi-select key

interface RunDeps {
  remoteOnly: boolean;
  /** push keywords into the jobs search box so fresh results are visible */
  applyQuery: (q: string) => void;
  reload: (opts?: { silent?: boolean }) => Promise<void>;
}

function loadLocations(): string[] {
  const saved = storageReadJSON<string[]>(KEY_LOCATIONS);
  if (saved) return saved;
  const legacy = storageRead(KEY_LOCATIONS_LEGACY);
  return legacy ? [legacy] : [];
}

/** Poll /scrape/status until done; silent-reloads so cards fade in as saved. */
async function pollUntilDone(
  reload: RunDeps["reload"],
  onProgress: (msg: string) => void
): Promise<number> {
  let st = { running: true, new: 0 };
  while (st.running) {
    await new Promise((r) => setTimeout(r, POLL_MS));
    st = await fetchScrapeStatus().catch(() => ({ running: false, new: 0 }));
    await reload({ silent: true });
    onProgress(`Скрапінг… знайдено нових: ${st.new}`);
  }
  return st.new;
}

/** Scrape form state + the run/poll loop. Persistence in localStorage. */
export function useScrape() {
  const [keywords, setKeywords] = useState(
    () => storageRead(KEY_KEYWORDS) ?? ""
  );
  const [locations, setLocations] = useState<string[]>(loadLocations);
  const [scraping, setScraping] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    storageWrite(KEY_KEYWORDS, keywords);
  }, [keywords]);
  useEffect(() => {
    storageWrite(KEY_LOCATIONS, JSON.stringify(locations));
  }, [locations]);

  /** POST /scrape, then poll /scrape/status and silently reload the list
   *  so new cards appear as they're saved, not all at the end. */
  const start = async ({ remoteOnly, applyQuery, reload }: RunDeps) => {
    setScraping(true);
    setMsg(null);
    try {
      const started = await runScrape(keywords, remoteOnly, locations.join(","));
      if (started.status === "already_running") {
        setMsg("Скрапінг уже виконується…");
      }
      if (keywords.trim()) {
        applyQuery(keywords.trim());
      }
      const total = await pollUntilDone(reload, setMsg);
      setMsg(`Готово: +${total} нових вакансій`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Помилка скрапінгу");
    } finally {
      setScraping(false);
    }
  };

  return { keywords, setKeywords, locations, setLocations, scraping, msg, start };
}
