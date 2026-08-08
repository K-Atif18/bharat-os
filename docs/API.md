# API reference

FastAPI service, `http://localhost:8000` in development. Interactive docs at
`/docs`. This is an operator-friendly inventory; the generated OpenAPI schema
(`make types`) is the exact contract.

## Conventions

- JSON bodies use snake_case. Auth is an opaque HttpOnly session cookie.
- Error responses use `{ "detail": ... }`.
- `401` no session · `403` missing consent/role · `404` not found for this
  caller · `409` state conflict · `422` validation failed · `429` rate limit.

## Health

| Method | Path | Access |
| --- | --- | --- |
| GET | `/health` | Public |

## Scheme corpus

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/schemes` | Public | Current scheme summaries (40 schemes) |
| GET | `/schemes/{slug}` | Public | Sourced scheme detail |

## Authentication and account

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public | Create account + consents, issue session |
| POST | `/auth/login` | Public | Verify credentials, issue session |
| POST | `/auth/logout` | Session | Revoke session |
| GET | `/me` | Session | Account + consents + profile-presence flag |
| POST | `/me/consents` | Session | Grant/withdraw one purpose |
| DELETE | `/me` | Session | Erase personal data, return deletion receipt |

## Profile and matching

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET / POST | `/profile` | Session + consent | Business profile |
| GET | `/matches` | Session + consent | Ranked scheme feed (met/unmet/ruled-out) |
| GET | `/matches/{slug}/deep-dive` | Session + consent | Full criterion-by-criterion breakdown |
| GET | `/matches/draftable` | Public | Scheme slugs that support drafting |

## Drafts (application workspace)

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/matches/{slug}/draft` | Session | Generate a new draft version (never overwrites) |
| GET | `/matches/{slug}/draft` | Session | Fetch the current draft version |
| GET | `/matches/drafts/{id}/diff/{other_id}` | Session | Field-by-field diff between two of the caller's own draft versions |

Drafts are immutable once generated — there is no edit endpoint. The
frontend workspace page (`/schemes/[slug]/workspace`) persists
human-provided field edits in browser localStorage only, clearly labeled as
such, never submitted anywhere.

## Documents and deadlines

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET / POST | `/documents` | Session + consent | Document vault metadata |
| DELETE | `/documents/{id}` | Session + consent | Remove a vault record |
| GET | `/matches/{slug}/documents` | Session + consent | Have/need/expired checklist for one scheme |
| GET | `/deadlines` | Session + consent | Reachability-scored deadline list |
| GET | `/deadlines/calendar.ics` | Session + consent | `.ics` calendar export |

## Applications and outcomes

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/applications` | Session | List tracked applications |
| POST | `/matches/{slug}/applications` | Session | Start tracking an application (draft state) |
| PATCH | `/applications/{id}` | Session | Record a user-told-us status change |
| POST | `/applications/{id}/outcome` | Session + consent | Record an outcome (turnover banded at capture) |
| GET | `/schemes/{slug}/outcome-stats` | Session | Aggregate, de-identified outcome stats |

## Trust and measurement

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/freshness/` | Public | Staleness report for all schemes |
| GET | `/freshness/{slug}` | Public | Staleness for one scheme |
| GET | `/calibration/` | Public | Expected Calibration Error + reliability buckets |
| GET | `/intelligence/{slug}` | Public | Real approval rate, rejection reasons, turnover-band breakdown |

All three are aggregate/catalogue data, not user data, hence public.

## Crawler and review queue (reviewer-only)

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/crawler/run` | Reviewer | Run crawler + LLM extraction against monitored sources |
| GET | `/crawler/sources` | Reviewer | List monitored crawl sources |
| GET | `/review-queue/` | Reviewer | Pending extraction revisions |
| POST | `/review-queue/{id}/approve` | Reviewer | Approve an extraction as reviewed |
| POST | `/review-queue/{id}/reject` | Reviewer | Reject with a required reason |
