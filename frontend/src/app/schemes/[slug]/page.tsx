"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DocumentChecklistCard } from "@/components/DocumentChecklist";
import { DraftGenerator } from "@/components/DraftGenerator";
import { HardCriterionRow, SoftCriterionRow } from "@/components/CriterionRow";
import { ApiError, getDeepDive, type DeepDive } from "@/lib/api";
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
  }, [params.slug, router]);

  if (error) {
    return (
      <div role="alert" className="rounded-lg border border-unmet-border bg-unmet-bg p-4 text-sm text-unmet-fg">
        {error}
      </div>
    );
  }

  if (!data) {
    return <p className="text-sm text-ink-subtle">Loading the full breakdown…</p>;
  }

  const copy = OUTCOME_COPY[data.outcome] ?? OUTCOME_COPY.promising!;
  const totalHard = data.met.length + data.unmet.length + data.unverifiable.length;

  return (
    <div className="space-y-8">
      <div>
        <Link href="/dashboard" className="text-sm text-brand hover:underline">
          ← Back to your matches
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{data.name}</h1>
        <p className={`mt-1 text-sm font-medium ${copy.tone}`}>{copy.heading}</p>
        {data.confidence !== null && data.confidence !== undefined && (
          <p className="mt-1 text-sm text-ink-muted">
            {formatConfidence(data.confidence)} of the evidence we can check supports this —
            {" "}
            {data.met.length} of {totalHard} hard requirements confirmed
            {data.soft.length > 0 && `, plus ${data.soft.length} criteria needing judgement`}.
          </p>
        )}
      </div>

      {data.has_stale_data && (
        <div className="rounded border border-unverified-border bg-unverified-bg px-4 py-2 text-sm text-unverified-fg">
          Some criteria on this scheme have not been re-checked recently. Confirm against the
          official source before you act on this.
        </div>
      )}

      {data.outcome === "ruled_out" && data.disqualifications.length > 0 && (
        <section className="rounded-lg border border-unmet-border bg-unmet-bg p-5">
          <h2 className="text-sm font-medium text-unmet-fg">
            Why you do not currently qualify
          </h2>
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
        <section className="rounded-lg border border-unverified-border bg-unverified-bg p-5">
          <h2 className="text-sm font-medium text-unverified-fg">
            Add these to your profile to settle open requirements
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            {data.missing_fields.map(humaniseField).join(", ")}
          </p>
          <Link href="/onboarding" className="mt-2 inline-block text-sm text-brand hover:underline">
            Update profile
          </Link>
        </section>
      )}

      {data.met.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-medium uppercase tracking-wide text-ink-subtle">
            Met ({data.met.length})
          </h2>
          {data.met.map((c) => (
            <HardCriterionRow key={c.criterion_id} criterion={c} />
          ))}
        </section>
      )}

      {data.unmet.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-medium uppercase tracking-wide text-ink-subtle">
            Not met ({data.unmet.length})
          </h2>
          {data.unmet.map((c) => (
            <HardCriterionRow key={c.criterion_id} criterion={c} />
          ))}
        </section>
      )}

      {data.unverifiable.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-medium uppercase tracking-wide text-ink-subtle">
            Cannot verify yet ({data.unverifiable.length})
          </h2>
          {data.unverifiable.map((c) => (
            <HardCriterionRow key={c.criterion_id} criterion={c} />
          ))}
        </section>
      )}

      {data.soft.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-medium uppercase tracking-wide text-ink-subtle">
            Requires judgement ({data.soft.length})
          </h2>
          {data.soft.map((c) => (
            <SoftCriterionRow key={c.criterion_id} criterion={c} />
          ))}
        </section>
      )}

      <DocumentChecklistCard slug={params.slug} />

      <DraftGenerator slug={params.slug} schemeName={data.name} />

      <p className="rounded border border-surface-border bg-surface px-4 py-3 text-xs text-ink-muted">
        {data.disclaimer}
      </p>
    </div>
  );
}
