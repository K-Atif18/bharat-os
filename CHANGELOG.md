# Changelog

Everything built during the CODEAMBLE 2026 hackathon session, on top of the
pre-existing baseline (deterministic eligibility engine, LLM soft-criteria
judgement, ranking, draft generation for 3 schemes, application lifecycle,
outcome capture, calibration CLI, crawler, PDF pipeline, review queue, 15
schemes).

## Backend

- **Scheme corpus**: 15 → 40 schemes, each validated against the real
  Pydantic schema before merging; entries without genuine sourcing held back
  rather than published with placeholder or fabricated citations.
- **Freshness API** (`/freshness/`, `/freshness/{slug}`) — staleness
  computed from a scheme's oldest verified criterion.
- **Calibration API** (`/calibration/`) — live ECE, reliability buckets,
  overconfidence/underconfidence direction, exposed from the existing
  measurement service.
- **Outcome intelligence API** (`/intelligence/{slug}`) — approval rate,
  average days to decision, rejection-reason ranking, turnover-band
  breakdown, with a synthetic-outcome seed script and an honest
  `has_real_outcomes` invariant (never diluted by synthetic volume).
- **Crawler orchestration** — HTML change detection now runs the same LLM
  extraction pipeline PDFs already used; new CLI, seeded crawl sources,
  reviewer-gated API.
- **RAG retrieval** — dependency-free chunking/keyword-scoring for long
  document extraction and for grounding soft-criteria AI judgement in a
  scheme's own stored text; no vector database or embeddings.
- **Draft version diff** (`/matches/drafts/{id}/diff/{other_id}`) — pure
  Python field-by-field comparison between a caller's own draft versions.
- **Real Gemini integration** — provider-neutral adapter now backed by a
  real Gemini API key in local dev (`gemini-flash-latest`).

## Frontend

- **Full visual redesign**, chosen through a structured design-direction
  process: a monochrome "field system" for every working page (dashboard,
  deep-dive, calibration, onboarding, settings, review queue, application
  workspace, vault, applications, deadlines), and a green-phosphor "terminal
  system" for the landing page — two deliberately distinct worlds sharing
  one underlying design language.
- **New pages**: `/calibration`, `/schemes/[slug]/workspace` (full
  application workspace with draft editing via localStorage), `/vault`,
  `/applications` (with outcome reporting), `/deadlines` (reachability
  calendar + `.ics` export).
- **Dashboard**: real-time stats strip (assessed / fully met / worth a
  look / potential benefit ₹) sourced from the live match feed.
- **Draft editing** — human-required fields are now editable, persisted to
  browser localStorage only, clearly labeled as not submitted or synced.
- **Accessibility fix** — several redesigned section headings were
  rendering without a real heading element (caught by CI's E2E suite);
  fixed across every affected component.

## Process

- Design direction for both visual worlds selected via the impeccable
  design skill's structured comparison process, not ad hoc styling choices.
- Every redesigned page kept its real API calls, validation logic, and
  compliance-sensitive copy (consent withdrawal, account erasure) unchanged
  — verified against existing test coverage where it existed.
- CI (GitHub Actions): 6 jobs, 4 E2E browser journeys, all green as of the
  final push this session.
