"use client";

/*
THESIS: A scheme's eligibility breakdown is a diagnostic readout, not a
form with a verdict banner — every criterion resolves to a labeled
status, sourced and dated, with the reserved accent spent only on what
actually blocks the applicant.
OWN-WORLD: Field system — black ground, monospace type, hairline rules,
tabular readouts, one reserved accent for unmet/blocking states.
STORY: An applicant opens a scheme they matched with, sees the freshness
and confidence readouts first, then reads every hard and soft criterion
as a labeled row — met/unmet/uncertain, sourced and dated — before
reaching document status, the draft generator, and real outcome
intelligence for this specific scheme.
FIRST VIEWPORT: FieldNav, a breadcrumb back to the dashboard, the scheme
name with its outcome heading and freshness readout beside it.
FORM: Rollout of the already-committed field-system direction (seed key
ca281bee, index 3) — this page extends that established world.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md.
*/

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DocumentChecklistCard } from "@/components/DocumentChecklist";
import { DraftGenerator } from "@/components/DraftGenerator";
import { FieldNav } from "@/components/FieldNav";
import { HardCriterionRow, SoftCriterionRow } from "@/components/CriterionRow";
import { IntelligencePanel } from "@/components/IntelligencePanel";
import { FieldLoadingState } from "@/components/Ui";
import {
  ApiError,
  getDeepDive,
  getFreshness,
  getIntelligence,
  type DeepDive,
  type SchemeFreshness,
  type SchemeIntelligence,
} from "@/lib/api";
import { formatConfidence, humaniseField } from "@/lib/format";

const OUTCOME_COPY: Record<string, { heading: string; alert: boolean }> = {
  strong: { heading: "Every checkable requirement is met", alert: false },
  promising: { heading: "Worth pursuing, with open questions", alert: false },
  insufficient_data: { heading: "Too little established to say yet", alert: false },
  needs_human_review: { heading: "A judgement here needs a human before you rely on it", alert: false },
  ruled_out: { heading: "You do not currently qualify", alert: true },
};

export default function SchemeDeepDivePage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [data, setData] = useState<DeepDive | null>(null);
  const [freshness, setFreshness] = useState<SchemeFreshness | null>(null);
  const [intel, setIntel] = useState<SchemeIntelligence | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDeepDive(params.slug)
      .then(setData)
      .catch((caught) => {
        if (caught instanceof ApiError && caught.isUnauthenticated) {
          router.replace("/");
        } else if (caught instanceof ApiError && caught.status === 409) {
          router.replace("/onboarding");
        } else {
          setError(caught instanceof ApiError ? caught.detail : "Could not load this scheme.");
        }
      });

    // Freshness is a supplementary trust signal, not on the critical path —
    // a failure here must never block the eligibility breakdown from
    // rendering, so it is fetched and swallowed independently.
    getFreshness(params.slug)
      .then(setFreshness)
      .catch(() => setFreshness(null));

    // Same reasoning as freshness: outcome intelligence is supplementary,
    // fetched and swallowed independently so a failure here never blocks
    // the eligibility breakdown.
    getIntelligence(params.slug)
      .then(setIntel)
      .catch(() => setIntel(null));
  }, [params.slug, router]);

  if (error) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <div role="alert" className="field-panel field-panel-active mx-auto max-w-3xl p-6">
            <p className="text-field-fg">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <FieldLoadingState label="Building the full breakdown" />
        </div>
      </div>
    );
  }

  const copy = OUTCOME_COPY[data.outcome] ?? OUTCOME_COPY.promising!;
  const totalHard = data.met.length + data.unmet.length + data.unverifiable.length;

  return (
    <div className="field-shell">
      <FieldNav trail={data.name} />
      <div className="border-b border-field-rule px-4 py-2 sm:px-6">
        <Link href="/dashboard" className="field-nav-key">
          ← BACK TO YOUR MATCHES
        </Link>
      </div>

      <main className="field-page space-y-8">
        <section className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="field-display">{data.name}</h1>
            <p className={`mt-1 font-field text-sm font-semibold uppercase ${copy.alert ? "text-field-alert" : "text-field-fg"}`}>
              {copy.heading}
            </p>
            {data.confidence !== null && data.confidence !== undefined && (
              <p className="mt-2 max-w-2xl text-sm leading-6 text-field-fg-muted">
                {formatConfidence(data.confidence)} of the evidence we can check supports this —
                {" "}
                {data.met.length} of {totalHard} hard requirements confirmed
                {data.soft.length > 0 && `, plus ${data.soft.length} criteria needing judgement`}.
              </p>
            )}
          </div>

          {freshness && (
            <div className="field-panel shrink-0 px-4 py-1 sm:px-5">
              <div className="field-readout">
                <span className="field-readout-label">SOURCE FRESHNESS</span>
                <span
                  className={
                    freshness.is_stale
                      ? "field-readout-value text-field-alert"
                      : "field-readout-value"
                  }
                >
                  {freshness.is_stale
                    ? `⚠ ${freshness.days_since_last_verification ?? "?"}D AGO`
                    : `WITHIN ${freshness.staleness_threshold_days}D`}
                </span>
              </div>
              <div className="field-readout">
                <span className="field-readout-label">STALE CRITERIA</span>
                <span className="field-readout-value">
                  {freshness.stale_criterion_count}/{freshness.total_criterion_count}
                </span>
              </div>
            </div>
          )}
        </section>

        {(data.has_stale_data || freshness?.is_stale) && (
          <div className="border border-field-alert-border bg-field-alert-bg p-3 font-field text-xs uppercase text-field-alert">
            SOME CRITERIA ON THIS SCHEME HAVE NOT BEEN RE-CHECKED RECENTLY. CONFIRM AGAINST THE OFFICIAL SOURCE BEFORE YOU ACT ON THIS.
          </div>
        )}

        {data.outcome === "ruled_out" && data.disqualifications.length > 0 && (
          <section className="border border-field-alert-border bg-field-alert-bg p-4">
            <h2 className="font-field text-sm font-semibold uppercase text-field-alert">WHY YOU DO NOT CURRENTLY QUALIFY</h2>
            <ul className="mt-2 space-y-2">
              {data.disqualifications.map((d) => (
                <li key={d.criterion_id} className="text-sm">
                  <span className="font-medium text-field-fg">{d.description}</span>
                  <span className="block text-field-fg-muted">{d.reason}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {data.missing_fields.length > 0 && (
          <section className="border border-field-alert-border bg-field-alert-bg p-4">
            <h2 className="font-field text-sm font-semibold uppercase text-field-alert">ADD THESE TO YOUR PROFILE TO SETTLE OPEN REQUIREMENTS</h2>
            <p className="mt-1 text-sm text-field-fg-muted">{data.missing_fields.map(humaniseField).join(", ")}</p>
            <Link href="/onboarding" className="mt-2 inline-block font-field text-xs font-semibold uppercase text-field-alert hover:text-field-fg">
              UPDATE PROFILE
            </Link>
          </section>
        )}

        <div className="grid gap-10 lg:grid-cols-[1.6fr_1fr] lg:gap-14">
          <div className="space-y-6">
            {data.met.length > 0 && (
              <section className="space-y-2">
                <h2 className="field-section-label border-none pb-0">MET ({data.met.length})</h2>
                {data.met.map((c) => <HardCriterionRow key={c.criterion_id} criterion={c} />)}
              </section>
            )}

            {data.unmet.length > 0 && (
              <section className="space-y-2">
                <h2 className="field-section-label border-none pb-0">NOT MET ({data.unmet.length})</h2>
                {data.unmet.map((c) => <HardCriterionRow key={c.criterion_id} criterion={c} />)}
              </section>
            )}

            {data.unverifiable.length > 0 && (
              <section className="space-y-2">
                <h2 className="field-section-label border-none pb-0">CANNOT VERIFY YET ({data.unverifiable.length})</h2>
                {data.unverifiable.map((c) => <HardCriterionRow key={c.criterion_id} criterion={c} />)}
              </section>
            )}

            {data.soft.length > 0 && (
              <section className="space-y-2">
                <h2 className="field-section-label border-none pb-0">REQUIRES JUDGEMENT ({data.soft.length})</h2>
                {data.soft.map((c) => <SoftCriterionRow key={c.criterion_id} criterion={c} />)}
              </section>
            )}
          </div>

          <div className="space-y-6">
            <DocumentChecklistCard slug={params.slug} />
            <DraftGenerator slug={params.slug} schemeName={data.name} />
          </div>
        </div>

        {intel && <IntelligencePanel intel={intel} />}

        <p className="field-panel p-4 font-field text-[11px] uppercase leading-6 tracking-[0.04em] text-field-fg-muted">
          {data.disclaimer}
        </p>
      </main>
    </div>
  );
}
