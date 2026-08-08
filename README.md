# Bharat OS

Eligibility reasoning and application preparation for Indian government
funding schemes — for startups and MSMEs who don't have a consultant doing
this for them.

Most tools in this space stop at discovery: fill a form, get a match score,
get a link to a government portal. Bharat OS goes further: it tells you
**why** you qualify (or don't), what documents you're missing, drafts your
application with every field labeled by source, and reports honestly on its
own accuracy instead of presenting AI output as fact.

## What makes this different

- **Deterministic eligibility, not AI guessing.** Hard criteria (turnover
  caps, registration requirements, age limits) run through a real
  three-valued logic engine — met / unmet / **cannot verify**. Missing data
  is never silently treated as a failed check.
- **Every fact is sourced.** Every eligibility criterion carries a real
  government source URL. An unverifiable claim is flagged as such, never
  invented.
- **AI judgments are hedged, not confident-sounding.** Soft/subjective
  criteria go through an LLM with an explicit confidence score and a full
  audit trail (model, prompt version, cache status). Low-confidence
  judgments are forced into human review, not presented as answers.
- **The system reports on its own accuracy.** A live calibration page
  measures whether the AI's stated confidence actually matches real
  outcomes — with an honest warning whenever the underlying data is
  synthetic rather than real.
- **It goes past discovery into execution.** Document-gap analysis, a
  deadline reachability calendar, and an editable draft application with
  per-field provenance (profile-sourced / AI-drafted / needs you) — not
  just a match score and a portal link.
- **It tracks ground truth.** An outcome-intelligence panel aggregates
  de-identified real application outcomes — actual approval rates, actual
  timelines, actual rejection reasons — instead of only republishing what
  a scheme's official notification claims.

## Stack

- **Backend:** FastAPI, Python 3.11, SQLAlchemy 2, PostgreSQL (SQLite for
  local dev)
- **Frontend:** Next.js 15, React 19, Tailwind CSS
- **AI:** Provider-neutral LLM adapter (deterministic mock by default,
  Gemini optional)

## Quick start

```bash
# Create databases
sudo -u postgres createuser --createdb "$USER"
sudo -u postgres createdb -O "$USER" bharat_os

# Install
cp .env.example .env
make install
make migrate
make seed

# Run
make dev-backend   # http://localhost:8000
make dev-frontend  # http://localhost:3000
```

Open `http://localhost:3000` and select **Launch live judge demo** for a
one-click provisioned account with real scheme matches, or register a real
account through the normal flow.

## Commands

```
make install        install dependencies
make migrate         run database migrations
make seed             load scheme data
make dev-backend     start API server
make dev-frontend    start frontend
make test             run tests
make lint             run linters
make types            regenerate frontend types from the live API schema
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design, repository
  map, backend layers, and the two frontend visual systems
- [`docs/API.md`](docs/API.md) — full endpoint reference
- [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) — demo setup and what to expect
- [`CHANGELOG.md`](CHANGELOG.md) — what was built and when

## Status

40 seeded schemes, real deterministic + AI-assisted eligibility reasoning,
live calibration and outcome-intelligence measurement, application
workspace with draft generation, document vault, and deadline tracking. All
routes and the full test suite (372 backend, 25 frontend, 4 end-to-end) pass
in CI.

This is an advisory tool, not legal or financial advice. Every draft
requires human review before submission; nothing in this system files an
application on a user's behalf.
