/** Safe localStorage wrappers: reads return null when storage is
 *  unavailable (privacy mode) or JSON is corrupt; write errors surface
 *  as console warnings instead of crashing — or vanishing silently. */

export function storageRead(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // storage disabled entirely (privacy mode, iframe)
  }
}

export function storageReadJSON<T>(key: string): T | null {
  const raw = storageRead(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch (e) {
    console.warn(`[storage] corrupt JSON in "${key}" — using defaults`, e);
    return null;
  }
}

export function storageWrite(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    // QuotaExceeded / SecurityError — data loss deserves a trace
    console.warn(`[storage] set "${key}" failed:`, e);
  }
}
