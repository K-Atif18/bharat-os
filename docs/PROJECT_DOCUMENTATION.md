# Bharat OS — Project Documentation

**Eligibility reasoning and application preparation for Indian government
funding schemes (startups & MSMEs).**

Bharat OS goes beyond scheme *discovery*. It tells a user **why** they qualify
(or don't) using a deterministic logic engine, sources every fact to a real
government URL, hedges every AI judgment with a confidence score, drafts an
application with per-field provenance, and reports honestly on its own accuracy.

| | |
|---|---|
| **Live website** | https://bharat-os-tawny.vercel.app |
| **Live API** | https://bharat-os-production.up.railway.app |
| **Interactive API docs** | https://bharat-os-production.up.railway.app/docs |
| **Corpus** | 40 real schemes, 21 authorities |

---

## 1. System Architecture

Bharat OS is a **modular monolith**: a Next.js frontend and a FastAPI backend,
with deterministic eligibility logic kept strictly separate from AI judgment.

```
Applicant ─┐
           ├─►  Next.js frontend  ──JSON + HttpOnly session cookie──►  FastAPI API
Reviewer ──┘        (Vercel)                                            (Railway)
                                                                          │
                          ┌───────────────────────────────────────────────┤
                          ▼                    ▼                    ▼
                 Deterministic          LLM provider          PostgreSQL
                 eligibility engine     adapter (mock/Gemini)  (Railway managed)
                          ▲
        Official pages/PDFs ─► Crawler / PDF pipeline ─► Pending revisions ─► Human reviewer
```

The browser never talks directly to the database, the LLM, or the crawler. The
API owns authentication, consent, rate limiting, and every response contract.

**Backend layers**
- **`engine/`** — Pure hard-rule evaluator. No FastAPI, SQLAlchemy, or network
  imports. Implements **Kleene three-valued logic**: every criterion resolves to
  `met` / `unmet` / `cannot_verify`. Missing data is *never* silently treated as
  a failure.
- **`llm/`** — Provider-neutral AI boundary: `MockProvider` (deterministic,
  offline) and `GeminiProvider` (`gemini-flash-latest`). The AI never evaluates
  hard rules and never publishes scheme data. Low-confidence judgments (< 0.6)
  are forced into human review. Every judgment stores a full audit trail
  (model, prompt, prompt version, confidence).
- **`services/`** — Use cases: ranking, deep-dive assembly, drafting, deadlines,
  outcome de-identification, calibration measurement, and a dependency-free
  retrieval (RAG) layer (keyword/overlap scoring — no vector DB).
- **`api/`** — Thin HTTP routers over the services. Shared dependencies enforce
  session validity, purpose-specific consent, and reviewer role.

**Tech stack**
- **Backend:** FastAPI, Python 3.11, SQLAlchemy 2, Pydantic v2, Alembic
- **Frontend:** Next.js 15, React 19, Tailwind CSS
- **Database:** PostgreSQL (SQLite for local dev)
- **AI:** provider-neutral adapter (mock by default, Gemini optional)
- **Hosting:** Frontend on Vercel, backend + PostgreSQL on Railway (Docker)

**Data-integrity & privacy invariants**
- Every eligibility criterion carries a real `source_url`; an unsourced claim is
  flagged (`source_quote: null`), never fabricated.
- Sensitive profile fields (exact turnover, social category) are **encrypted at
  rest** via Fernet (authenticated encryption: AES-128-CBC + HMAC-SHA256).
- Consent is **per-purpose** (DPDP Act–aligned); account **erasure** is a real
  API endpoint. Outcome records are **de-identified at capture** (turnover
  banded, no link to a person).

---

## 2. API Endpoints

Base URL: `https://bharat-os-production.up.railway.app`. JSON bodies use
snake_case. Auth is an opaque HttpOnly session cookie. Errors return
`{ "detail": ... }`. Status codes: `401` no session · `403` missing
consent/role · `404` not found · `409` conflict · `422` validation · `429`
rate-limited.

**Health & scheme corpus (public)**
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + DB reachability + scheme count |
| GET | `/schemes` | Scheme summaries (40 schemes) |
| GET | `/schemes/{slug}` | Sourced scheme detail |

**Authentication & account**
| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register` | Public | Create account + consents, issue session |
| POST | `/auth/login` | Public | Verify credentials, issue session |
| POST | `/auth/logout` | Session | Revoke session |
| GET | `/me` | Session | Account + consents + profile flag |
| POST | `/me/consents` | Session | Grant/withdraw one consent purpose |
| DELETE | `/me` | Session | Erase personal data, return receipt |

**Profile & matching**
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET / PUT | `/profile` | Session + consent | Business profile |
| GET | `/matches` | Session + consent | Ranked scheme feed (met/unmet/ruled-out) |
| GET | `/matches/{slug}/deep-dive` | Session + consent | Criterion-by-criterion breakdown |

**Drafts (application workspace)**
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/matches/draftable` | Public | Slugs that support drafting |
| POST | `/matches/{slug}/draft` | Session | Generate a new draft version (never overwrites) |
| GET | `/matches/{slug}/draft` | Session | Fetch current draft version |
| GET | `/matches/drafts/{id}/diff/{other_id}` | Session | Field-by-field diff between versions |

**Documents & deadlines**
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET / POST | `/documents` | Session + consent | Document vault metadata |
| DELETE | `/documents/{id}` | Session + consent | Remove a vault record |
| GET | `/matches/{slug}/documents` | Session + consent | Have/need/expired checklist |
| GET | `/deadlines` | Session + consent | Reachability-scored deadlines |
| GET | `/deadlines/calendar.ics` | Session + consent | `.ics` calendar export |

**Applications & outcomes**
| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/applications` | Session | List tracked applications |
| POST | `/matches/{slug}/applications` | Session | Start tracking an application |
| PATCH | `/applications/{id}` | Session | Record a status change |
| POST | `/applications/{id}/outcome` | Session + consent | Record an outcome (turnover banded) |
| GET | `/schemes/{slug}/outcome-stats` | Session | Aggregate de-identified stats |

**Trust & measurement (public — aggregate/catalogue data, not user data)**
| Method | Path | Purpose |
|---|---|---|
| GET | `/freshness/` · `/freshness/{slug}` | Data staleness report |
| GET | `/calibration/` | Expected Calibration Error + reliability buckets |
| GET | `/intelligence/{slug}` | Approval rate, rejection reasons, turnover-band split |

**Crawler & review queue (reviewer-only)**
| Method | Path | Purpose |
|---|---|---|
| POST | `/crawler/run` · GET `/crawler/sources` | Run/list monitored crawl sources |
| GET | `/review-queue` | Pending extraction revisions |
| POST | `/review-queue/{id}/approve` · `/reject` · `/annotate` | Human decision on a revision |

> The full, exact contract is the generated OpenAPI schema at `/docs`.

---

## 3. Setup Guide

**Prerequisites:** Python 3.11, Node.js 22, and PostgreSQL (or use SQLite for
local dev).

**Local development**
```bash
# 1. Configure
cp .env.example .env

# 2. Install backend + frontend dependencies
make install

# 3. Create the database schema and load the 40-scheme corpus
make migrate
make seed

# 4. Run (two terminals)
make dev-backend    # http://localhost:8000  (API + /docs)
make dev-frontend   # http://localhost:3000  (website)
```
Open `http://localhost:3000` and click **Launch live judge demo** for a
one-click provisioned account with real scheme matches.

**Key environment variables** (`BHARAT_OS_` prefix)
| Variable | Purpose |
|---|---|
| `BHARAT_OS_ENVIRONMENT` | `development` / `production` |
| `BHARAT_OS_DATABASE_URL` | Postgres URL (managed `postgres://` URLs auto-normalised) |
| `BHARAT_OS_ENCRYPTION_KEY` | Fernet key for field encryption (**required in production**) |
| `BHARAT_OS_CORS_ALLOWED_ORIGINS` | Allowed frontend origin(s), comma-separated |
| `BHARAT_OS_LLM_PROVIDER` | `mock` (offline) or `gemini` |
| `BHARAT_OS_GEMINI_API_KEY` / `_MODEL` | Gemini credentials (model: `gemini-flash-latest`) |

**Production deployment (as currently hosted)**
- **Backend + PostgreSQL → Railway.** Service root directory `backend`, builds
  from `backend/Dockerfile` (runs `alembic upgrade head` then uvicorn on boot).
  A managed PostgreSQL plugin supplies `${{Postgres.DATABASE_URL}}`. Schemes
  loaded once via the Railway console: `python -m bharat_os.seed.load`.
- **Frontend → Vercel.** Root directory `frontend` (auto-detected Next.js), with
  `NEXT_PUBLIC_API_BASE_URL` pointing at the Railway API URL.
- The backend's `CORS_ALLOWED_ORIGINS` is set to the Vercel origin, and the
  production session cookie uses `SameSite=None; Secure` so authentication works
  across the two hosted domains.

**Tests:** `make test` (backend + frontend). `make lint` for linters/type-checks.

---

## 4. Feature Breakdown

**Deterministic three-valued eligibility engine.** Hard criteria (turnover caps,
registration requirements, age limits) run through a real Kleene-logic engine:
`met` / `unmet` / `cannot_verify`. A single unmet hard criterion disqualifies;
missing data becomes `cannot_verify` (with the exact field named), never a false
rejection. Every verdict carries a plain-language reason.

**Sourced, honest scheme data.** All 40 schemes are validated against a strict
Pydantic schema before merge, each criterion carrying a real government
`source_url`. Where a verbatim quote couldn't be retrieved, the field is honestly
`null` — never fabricated.

**Hedged, audited AI judgments.** Subjective ("soft") criteria are judged by an
LLM that may only return `likely_met` / `likely_unmet` / `uncertain`, each with a
confidence score and reasoning. Confidence below 0.6 is forced into human review.
A dependency-free retrieval layer optionally grounds judgments in the scheme's own
text. Every judgment is fully auditable (model, prompt, prompt version, cache).

**Self-measuring calibration.** A live `/calibration` page computes Expected
Calibration Error and a reliability diagram measuring whether the AI's stated
confidence matches real outcomes — with a visible warning whenever the underlying
data is synthetic rather than real.

**Execution, not just discovery.** Per-scheme document-gap checklists
(have / need / expired), a deadline reachability calendar with `.ics` export, and
an editable draft application with **per-field provenance** (`profile` /
`ai-drafted` / `needs-you`). Drafts are versioned and never overwrite; nothing is
ever submitted on the user's behalf.

**Outcome intelligence.** An `/intelligence` panel aggregates de-identified
application outcomes — real approval rates, average days-to-decision, and ranked
rejection reasons per scheme — the ground truth a government portal never
publishes.

**Privacy & trust by design.** Fernet field encryption at rest, per-purpose DPDP
Act–aligned consent (withdrawal deletes the corresponding data), real account
erasure, and de-identified-at-capture outcome banding.

**Crawler orchestration & change detection.** A crawl pass is triggered two ways
— a CLI (`make crawl`) or a reviewer-gated `POST /crawler/run` (it makes real
outbound requests and LLM calls, so it is never public). For each monitored
source the runner: (1) checks **robots.txt**, which **fails closed** — an
unreachable or unparseable robots file is treated as *disallowed*; (2) fetches
politely — static pages over `httpx`, JavaScript-rendered pages through a
headless **Playwright/Chromium** browser — behind a **per-host 3-second rate
limiter** and a self-identifying User-Agent; (3) runs **hash-based change
detection** that first **normalises out volatile noise** — timestamps,
`session`/`token`/`nonce`/`csrf` parameters, and whitespace — *before* taking a
SHA-256 hash, so incidental markup churn never triggers a false "changed"
signal. Failures are isolated per source (one broken page can't sink the run),
and a source is auto-deactivated after 5 consecutive failures. The whole
architecture converges on one hard invariant: a detected change becomes a
`PendingRevision`, **never** a live `SchemeVersion`.

**Human-gated intake with LLM extraction.** On a real change, HTML is reduced to
text and passed through the **same structured-extraction pipeline the PDF
ingestion uses** — one code path, one extraction prompt, one confidence policy.
The model returns structured fields plus a confidence score; below the **0.7
threshold** the revision is flagged for review, and even an outright extraction
*failure* still produces a queued row ("we couldn't confidently extract this" is
itself useful signal, not a reason to auto-publish). A reviewer then approves,
rejects (with a mandatory reason), or annotates each `PendingRevision`. Approval
marks it reviewed — it still does not publish; turning approved data into a live
scheme is a separate, deliberate human step. **Nothing scraped or extracted ever
reaches the live corpus without a human decision.**

**Retrieval-augmented extraction & grounding (RAG) — dependency-free.** A
government notification can run to many pages; sending it whole either blows the
prompt budget or forces a truncation that can silently cut off the one section
that matters (eligibility, benefit ceilings, document lists). Bharat OS instead
**retrieves** the relevant passages first: it splits text into ~800-character,
sentence-boundary chunks, scores each by overlap with a domain vocabulary
(`eligibility`, `turnover`, `Udyam`, `benefit`, `last date`, …), keeps the top
chunks (re-sorted back into original document order so cross-references read
correctly), and caps what is sent to the model. It is used in **two places**:
(1) long-document extraction — retrieval kicks in above ~12,000 characters, and a
`used_retrieval` flag is surfaced to the reviewer for transparency; and
(2) **grounding soft-criteria judgments** in the scheme's own summary, benefit
text, and neighbouring criteria (via a separate `v1-grounded` prompt version and
cache key, so it never collides with the default judgment path). The design is
deliberately **embedding-free and vector-DB-free** — the domain vocabulary is
predictable enough that keyword/overlap scoring suffices, avoiding a heavy
dependency the problem doesn't need. This path was verified against the real
Gemini API, correctly extracting an eligibility clause buried in a
27,491-character document among ~300 filler paragraphs.

---

*This is an advisory tool, not legal or financial advice. Every draft requires
human review before submission; nothing in this system files an application on a
user's behalf.*
