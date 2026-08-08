/**
 * Typed access to the Bharat OS API.
 *
 * Response types come from `api-types.ts`, which is generated from the backend's
 * OpenAPI schema by `make types`. Nothing here restates a shape the backend
 * already defines, so the two sides cannot drift apart unnoticed.
 *
 * Every request sends credentials, because authentication is a session cookie.
 */

import type { components } from "@/lib/api-types";

export type SchemeSummary = components["schemas"]["SchemeSummaryOut"];
export type SchemeDetail = components["schemas"]["SchemeDetailOut"];
export type Health = components["schemas"]["HealthOut"];
export type EligibilityCriterion = components["schemas"]["EligibilityCriterionOut"];
export type DocumentRequirement = components["schemas"]["DocumentRequirementOut"];
export type Account = components["schemas"]["AccountOut"];
export type Consent = components["schemas"]["ConsentOut"];
export type Profile = components["schemas"]["ProfileOut"];
export type ProfileInput = components["schemas"]["ProfileIn"];
export type Match = components["schemas"]["MatchOut"];
export type MatchFeed = components["schemas"]["MatchFeedOut"];
export type DeepDive = components["schemas"]["DeepDiveOut"];
export type Erasure = components["schemas"]["ErasureOut"];
export type ConsentPurpose = components["schemas"]["ConsentPurpose"];
export type MatchOutcome = components["schemas"]["MatchOutcome"];

const SERVER_FALLBACK_BASE_URL = "http://127.0.0.1:8000";

export function apiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");

  // Keep the API on the same browser hostname as the frontend. SameSite=Lax
  // cookies set by 127.0.0.1 are not sent from a page opened on localhost (and
  // vice versa), even though both resolve to this machine.
  if (typeof window !== "undefined") {
    const port = process.env.NEXT_PUBLIC_API_PORT?.trim() || "8000";
    return `${window.location.protocol}//${window.location.hostname}:${port}`;
  }

  return SERVER_FALLBACK_BASE_URL;
}

/** Raised when the API responds with a non-2xx status. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }

  /** Whether this represents "not signed in", which callers handle differently. */
  get isUnauthenticated(): boolean {
    return this.status === 401;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    // The session lives in an HttpOnly cookie, so it must be sent explicitly
    // for cross-origin requests during development.
    credentials: "include",
    // Scheme data changing under a user mid-application is actively harmful,
    // so nothing here is cached.
    cache: "no-store",
  });

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation errors arrive as a list of field problems.
        detail = body.detail
          .map((item) => {
            const entry = item as { loc?: unknown[]; msg?: string };
            const field = entry.loc?.slice(1).join(".") ?? "request";
            return `${field}: ${entry.msg ?? "invalid"}`;
          })
          .join("; ");
      }
    } catch {
      // Response body was not JSON; the status text is the best we have.
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

// --- Public catalogue -------------------------------------------------------

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

export function listSchemes(
  params: { segment?: string; state?: string } = {},
): Promise<SchemeSummary[]> {
  const query = new URLSearchParams();
  if (params.segment) query.set("segment", params.segment);
  if (params.state) query.set("state", params.state);
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  return request<SchemeSummary[]>(`/schemes${suffix}`);
}

export function getScheme(slug: string, version?: number): Promise<SchemeDetail> {
  const suffix = version === undefined ? "" : `?version=${version}`;
  return request<SchemeDetail>(`/schemes/${encodeURIComponent(slug)}${suffix}`);
}

// --- Authentication ---------------------------------------------------------

export function registerAccount(input: {
  email: string;
  password: string;
  consents: ConsentPurpose[];
}): Promise<Account> {
  return request<Account>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function login(input: { email: string; password: string }): Promise<Account> {
  return request<Account>("/auth/login", { method: "POST", body: JSON.stringify(input) });
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export function getAccount(): Promise<Account> {
  return request<Account>("/me");
}

export function updateConsent(purpose: ConsentPurpose, granted: boolean): Promise<Consent[]> {
  return request<Consent[]>("/me/consents", {
    method: "POST",
    body: JSON.stringify({ purpose, granted }),
  });
}

export function eraseAccount(): Promise<Erasure> {
  return request<Erasure>("/me", { method: "DELETE" });
}

// --- Profile ----------------------------------------------------------------

export function getProfile(): Promise<Profile> {
  return request<Profile>("/profile");
}

export function saveProfile(input: ProfileInput): Promise<Profile> {
  return request<Profile>("/profile", { method: "PUT", body: JSON.stringify(input) });
}

// --- Matches ----------------------------------------------------------------

export function getMatches(minConfidence?: number): Promise<MatchFeed> {
  const suffix = minConfidence === undefined ? "" : `?min_confidence=${minConfidence}`;
  return request<MatchFeed>(`/matches${suffix}`);
}

export function getMatch(slug: string): Promise<Match> {
  return request<Match>(`/matches/${encodeURIComponent(slug)}`);
}

export function getDeepDive(slug: string): Promise<DeepDive> {
  return request<DeepDive>(`/matches/${encodeURIComponent(slug)}/deep-dive`);
}

// --- Scheme data freshness ----------------------------------------------------

export type SchemeFreshness = components["schemas"]["SchemeFreshnessOut"];

export function listFreshness(): Promise<SchemeFreshness[]> {
  return request<SchemeFreshness[]>("/freshness/");
}

export function getFreshness(slug: string): Promise<SchemeFreshness> {
  return request<SchemeFreshness>(`/freshness/${encodeURIComponent(slug)}`);
}

// --- Confidence calibration -----------------------------------------------

export type Calibration = components["schemas"]["CalibrationOut"];
export type CalibrationBucket = components["schemas"]["BucketOut"];

export function getCalibration(): Promise<Calibration> {
  return request<Calibration>("/calibration/");
}

// --- Scheme outcome intelligence --------------------------------------------

export type SchemeIntelligence = components["schemas"]["SchemeIntelligenceOut"];

export function getIntelligence(slug: string): Promise<SchemeIntelligence> {
  return request<SchemeIntelligence>(`/intelligence/${encodeURIComponent(slug)}`);
}

// --- Document vault ----------------------------------------------------------

export type UserDocument = components["schemas"]["UserDocumentOut"];
export type UserDocumentInput = components["schemas"]["UserDocumentIn"];
export type DocumentChecklist = components["schemas"]["DocumentChecklistOut"];

export function listDocuments(): Promise<UserDocument[]> {
  return request<UserDocument[]>("/documents");
}

export function addDocument(input: UserDocumentInput): Promise<UserDocument> {
  return request<UserDocument>("/documents", { method: "POST", body: JSON.stringify(input) });
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function getDocumentChecklist(slug: string): Promise<DocumentChecklist> {
  return request<DocumentChecklist>(`/matches/${encodeURIComponent(slug)}/documents`);
}

// --- Application drafts -------------------------------------------------------

export type Draft = components["schemas"]["DraftOut"];

export function createDraft(slug: string): Promise<Draft> {
  return request<Draft>(`/matches/${encodeURIComponent(slug)}/draft`, { method: "POST" });
}

export function getDraft(slug: string): Promise<Draft> {
  return request<Draft>(`/matches/${encodeURIComponent(slug)}/draft`);
}

// --- Application tracking -----------------------------------------------------

export type Application = components["schemas"]["ApplicationOut"];
export type ApplicationStatus = components["schemas"]["ApplicationStatus"];
export type Outcome = components["schemas"]["OutcomeOut"];
export type OutcomeInput = components["schemas"]["OutcomeIn"];

export function listApplications(): Promise<Application[]> {
  return request<Application[]>("/applications");
}

export function startApplication(slug: string): Promise<Application> {
  return request<Application>(`/matches/${encodeURIComponent(slug)}/applications`, {
    method: "POST",
  });
}

export function updateApplicationStatus(
  applicationId: string,
  status: ApplicationStatus,
  externalReference?: string,
): Promise<Application> {
  return request<Application>(`/applications/${encodeURIComponent(applicationId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status, external_reference: externalReference ?? null }),
  });
}

export function recordOutcome(applicationId: string, input: OutcomeInput): Promise<Outcome> {
  return request<Outcome>(`/applications/${encodeURIComponent(applicationId)}/outcome`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// --- Deadline calendar ---------------------------------------------------------

export type DeadlineCalendar = components["schemas"]["DeadlineCalendarOut"];

export function getDeadlineCalendar(): Promise<DeadlineCalendar> {
  return request<DeadlineCalendar>("/deadlines");
}

// --- Verification queue (reviewer-only) ---------------------------------------

export type PendingRevision = components["schemas"]["PendingRevisionOut"];

export function listPendingRevisions(): Promise<PendingRevision[]> {
  return request<PendingRevision[]>("/review-queue");
}

export function approveRevision(id: string, note?: string): Promise<PendingRevision> {
  return request<PendingRevision>(`/review-queue/${encodeURIComponent(id)}/approve`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null }),
  });
}

export function rejectRevision(id: string, note: string): Promise<PendingRevision> {
  return request<PendingRevision>(`/review-queue/${encodeURIComponent(id)}/reject`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}
