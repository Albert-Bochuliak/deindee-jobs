import { useEffect, useState } from "react";
import { fetchScrapeStatus, runScrape, stopScrape } from "../api/client";
import { storageRead, storageReadJSON, storageWrite } from "../utils/storage";

const POLL_MS = 1500;
const KEY_KEYWORDS = "scrapeKeywords";
const KEY_LOCATIONS = "scrapeLocations";
const KEY_LOCATIONS_LEGACY = "scrapeLocation"; // pre-multi-select key

interface RunDeps {
  remoteOnly: boolean;
  reload: (opts?: { silent?: boolean; append?: boolean }) => Promise<void>;
  /** wipe the visible list — a new run starts from an empty board */
  clear: () => void;
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
): Promise<{ new: number; stopped: boolean }> {
  let st = { running: true, new: 0, stopped: false };
  while (st.running) {
    await new Promise((r) => setTimeout(r, POLL_MS));
    st = await fetchScrapeStatus()
      .then((s) => ({ stopped: false, ...s }))
      .catch(() => ({ running: false, new: 0, stopped: false }));
    // append: cards keep their place, fresh arrivals land at the end —
    // no grid reshuffle on every tick
    await reload({ silent: true, append: true });
    onProgress(`Скрапінг… знайдено нових: ${st.new}`);
  }
  return { new: st.new, stopped: st.stopped };
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
  const start = async ({ remoteOnly, reload, clear }: RunDeps) => {
    setScraping(true);
    setMsg(null);
    try {
      const started = await runScrape(keywords, remoteOnly, locations.join(","));
      if (started.status === "already_running") {
        setMsg("Скрапінг уже виконується…");
      } else {
        clear(); // fresh run — old cards go away, new ones stream in via polling
      }
      const last = await pollUntilDone(reload, setMsg);
      // canonical relevance sort applies ONCE at the end — direct title
      // matches lead, fuzzy matches tail behind
      await reload({ silent: true });
      setMsg(
        last.stopped
          ? `Зупинено: +${last.new} нових вакансій`
          : `Готово: +${last.new} нових вакансій`
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Помилка скрапінгу");
    } finally {
      setScraping(false);
    }
  };

  /** Cooperative stop — saved jobs stay; the poll loop exits on its own. */
  const stop = () => {
    stopScrape().catch(() => undefined);
    // instant visual feedback — don't wait ~1 poll cycle for running=false
    setScraping(false);
    setMsg("Зупиняю скрапінг…");
  };

  return { keywords, setKeywords, locations, setLocations, scraping, msg, start, stop };
}
