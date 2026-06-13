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
  /** Source/adapter that produced this record (e.g. "remoteok", "12twenty"). */
  source_adapter?: string;
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

// ── Application tracker ──────────────────────────────────────────────────────

export type ApplicationStage =
  | "saved"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected"
  | "archived";

export interface Application {
  id: string;
  title: string;
  employer: string;
  location: string;
  url: string;
  source: string;
  stage: ApplicationStage;
  salary: string;
  applied_date: string;
  deadline: string;
  notes: string;
  posting_id: string | null;
  resume_document_id: string | null;
  created_at: string;
  updated_at: string;
  raw_data: Record<string, unknown>;
}

export interface ApplicationCreateBody {
  posting_id?: string;
  title?: string;
  employer?: string;
  location?: string;
  url?: string;
  source?: string;
  stage?: ApplicationStage;
  salary?: string;
  applied_date?: string;
  deadline?: string;
  notes?: string;
  resume_document_id?: string | null;
}

export interface ApplicationPatch {
  stage?: ApplicationStage;
  notes?: string;
  applied_date?: string;
  deadline?: string;
  salary?: string;
  resume_document_id?: string | null;
  title?: string;
  employer?: string;
  location?: string;
  url?: string;
  source?: string;
}

export type DocumentKind = "resume" | "cover_letter";

export interface GeneratedDocument {
  id: string;
  kind: DocumentKind;
  label: string;
  title: string;
  employer: string;
  file_path: string;
  tex_path: string | null;
  ats_score: number | null;
  provider: string;
  tailored: boolean;
  job_snippet: string;
  application_id: string | null;
  posting_id: string | null;
  created_at: string;
  raw_data: Record<string, unknown>;
}

/** List applications, optionally filtered by stage. */
export function getApplications(
  stage?: ApplicationStage,
  limit = 200,
): Promise<Application[]> {
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  params.set("limit", String(limit));
  return getJSON<Application[]>(`/api/applications?${params}`, []);
}

/** Create a new tracked application (from a posting or manually). */
export async function createApplication(body: ApplicationCreateBody): Promise<Application | null> {
  try {
    const res = await fetch(`${API_BASE}/api/applications`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as Application;
  } catch {
    return null;
  }
}

/** Fetch a single application by id. */
export function getApplication(id: string): Promise<Application | null> {
  return getJSON<Application | null>(`/api/applications/${encodeURIComponent(id)}`, null);
}

/** Partially update a tracked application. */
export async function updateApplication(
  id: string,
  patch: ApplicationPatch,
): Promise<Application | null> {
  try {
    const res = await fetch(`${API_BASE}/api/applications/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(patch),
    });
    if (!res.ok) return null;
    return (await res.json()) as Application;
  } catch {
    return null;
  }
}

/** Delete a tracked application. Returns true on success. */
export async function deleteApplication(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/applications/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** Count of applications per stage plus total. */
export function getApplicationStats(): Promise<Record<string, number>> {
  return getJSON<Record<string, number>>("/api/applications/stats", {});
}

/** List generated documents, optionally filtered by kind. */
export function getDocuments(kind?: DocumentKind, limit = 200): Promise<GeneratedDocument[]> {
  const params = new URLSearchParams();
  if (kind) params.set("kind", kind);
  params.set("limit", String(limit));
  return getJSON<GeneratedDocument[]>(`/api/documents?${params}`, []);
}

/** Return the URL that serves the PDF file for a document. */
export function documentFileUrl(id: string): string {
  return `${API_BASE}/api/documents/${encodeURIComponent(id)}/file`;
}

/** Delete a generated document record (and its file on disk). Returns true on success. */
export async function deleteDocument(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ── Job Sources ───────────────────────────────────────────────────────────────

export interface JobQuery {
  keywords?: string;
  location?: string;
  remote?: boolean | null;
  job_type?: string;
  salary_min?: number | null;
  date_posted_days?: number | null;
  radius_km?: number | null;
  seniority?: string;
  company?: string;
  limit?: number;
  /** Restrict search to these source IDs only. */
  sources?: string[];
}

export interface JobSourceStatus {
  id: string;
  label: string;
  enabled: boolean;
  requires_key: boolean;
  is_scraper: boolean;
  configured: boolean;
  homepage: string;
}

export interface SourceError {
  source: string;
  detail: string;
}

export interface SearchResponse {
  results: JobPosting[];
  errors: SourceError[];
  counts: Record<string, number>;
}

export interface SourceConfigKeys {
  ADZUNA_APP_ID?: string;
  ADZUNA_APP_KEY?: string;
  ADZUNA_COUNTRY?: string;
  USAJOBS_API_KEY?: string;
  USAJOBS_EMAIL?: string;
  THEMUSE_API_KEY?: string;
}

export interface SourceConfigBody {
  enabled_sources?: string[];
  keys?: SourceConfigKeys;
}

/** List all known job sources with their configuration status. */
export function getSources(): Promise<{ sources: JobSourceStatus[] } | null> {
  return getJSON<{ sources: JobSourceStatus[] } | null>("/api/sources", null);
}

/**
 * Update enabled sources and/or API keys.
 * Raw keys are never returned — response contains configured booleans only.
 */
export async function updateSourcesConfig(
  body: SourceConfigBody,
): Promise<{ sources: JobSourceStatus[] } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/sources/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as { sources: JobSourceStatus[] };
  } catch {
    return null;
  }
}

/** Search for jobs across enabled (or specified) sources. Results are ephemeral. */
export async function searchJobs(query: JobQuery): Promise<SearchResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/sources/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(query),
    });
    if (!res.ok) return null;
    return (await res.json()) as SearchResponse;
  } catch {
    return null;
  }
}

/**
 * Fetch all current openings from a company's public ATS board.
 * @param ats  One of "greenhouse", "lever", "ashby".
 * @param slug The company slug (e.g. "stripe", "linear").
 */
export async function fetchCompanyBoard(
  ats: string,
  slug: string,
): Promise<{ results: JobPosting[] } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/sources/company`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ ats, slug }),
    });
    if (!res.ok) return null;
    return (await res.json()) as { results: JobPosting[] };
  } catch {
    return null;
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
