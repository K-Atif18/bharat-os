# Demo guide

## Setup

```bash
cp .env.example .env
make install
make migrate
make seed
make dev-backend   # http://localhost:8000
make dev-frontend  # http://localhost:3000
```

Open `http://localhost:3000` and select **Launch live judge demo** on the
landing page.

## What the demo provisions

An isolated account through the real registration API, with:

- **ZEN Club** — Pune, Maharashtra, logistics, early stage
- 12 employees, ₹18L annual turnover
- DPIIT, GST, and company-incorporation registrations
- DPIIT certificate + incorporation certificate in the document vault

Safe to repeat — every launch creates a fresh isolated account.

## Key invariants to state out loud

1. The draft workspace always shows "this is a draft, not a submission."
2. Outcome reporting always shows the de-identification note.
3. The calibration page shows a synthetic-data warning whenever real
   outcome data doesn't yet exist for the sample.
4. Soft criteria never say "eligible" — always a verdict + confidence +
   reasoning, with low-confidence cases forced into human review.
5. `cannot_verify` is a visible, distinct state — never silently treated
   as a failed check.
