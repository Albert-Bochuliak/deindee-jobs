import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  LogOut,
  X,
  XCircle,
} from "lucide-react";
import {
  adminChangePassword,
  adminLogin,
  adminLogout,
  ApiError,
  fetchSettings,
  saveSettings,
} from "../api/client";
import type { AppSettings } from "../types/job";

const SOURCE_LABELS: Record<string, string> = {
  jooble: "Jooble",
  adzuna: "Adzuna",
  usajobs: "USAJOBS",
};

const INPUT =
  "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-sky-600";

const is401 = (e: unknown) => e instanceof ApiError && e.status === 401;

/** saved values -> prefilled inputs */
const fillDraft = (s: AppSettings) =>
  Object.fromEntries(s.keys.map((k) => [k.name, k.value ?? ""]));

/** /admin — login-gated page for API credentials. Session is an
 *  HttpOnly cookie set by /api/admin/login. */
type AdminTab = "keys" | "password";

export function AdminPage() {
  const [authed, setAuthed] = useState<boolean | null>(null); // null = probing
  const [tab, setTab] = useState<AdminTab>("keys");
  // stable callbacks — unstable props would refire CredentialsCard's fetch effect
  const authFail = useCallback(() => setAuthed(false), []);
  const logout = useCallback(
    () => void adminLogout().finally(() => setAuthed(false)),
    []
  );

  // session probe: valid cookie -> credentials card, 401/offline -> login
  useEffect(() => {
    fetchSettings()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false));
  }, []);
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/60">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-4">
          <Lock size={18} className="text-sky-400" />
          <h1 className="text-lg font-semibold">Адмінка</h1>
          {authed && (
            <button
              onClick={logout}
              className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-300 hover:border-red-700 hover:text-red-300"
            >
              <LogOut size={14} /> Вийти
            </button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-10">
        {authed === null && (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="animate-spin" />
          </div>
        )}
        {authed === false && <LoginCard onOk={() => setAuthed(true)} />}
        {authed && (
          <>
            <div className="mb-5 flex gap-2">
              {(
                [
                  ["keys", "API ключі"],
                  ["password", "Пароль"],
                ] as [AdminTab, string][]
              ).map(([t, label]) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`rounded-lg border px-4 py-1.5 text-sm ${
                    tab === t
                      ? "border-sky-600 bg-sky-900/40 text-sky-300"
                      : "border-slate-700 bg-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            {tab === "keys" ? (
              <CredentialsCard onAuthFail={authFail} />
            ) : (
              <PasswordCard onAuthFail={authFail} />
            )}
          </>
        )}
      </main>
    </div>
  );
}

function LoginCard({ onOk }: { onOk: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminLogin(username, password);
      onOk();
    } catch (err) {
      setError(
        is401(err)
          ? "Невірний логін або пароль"
          : err instanceof ApiError && err.status === 403
            ? "Адмінку вимкнено — задайте ADMIN_PASSWORD у .env"
            : "Помилка з'єднання з API"
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="mx-auto max-w-sm space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6"
    >
      <h2 className="text-base font-semibold">Вхід</h2>
      <input
        className={INPUT}
        placeholder="Логін"
        value={username}
        autoComplete="username"
        onChange={(e) => setUsername(e.target.value)}
      />
      <div className="relative">
        <input
          className={`${INPUT} pr-9`}
          type={showPass ? "text" : "password"}
          placeholder="Пароль"
          value={password}
          autoComplete="current-password"
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          type="button"
          tabIndex={-1}
          aria-label={showPass ? "Сховати пароль" : "Показати пароль"}
          onClick={() => setShowPass((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:bg-slate-700 hover:text-slate-200"
        >
          {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
      {error && (
        <div className="rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      <button
        type="submit"
        disabled={busy || !username || !password}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
      >
        {busy && <Loader2 size={14} className="animate-spin" />}
        Увійти
      </button>
    </form>
  );
}

/** Small password input — each field owns its show/hide state. */
function PassField({
  label,
  value,
  onChange,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label className="mb-1 block text-xs text-slate-400">{label}</label>
      <div className="relative">
        <input
          className={`${INPUT} pr-9`}
          type={show ? "text" : "password"}
          value={value}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          tabIndex={-1}
          aria-label={show ? "Сховати" : "Показати"}
          onClick={() => setShow((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:bg-slate-700 hover:text-slate-200"
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
    </div>
  );
}

function PasswordCard({ onAuthFail }: { onAuthFail: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      setError("Новий пароль і підтвердження не збігаються");
      return;
    }
    setBusy(true);
    setError(null);
    setOk(false);
    try {
      await adminChangePassword(current, next);
      setOk(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      if (is401(err)) onAuthFail();
      else setError(err instanceof Error ? err.message : "Помилка");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="mx-auto max-w-sm space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6"
    >
      <h2 className="text-base font-semibold">Змінити пароль</h2>
      <PassField
        label="Поточний пароль"
        value={current}
        onChange={setCurrent}
        autoComplete="current-password"
      />
      <PassField
        label="Новий пароль (мін. 8 символів)"
        value={next}
        onChange={setNext}
        autoComplete="new-password"
      />
      <PassField
        label="Повторіть новий пароль"
        value={confirm}
        onChange={setConfirm}
        autoComplete="new-password"
      />
      {error && (
        <div className="rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      {ok && !error && (
        <div className="text-sm text-emerald-400">
          Пароль змінено — записано в базу даних.
        </div>
      )}
      <button
        type="submit"
        disabled={busy || !current || !next || !confirm}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
      >
        {busy && <Loader2 size={14} className="animate-spin" />}
        Змінити пароль
      </button>
    </form>
  );
}

function CredentialsCard({ onAuthFail }: { onAuthFail: () => void }) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [cleared, setCleared] = useState<Set<string>>(new Set());
  const [hidden, setHidden] = useState<Set<string>>(new Set()); // keys shown as dots
  const [busy, setBusy] = useState<"load" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setBusy("load");
    fetchSettings()
      .then((s) => {
        setSettings(s);
        setDraft(fillDraft(s));
      })
      .catch((e) => {
        if (is401(e)) onAuthFail();
        else setError(e instanceof Error ? e.message : "Помилка");
      })
      .finally(() => setBusy(null));
  }, [onAuthFail]);

  const dirty =
    cleared.size > 0 ||
    (settings?.keys.some(
      (k) => (draft[k.name] ?? "") !== (k.value ?? "")
    ) ??
      false);

  const save = async () => {
    setBusy("save");
    setError(null);
    try {
      // send only what actually changed; cleared keys go as ""
      const values: Record<string, string> = {};
      for (const k of settings?.keys ?? []) {
        if (cleared.has(k.name)) values[k.name] = "";
        else if ((draft[k.name] ?? "") !== (k.value ?? ""))
          values[k.name] = draft[k.name] ?? "";
      }
      const next = await saveSettings(values);
      setSettings(next);
      setDraft(fillDraft(next));
      setCleared(new Set());
      setSaved(true);
    } catch (e) {
      if (is401(e)) onAuthFail();
      else setError(e instanceof Error ? e.message : "Помилка збереження");
    } finally {
      setBusy(null);
    }
  };

  const markClear = (name: string) =>
    setCleared((s) => new Set(s).add(name));
  const undoClear = (name: string) =>
    setCleared((s) => {
      const next = new Set(s);
      next.delete(name);
      return next;
    });
  const toggleHidden = (name: string) =>
    setHidden((s) => {
      const next = new Set(s);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  if (busy === "load")
    return (
      <div className="flex justify-center py-16 text-slate-400">
        <Loader2 className="animate-spin" />
      </div>
    );

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      {settings && (
        <div className="mb-5 flex flex-wrap gap-2 text-xs">
          {Object.entries(SOURCE_LABELS).map(([key, label]) => {
            const enabled = settings.sources[key];
            return (
              <span
                key={key}
                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 ${
                  enabled
                    ? "border-emerald-700 bg-emerald-900/40 text-emerald-300"
                    : "border-slate-700 bg-slate-800 text-slate-400"
                }`}
              >
                {enabled ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                {label}
              </span>
            );
          })}
        </div>
      )}

      {settings && (
        <div className="space-y-3">
          {settings.keys.map((k) => {
            const isCleared = cleared.has(k.name);
            return (
              <div key={k.name}>
                <label className="mb-1 flex items-center justify-between text-xs text-slate-400">
                  <span>
                    {k.label}
                    <span className="ml-2 text-slate-600">{k.hint}</span>
                  </span>
                  <span
                    className={
                      k.set && !isCleared ? "text-emerald-400" : "text-slate-500"
                    }
                  >
                    {isCleared
                      ? "буде очищено"
                      : k.set
                        ? "задано"
                        : "не задано"}
                  </span>
                </label>
                <div className="relative">
                  <input
                    type={hidden.has(k.name) ? "password" : "text"}
                    className={`${INPUT} pr-16 ${
                      isCleared ? "opacity-40 line-through" : ""
                    }`}
                    placeholder={
                      k.set ? "Введіть нове значення…" : "Вставте ключ…"
                    }
                    value={draft[k.name] ?? ""}
                    disabled={isCleared}
                    autoComplete="off"
                    spellCheck={false}
                    onChange={(e) => {
                      setDraft((d) => ({ ...d, [k.name]: e.target.value }));
                      setSaved(false);
                    }}
                  />
                  <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 gap-1">
                    <button
                      type="button"
                      tabIndex={-1}
                      aria-label={hidden.has(k.name) ? "Показати" : "Сховати"}
                      title={hidden.has(k.name) ? "Показати" : "Сховати крапками"}
                      onClick={() => toggleHidden(k.name)}
                      className="rounded p-1 text-slate-500 hover:bg-slate-700 hover:text-slate-200"
                    >
                      {hidden.has(k.name) ? (
                        <Eye size={14} />
                      ) : (
                        <EyeOff size={14} />
                      )}
                    </button>
                    {k.set &&
                      (isCleared ? (
                        <button
                          type="button"
                          onClick={() => undoClear(k.name)}
                          className="rounded px-1.5 py-1 text-xs text-sky-400 hover:bg-slate-700"
                        >
                          назад
                        </button>
                      ) : (
                        <button
                          type="button"
                          aria-label="Очистити ключ"
                          title="Очистити ключ"
                          onClick={() => markClear(k.name)}
                          className="rounded p-1 text-slate-500 hover:bg-slate-700 hover:text-red-300"
                        >
                          <X size={14} />
                        </button>
                      ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {error && (
        <div className="mt-3 rounded-lg border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      {saved && !error && (
        <div className="mt-3 text-sm text-emerald-400">
          Збережено — джерела оновлено без перезапуску.
        </div>
      )}

      <div className="mt-5 flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          Ключі зберігаються в базі даних (jobs.db) — .env лише фолбек.
        </p>
        <button
          onClick={save}
          disabled={!dirty || busy === "save"}
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
        >
          {busy === "save" && <Loader2 size={14} className="animate-spin" />}
          Зберегти
        </button>
      </div>
    </div>
  );
}
