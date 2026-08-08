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

## Demo script (~4 minutes)

1. **Landing** — a live typed boot sequence types out real system facts
   (scheme count, engine type) before the page reveals. Click **Launch
   live judge demo**.
2. **Dashboard** — "40 schemes assessed. X fully met, Y worth a look,
   potential benefit ₹Z" as tabular instrument readouts, not a stat-card
   grid. Point out the reserved red accent only appears when something is
   actually blocked — everything else is deliberately neutral.
3. **Click into a match** (e.g. SISFS) — the deep-dive page: hard
   criteria (met/unmet/cannot-verify) and soft criteria (AI-judged, with a
   confidence score and an expandable audit trail — model, prompt version,
   cache status). Point out the freshness readout ("verified within 90d" /
   stale warning).
4. **Document checklist** — "have / need / expired" counts, real gap
   detection against the vault.
5. **Generate a draft** — the compact draft card on the deep-dive page,
   then **Open full workspace** for the full instrument-panel view:
   version number, fields-populated count, per-field provenance
   (profile / AI-drafted / needs you). Point out the "not a submission"
   notice.
6. **Outcome intelligence panel** (bottom of the deep-dive page) — real
   approval rate, average days to decision, ranked rejection reasons, with
   an explicit synthetic-data warning where applicable.
7. **Calibration page** (`/calibration`) — "when we say 80% confident, are
   we actually right 80% of the time?" — the 5-band reliability diagram,
   ECE, and overconfidence/underconfidence direction, all computed live
   from real seeded data.
8. **Applications page** (`/applications`) — pipeline status, outcome
   reporting with a de-identification note.
9. **Vault** (`/vault`) and **Deadlines** (`/deadlines`) — document
   metadata and reachability-scored deadlines with `.ics` export.

## Key invariants to state out loud

1. The draft workspace always shows "this is a draft, not a submission."
2. Outcome reporting always shows the de-identification note.
3. The calibration page shows a synthetic-data warning whenever real
   outcome data doesn't yet exist for the sample.
4. Soft criteria never say "eligible" — always a verdict + confidence +
   reasoning, with low-confidence cases forced into human review.
5. `cannot_verify` is a visible, distinct state — never silently treated
   as a failed check.

## Judge Q&A

**Q: What's actually new versus a chatbot wrapper?**
A: A deterministic three-valued rule engine for hard criteria (no LLM
involved at all), a real confidence-calibration measurement of the AI's
own accuracy, and outcome intelligence that tracks what actually happens
to real applications — not just what the scheme guidelines claim.

**Q: The calibration/intelligence data is synthetic — doesn't that
undercut the point?**
A: We say so explicitly in the UI, every time. The measurement machinery
is real and live; it's waiting for real outcome reports to replace the
synthetic seed data, and the moment one real outcome exists, it's never
diluted by the synthetic volume around it (a hard invariant, tested).

**Q: How do you handle government portals changing?**
A: A crawler does hash-based change detection on monitored URLs. Any
change runs through the same LLM extraction pipeline as PDF ingestion,
then lands in a human review queue — nothing publishes automatically. The
freshness API separately reports how long it's been since each criterion
was last human-verified.

**Q: Scheme corpus size?**
A: 40 schemes, each validated against the real Pydantic schema, each with
at least one hard criterion and real document requirements. Entries where
genuine sourcing couldn't be confirmed were held back rather than
published with a placeholder or fabricated quote.
