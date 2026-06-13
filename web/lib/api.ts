/**
 * Typed client for the local Job Sentinel API (see src/job_sentinel/api/app.py).
 * Every call degrades gracefully: on any failure it returns a safe empty value
 * instead of throwing, so pages render an empty state rather than a crash.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export interface Link {
  label: string;
  url: string;
}
export interface Basics {
  name: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
  links: Link[];
  summary: string;
}
export interface Experience {
  company: string;
  role: string;
  location: string;
  start: string;
  end: string;
  bullets: string[];
  tags: string[];
}
export interface Project {
  name: string;
  description: string;
  url: string;
  bullets: string[];
  tags: string[];
}
export interface Education {
  institution: string;
  degree: string;
  location: string;
  start: string;
  end: string;
  gpa: string;
  highlights: string[];
}
export interface SkillGroup {
  category: string;
  skills: string[];
}
export interface Certification {
  name: string;
  issuer: string;
  date: string;
  tags?: string[];
}
export interface Award {
  title: string;
  issuer: string;
  date: string;
  description: string;
  tags?: string[];
}
export interface Publication {
  title: string;
  venue: string;
  date: string;
  url: string;
  tags?: string[];
}
export interface Profile {
  basics: Basics;
  education: Education[];
  experience: Experience[];
  projects: Project[];
  skills: SkillGroup[];
  certifications: Certification[];
  awards: Award[];
  publications: Publication[];
}
export interface JobDetail {
  description?: string;
  salary?: string;
  salary_min?: number | null;
  salary_max?: number | null;
  openings?: number | null;
  industry?: string;
  job_function?: string;
  work_study_required?: boolean | null;
  application_begins?: string | null;
  job_start_date?: string | null;
  application_documents?: string[];
  contact_name?: string | null;
  contact_title?: string | null;
  contact_email?: string | null;
  apply_via_site?: boolean | null;
  external_url?: string | null;
  num_applicants?: number | null;
  required_work_auth?: string | null;
  time_commitment?: string | null;
}
export interface JobPosting {
  posting_id: string;
  title: string;
  employer: string;
  location: string;
  job_type: string;
  posted_date: string;
  deadline: string;
  description_snippet: string;
  status: string;
  portal_url: string;
  raw_data?: { detail?: JobDetail; [key: string]: unknown };
}
export interface TailorResult {
  score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  profile: Profile;
}

const TOKEN_KEY = "sentinel_token";

/** Bearer-token header from localStorage (no-op during SSR / when logged out). */
function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function getJSON<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store", headers: authHeaders() });
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export function getProfile(): Promise<Profile | null> {
  return getJSON<Profile | null>("/api/profile", null);
}

export function getJobs(limit = 20): Promise<JobPosting[]> {
  return getJSON<JobPosting[]>(`/api/jobs?limit=${limit}`, []);
}

export async function tailorResume(jobDescription: string): Promise<TailorResult | null> {
  try {
    const res = await fetch(`${API_BASE}/api/resume/tailor`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ job_description: jobDescription }),
    });
    if (!res.ok) return null;
    return (await res.json()) as TailorResult;
  } catch {
    return null;
  }
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}
export interface ChatReply {
  reply: string;
  source: "rules" | "llm";
}

/** Ask the Sentinel assistant. Returns null on any transport failure. */
export async function sendChat(messages: ChatTurn[]): Promise<ChatReply | null> {
  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ messages }),
    });
    if (!res.ok) return null;
    return (await res.json()) as ChatReply;
  } catch {
    return null;
  }
}

/** Update a posting's tracking status. Returns true on success. */
export async function setJobStatus(postingId: string, status: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(postingId)}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ status }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export interface ImportResult {
  ok: boolean;
  profile?: Profile;
  detail?: string;
}

/** Upload a resume PDF and get back a parsed Profile draft (nothing is saved). */
export async function importResume(file: File, ai = true): Promise<ImportResult> {
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/profile/import-resume?ai=${ai}`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      return { ok: false, detail: body.detail ?? `Import failed (${res.status})` };
    }
    return { ok: true, profile: (await res.json()) as Profile };
  } catch {
    return { ok: false, detail: "Could not reach the API. Is `job-sentinel serve` running?" };
  }
}

/** Persist the full profile. Returns the saved (validated) profile, or null. */
export async function putProfile(profile: Profile): Promise<Profile | null> {
  try {
    const res = await fetch(`${API_BASE}/api/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(profile),
    });
    if (!res.ok) return null;
    return (await res.json()) as Profile;
  } catch {
    return null;
  }
}

export interface OpStatus {
  state: "idle" | "running" | "ok" | "error";
  message: string;
  started_at: string | null;
  finished_at: string | null;
  detail: Record<string, unknown>;
}
export interface OpsStatus {
  config_ok: boolean;
  config_error: string;
  session: { exists: boolean; saved_at: string | null };
  login: OpStatus;
  scrape: OpStatus;
  watcher: { running: boolean; interval_seconds: number | null };
  adapter: string | null;
  adapters: string[];
}
export interface LlmStatus {
  base_url: string;
  reachable: boolean;
  chat_model: string;
  chat_ready: boolean;
  embed_model: string;
  embed_ready: boolean;
}
export interface StartResult {
  ok: boolean;
  detail?: string;
}

/** Snapshot of session/login/scrape/watcher state. Null if the API is down. */
export function getOpsStatus(): Promise<OpsStatus | null> {
  return getJSON<OpsStatus | null>("/api/ops/status", null);
}

/** Counts per tracking status (db stats). */
export function getStats(): Promise<Record<string, number>> {
  return getJSON<Record<string, number>>("/api/stats", {});
}

/** Local-LLM health (resume doctor). */
export function getLlmStatus(): Promise<LlmStatus | null> {
  return getJSON<LlmStatus | null>("/api/llm/status", null);
}

async function postJSON(path: string, body: unknown): Promise<StartResult> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body ?? {}),
    });
    if (res.ok) return { ok: true };
    const data = (await res.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, detail: data.detail ?? `Request failed (${res.status})` };
  } catch {
    return { ok: false, detail: "Could not reach the API. Is `job-sentinel serve` running?" };
  }
}

/** Open the interactive portal login (a browser opens on the API machine). */
export function startLogin(timeout = 300): Promise<StartResult> {
  return postJSON("/api/ops/login", { timeout });
}

export interface SessionCheck {
  valid: boolean;
  user: string;
  detail: string;
  checked: boolean;
}

/** Headless probe: is the saved portal session still valid? Null = API down/conflict. */
export async function checkSession(): Promise<SessionCheck | null> {
  try {
    const res = await fetch(`${API_BASE}/api/ops/session/check`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) return null;
    return (await res.json()) as SessionCheck;
  } catch {
    return null;
  }
}

/** Run one scrape cycle. `send` actually sends alerts (default dry-run). */
export function startScrape(send = false): Promise<StartResult> {
  return postJSON("/api/ops/scrape", { send });
}

/** Start / stop the continuous watcher (scrape on an interval + alerts). */
export function startWatcher(): Promise<StartResult> {
  return postJSON("/api/ops/watcher/start", {});
}
export function stopWatcher(): Promise<StartResult> {
  return postJSON("/api/ops/watcher/stop", {});
}

// ── LLM provider config ──────────────────────────────────────────────────────

export interface LlmSlotConfig {
  provider: string;
  model: string;
  base_url: string;
  api_key_set: boolean;
  api_key_masked: string;
}

export interface LlmProviderInfo {
  id: string;
  label: string;
  default_base_url: string;
  requires_key: boolean;
  supports_embeddings: boolean;
}

export interface LlmConfig {
  chat: LlmSlotConfig;
  embed: LlmSlotConfig;
  providers: LlmProviderInfo[];
}

export interface LlmConfigBody {
  chat: { provider: string; model: string; base_url: string; api_key?: string };
  embed: { provider: string; model: string; base_url: string; api_key?: string };
}

export interface LlmTestResult {
  ok: boolean;
  detail: string;
  latency_ms: number | null;
}

/** Fetch the current LLM provider config (chat + embed). Returns null if the API is down. */
export function getLlmConfig(): Promise<LlmConfig | null> {
  return getJSON<LlmConfig | null>("/api/llm/config", null);
}

/**
 * Persist LLM provider config. Omit `api_key` to leave unchanged; pass `""` to clear.
 * Returns the updated masked config, or null on failure.
 */
export async function putLlmConfig(body: LlmConfigBody): Promise<LlmConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/llm/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as LlmConfig;
  } catch {
    return null;
  }
}

/** Probe a chat or embedding slot. Returns {ok:false} on any transport failure. */
export async function testLlm(target: "chat" | "embed"): Promise<LlmTestResult> {
  try {
    const res = await fetch(`${API_BASE}/api/llm/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ target }),
    });
    if (!res.ok) return { ok: false, detail: `Request failed (${res.status})`, latency_ms: null };
    return (await res.json()) as LlmTestResult;
  } catch {
    return { ok: false, detail: "Could not reach the API. Is `job-sentinel serve` running?", latency_ms: null };
  }
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  username: string;
  is_admin: boolean;
}
export interface AuthStatus {
  mode: "off" | "demo" | "required";
  users_exist: boolean;
  user: AuthUser | null;
}

/** Current auth mode and (if a valid token is held) the logged-in user. */
export function getAuthStatus(): Promise<AuthStatus | null> {
  return getJSON<AuthStatus | null>("/api/auth/status", null);
}

/** Log in; stores the token on success. */
export async function authLogin(
  username: string,
  password: string,
): Promise<{ ok: boolean; detail?: string; user?: AuthUser }> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = (await res.json().catch(() => ({}))) as {
      token?: string;
      user?: AuthUser;
      detail?: string;
    };
    if (!res.ok || !body.token) return { ok: false, detail: body.detail ?? "Login failed." };
    setAuthToken(body.token);
    return { ok: true, user: body.user };
  } catch {
    return { ok: false, detail: "Could not reach the API." };
  }
}

export function authLogout(): void {
  setAuthToken(null);
}

export interface BuildResult {
  ok: boolean;
  blob?: Blob;
  detail?: string;
}

/** Build a (optionally tailored / LLM) résumé PDF and return the bytes. */
export async function buildResume(jobDescription = "", ai = false): Promise<BuildResult> {
  try {
    const res = await fetch(`${API_BASE}/api/resume/build`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ job_description: jobDescription, ai }),
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      return { ok: false, detail: body.detail ?? `Build failed (${res.status})` };
    }
    return { ok: true, blob: await res.blob() };
  } catch (e) {
    return { ok: false, detail: String(e) };
  }
}

/** Build a cover-letter PDF and return the bytes. */
export async function buildCover(
  jobDescription = "",
  role = "",
  company = "",
  ai = false,
): Promise<BuildResult> {
  try {
    const res = await fetch(`${API_BASE}/api/resume/cover`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ job_description: jobDescription, role, company, ai }),
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      return { ok: false, detail: body.detail ?? `Build failed (${res.status})` };
    }
    return { ok: true, blob: await res.blob() };
  } catch (e) {
    return { ok: false, detail: String(e) };
  }
}
