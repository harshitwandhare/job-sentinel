# ADR 006 — AI personalization, data governance, and the infra we deliberately skip

**Status:** Accepted · **Date:** 2026-06-14 · **Owner:** Harshit Wandhare

## Context

The profile, every generated résumé/cover letter, the application pipeline, and
tracked postings are now first-class local data. A natural next step is "make the
local model smarter about *me*." The obvious-but-wrong instinct is to fine-tune a
local model on this personal corpus, and to reach for heavyweight infra
(vector DB, knowledge graph, Redis, Kafka) to support it. This ADR records what we
do instead, and why.

## Decision

### 1. Personalize with RAG, not fine-tuning (for facts)

Use **retrieval-augmented generation** over the user's own data — profile,
generated documents, tracked jobs, applications — as the personalization
mechanism. Fine-tuning is explicitly **not** used to teach the model personal
facts.

Why:

- **Privacy & right-to-erasure.** RAG keeps personal data in a file/index the
  user can read, diff, and delete. Fine-tuning bakes it irreversibly into model
  weights — incompatible with our local-first, deletable-by-design promise and
  with GDPR/CCPA erasure expectations.
- **Freshness.** The corpus changes constantly (new applications, new tailored
  résumés). RAG reflects edits immediately; fine-tuning would need a retrain per
  change.
- **Accuracy.** RAG grounds answers in retrieved source text, reducing
  fabrication — which aligns with the existing no-fabrication tailoring contract.
  Fine-tuning on a tiny personal corpus risks overfitting and hallucination.
- **Cost & footprint.** RAG needs only embeddings we already produce; fine-tuning
  needs GPU time and per-user artifacts.

Industry guidance is consistent: RAG for injecting proprietary/personal
knowledge, fine-tuning for changing *style/behavior*. The only place fine-tuning
could earn its keep here is teaching the model the user's **writing voice**
(a future, optional LoRA over the user's own bullet phrasings) — never for facts.
That stays a deferred experiment, not a dependency.

### 2. The vector store is SQLite — no dedicated vector DB

The personal corpus is small (hundreds–thousands of chunks). Store embeddings in
the existing SQLite database (via `sqlite-vec`/`sqlite-vss` or plain
cosine-similarity over a loaded matrix). A hosted vector DB (Pinecone, Weaviate)
or even a local server (Qdrant, Chroma server) is unjustified at single-user
scale and would violate the zero-ops, local-first principle.

### 3. No knowledge graph / graph DB

The structured `profile.yaml` plus simple derived skill↔experience↔posting
relations already give us explainable matching. A dedicated graph database
(Neo4j) adds ops and cognitive load for marginal benefit. If richer relations are
ever needed, derive them in SQLite first.

### 4. Still no Redis / Kafka / Kubernetes

Unchanged from [NORTH_STAR §4](../NORTH_STAR.md): a single-user, local, poll-based
app has no shared cross-process cache, no streaming fan-out, and no fleet.
Adding them now is cosplay, not architecture. The seams (repository layer,
provider/source interfaces) keep the migration path open if a hosted multi-user
tier ever makes them real constraints.

### 5. Data governance: versioned and auditable

Personal/career data is treated as a first-class, auditable asset:

- **Versioning.** `profile.yaml` is diffable and belongs in the user's own git
  (it is gitignored from *this* repo). Generated documents are immutable rows in
  `generated_documents` with provenance (source profile snapshot reference, the
  JD used, ATS score, the model/provider that produced them, timestamp).
- **Provenance on every AI artifact.** We already record which provider/model
  generated each document and whether AI rephrasing was used — so any output can
  be traced and reproduced.
- **Deletability.** Every entity has a delete path (CLI + API + UI). Nothing is
  silently retained; nothing leaves the machine unless the user configures a BYO
  cloud provider.

## Consequences

- A small **RAG retrieval layer** over the local corpus is the next AI building
  block (powers the AI profile↔job match and a grounded assistant), reusing the
  existing embeddings backend — no new heavy dependency.
- Personalization improves continuously as the user's data grows, with zero
  retraining and full deletability.
- We can credibly claim "your data is never baked into a model and never leaves
  your machine" — a differentiator no fine-tuning-based competitor can match.

## Compliance note

Job Sentinel is a **candidate-side** assistant: it helps a job seeker organize
their own search and tailor their own documents. It is **not** an Automated
Employment Decision Tool — it does not screen, score, rank, or filter *other*
applicants on an employer's behalf. NYC Local Law 144 and the EU AI Act's
high-risk employment provisions target employers/vendors of AEDTs, so those
obligations do not attach to this tool. Our actual duties are data-protection
(GDPR/CCPA — satisfied by local-first storage + deletability) and basic AI
transparency (we disclose when output is AI-generated and never fabricate).
See [`docs/compliance.md`](../compliance.md).
