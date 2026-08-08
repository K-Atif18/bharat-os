"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DocumentChecklistCard } from "@/components/DocumentChecklist";
import { DraftGenerator } from "@/components/DraftGenerator";
import { HardCriterionRow, SoftCriterionRow } from "@/components/CriterionRow";
import { IntelligencePanel } from "@/components/IntelligencePanel";
import { LoadingState } from "@/components/Ui";
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

const OUTCOME_COPY: Record<string, { heading: string; tone: string }> = {
  strong: { heading: "Every checkable requirement is met", tone: "text-met-fg" },
  promising: { heading: "Worth pursuing, with open questions", tone: "text-unverified-fg" },
  insufficient_data: { heading: "Too little established to say yet", tone: "text-ink-muted" },
  needs_human_review: {
    heading: "A judgement here needs a human before you rely on it",
    tone: "text-unverified-fg",
  },
  ruled_out: { heading: "You do not currently qualify", tone: "text-unmet-fg" },
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
      <div role="alert" className="notice mx-auto max-w-3xl border-unmet-border bg-unmet-bg text-unmet-fg">
        {error}
      </div>
    );
  }

  if (!data) {
    return <LoadingState label="Building the full breakdown" />;
  }

  const copy = OUTCOME_COPY[data.outcome] ?? OUTCOME_COPY.promising!;
  const totalHard = data.met.length + data.unmet.length + data.unverifiable.length;

  return (
    <div className="page-stack">
      <div className="folio-rule" data-folio="Deep dive">
        <Link href="/dashboard" className="meta-line text-brand hover:underline">
          ← Back to your matches
        </Link>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="page-title">{data.name}</h1>
            <p className={`mt-1 text-sm font-semibold ${copy.tone}`}>{copy.heading}</p>
            {data.confidence !== null && data.confidence !== undefined && (
              <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
                {formatConfidence(data.confidence)} of the evidence we can check supports this —
                {" "}
                {data.met.length} of {totalHard} hard requirements confirmed
                {data.soft.length > 0 && `, plus ${data.soft.length} criteria needing judgement`}.
              </p>
            )}
          </div>

          {freshness && (
            <div className="shrink-0 border border-surface-strong px-3 py-2 text-right">
              <p className="meta-line">Source freshness</p>
              {freshness.is_stale ? (
                <p className="mt-1 text-sm font-semibold text-unverified-fg">
                  ⚠ {freshness.days_since_last_verification ?? "unknown"}d since last check
                </p>
              ) : (
                <p className="mt-1 text-sm font-semibold text-met-fg">
                  Verified within {freshness.staleness_threshold_days}d
                </p>
              )}
              <p className="mt-0.5 text-xs text-ink-subtle">
                {freshness.stale_criterion_count} of {freshness.total_criterion_count} criteria stale
              </p>
            </div>
          )}
        </div>
      </div>

      {(data.has_stale_data || freshness?.is_stale) && (
        <div className="notice border-unverified-border bg-unverified-bg text-unverified-fg">
          Some criteria on this scheme have not been re-checked recently. Confirm against the
          official source before you act on this.
        </div>
      )}

      {data.outcome === "ruled_out" && data.disqualifications.length > 0 && (
        <section className="notice border-unmet-border bg-unmet-bg text-unmet-fg">
          <h2 className="font-semibold">Why you do not currently qualify</h2>
          <ul className="mt-2 space-y-2">
            {data.disqualifications.map((d) => (
              <li key={d.criterion_id} className="text-sm">
                <span className="font-medium">{d.description}</span>
                <span className="block text-ink-muted">{d.reason}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.missing_fields.length > 0 && (
        <section className="notice border-unverified-border bg-unverified-bg text-unverified-fg">
          <h2 className="font-semibold">Add these to your profile to settle open requirements</h2>
          <p className="mt-1 text-sm">{data.missing_fields.map(humaniseField).join(", ")}</p>
          <Link href="/onboarding" className="mt-2 inline-block text-sm font-semibold text-brand hover:underline">
            Update profile
          </Link>
        </section>
      )}

      <div className="split-a">
        <div className="space-y-6">
          {data.met.length > 0 && (
            <section className="space-y-2">
              <h2 className="folio-rule pt-0 text-sm font-semibold uppercase tracking-wide text-ink-subtle">Met ({data.met.length})</h2>
              {data.met.map((c) => <HardCriterionRow key={c.criterion_id} criterion={c} />)}
            </section>
          )}

          {data.unmet.length > 0 && (
            <section className="space-y-2">
              <h2 className="folio-rule pt-0 text-sm font-semibold uppercase tracking-wide text-ink-subtle">Not met ({data.unmet.length})</h2>
              {data.unmet.map((c) => <HardCriterionRow key={c.criterion_id} criterion={c} />)}
            </section>
          )}

          {data.unverifiable.length > 0 && (
            <section className="space-y-2">
              <h2 className="folio-rule pt-0 text-sm font-semibold uppercase tracking-wide text-ink-subtle">Cannot verify yet ({data.unverifiable.length})</h2>
              {data.unverifiable.map((c) => <HardCriterionRow key={c.criterion_id} criterion={c} />)}
            </section>
          )}

          {data.soft.length > 0 && (
            <section className="space-y-2">
              <h2 className="folio-rule pt-0 text-sm font-semibold uppercase tracking-wide text-ink-subtle">Requires judgement ({data.soft.length})</h2>
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

      <p className="notice border-info-border bg-info-bg text-xs text-info-fg">{data.disclaimer}</p>
    </div>
  );
}
