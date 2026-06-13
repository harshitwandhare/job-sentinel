# AI providers (bring your own key)

Job Sentinel uses a local [Ollama](https://ollama.com) instance by default — pull a model once and everything runs fully offline, no accounts or API keys required. If you want a larger model, faster inference, or a cloud fallback, you can point either the chat slot or the embeddings slot at any OpenAI-compatible provider.

---

## How it works

The backend maintains two independent **slots**:

| Slot | Used for |
|---|---|
| **chat** | Resume rephrasing and tailoring, cover letter generation, the chat assistant |
| **embed** | Semantic job search, similarity scoring between your profile and job postings |

Each slot has its own `provider`, `model`, `base_url`, and optionally an `api_key`. The two slots are independent — you can use Ollama for chat and Gemini for embeddings, or mix and match however you like.

---

## Default: Ollama (local, zero-config)

No key needed. [Install Ollama](https://ollama.com/download), pull a model, done:

```bash
ollama pull llama3.2:3b         # chat — 3B fits in 4 GB of VRAM
ollama pull nomic-embed-text    # embeddings
```

Ollama binds to `http://localhost:11434` by default. The sentinel picks it up automatically.

---

## Supported providers

| Provider | Free tier | Chat | Embeddings | Notes |
|---|---|---|---|---|
| **Ollama** | yes (local) | yes | yes | Default; no key, fully offline |
| **OpenRouter** | yes (free models) | yes | limited | Huge model catalogue; free tier via `:free` suffix |
| **Groq** | yes | yes | **no** | Fast inference, but no embeddings API |
| **Gemini** | yes (generous) | yes | yes | `text-embedding-004` is free and accurate |
| **OpenAI** | no (pay-as-you-go) | yes | yes | `gpt-4o-mini` / `text-embedding-3-small` |
| **Custom** | — | yes | yes | Any OpenAI-compatible endpoint |

> Groq does not expose an embeddings endpoint. If you use Groq for chat, pair it with Gemini or Ollama for embeddings.

---

## Configuration

### Via the Settings UI (recommended)

Open the web app at `http://localhost:3000/settings`. You will find:

- A **provider** dropdown for each slot (populated live from the running backend).
- A **model** field with per-provider placeholder hints.
- An **API key** field (password-masked; leaving it blank on save keeps the existing key).
- An optional **Base URL** override (only needed for `custom` or self-hosted proxies).
- **Quick-setup presets** that fill all fields for common setups in one click.
- A **Test connection** button per slot that pings the provider and reports latency.

Changes take effect immediately after clicking Save — no restart required.

### Via environment variables

Set these in your `.env` before starting `job-sentinel serve`:

```bash
# Chat slot
CHAT_PROVIDER=openrouter          # ollama | openai | openrouter | groq | gemini | custom
CHAT_MODEL=meta-llama/llama-3.3-70b-instruct:free
CHAT_API_KEY=sk-or-...
CHAT_BASE_URL=https://openrouter.ai/api/v1   # optional override

# Embeddings slot
EMBED_PROVIDER=gemini
EMBED_MODEL=text-embedding-004
EMBED_API_KEY=AIza...
EMBED_BASE_URL=                              # leave blank for provider default

# Shared
LLM_TIMEOUT=30                 # seconds per request (default 30)
LLM_GRACEFUL_DEGRADATION=true  # fall back to keyword matching if LLM is unreachable
```

Environment variables are the source of truth at startup. The Settings UI writes back to `.env` via the API; the running process picks up changes without a restart.

---

## Getting free API keys

### OpenRouter

1. Create an account at [openrouter.ai](https://openrouter.ai).
2. Go to **Keys** and generate a key.
3. Use any model with the `:free` suffix — e.g. `meta-llama/llama-3.3-70b-instruct:free`.

### Groq

1. Sign up at [console.groq.com](https://console.groq.com).
2. Go to **API Keys** and create one.
3. Recommended model: `llama-3.1-70b-versatile`.
4. Note: Groq has no embeddings API — pair it with Gemini or Ollama for the embed slot.

### Gemini

1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
2. Click **Create API key**.
3. Chat model: `gemini-2.5-flash`. Embed model: `text-embedding-004`.

### OpenAI

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Create a project key. Usage is pay-as-you-go (no free tier).
3. Chat model: `gpt-4o-mini`. Embed model: `text-embedding-3-small`.

---

## Graceful degradation

If the configured provider is unreachable and `LLM_GRACEFUL_DEGRADATION=true` (the default):

- **Chat**: returns an empty or rule-based response instead of an error.
- **Tailoring**: falls back to keyword-only reordering — no rephrasing, but the PDF still builds.
- **Embeddings**: semantic search is disabled; full-text search continues to work.

Set `LLM_GRACEFUL_DEGRADATION=false` if you want hard failures instead (useful in CI).

---

## Privacy and security

- API keys are stored only in `.env` on your machine. They are never logged, never sent to any service other than the provider you configure, and never included in bug reports or telemetry.
- The Settings UI masks keys after saving — they cannot be read back from the browser.
- Passing `api_key=""` in a PUT request clears the stored key.
- Nothing about your profile, job data, or resume is sent to a provider unless you explicitly trigger an AI action (tailor, build with `--ai`, cover letter, or chat).
