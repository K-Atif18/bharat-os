"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { RuledOutCard, SchemeCard } from "@/components/SchemeCard";
import { LoadingState, SectionHeading } from "@/components/Ui";
import { ApiError, getMatches, getProfile, type MatchFeed, type Profile } from "@/lib/api";
import { humaniseField } from "@/lib/format";

const PIPELINE = [
  ["01", "Matched", "Ranked by fit, value, and effort"],
  ["02", "Verified", "Hard rules and AI judgement separated"],
  ["03", "Prepared", "Document gaps placed on a critical path"],
  ["04", "Drafted", "Editable workspace, never auto-submitted"],
];

export default function DashboardPage() {
  const router = useRouter();
  const [feed, setFeed] = useState<MatchFeed | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRuledOut, setShowRuledOut] = useState(false);
  const ruledOutId = useId();

  useEffect(() => {
    Promise.all([getMatches(), getProfile()])
      .then(([nextFeed, nextProfile]) => {
        setFeed(nextFeed);
        setProfile(nextProfile);
      })
      .catch((caught) => {
        if (caught instanceof ApiError && caught.isUnauthenticated) router.replace("/");
        else if (caught instanceof ApiError && caught.status === 409) router.replace("/onboarding");
        else setError(caught instanceof ApiError ? caught.detail : "Could not load matches.");
      });
  }, [router]);

  if (error) {
    return (
      <div role="alert" className="notice mx-auto max-w-3xl border-unmet-border bg-unmet-bg text-unmet-fg">
        <p className="font-semibold">{error}</p>
        <p className="mt-1 text-sm text-ink-muted">If the API is not running, start it with <code className="font-mono">make dev-backend</code>.</p>
      </div>
    );
  }

  if (!feed || !profile) return <LoadingState label="Checking your business against every scheme" />;

  const ready = feed.matches.filter((match) => match.outcome === "eligible");
  const partial = feed.matches.filter((match) => match.outcome !== "eligible");

  return (
    <div className="page-stack">
      <section className="panel overflow-hidden border-l-4 border-l-brand">
        <div className="p-5 sm:p-7">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="eyebrow">Funding command center</p>
              <h1 className="page-title mt-2">{profile.entity_name}</h1>
              <p className="mt-2 text-sm text-ink-muted sm:text-base">
                {profile.district ? `${profile.district}, ` : ""}{profile.state} · {humaniseField(profile.sector)}
                {profile.employee_count !== null && ` · ${profile.employee_count} employees`}
              </p>
              {profile.registrations.length > 0 && (
                <ul className="mt-4 flex flex-wrap gap-2" aria-label="Registrations">
                  {profile.registrations.map((registration) => (
                    <li key={registration} className="rounded-full border border-surface-strong bg-surface-sunken px-3 py-1 text-xs font-semibold text-ink-muted">
                      {humaniseField(registration)}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/onboarding" className="button-secondary">Edit profile</Link>
              <Link href="/settings" className="button-primary">Privacy &amp; data</Link>
            </div>
          </div>

          <dl className="mt-7 grid grid-cols-3 divide-x divide-surface-strong border-y border-surface-strong py-4">
            <div className="pr-3 sm:pr-6">
              <dt className="text-[11px] leading-4 text-ink-subtle sm:text-xs">Schemes assessed</dt>
              <dd className="data-value mt-1 text-2xl font-semibold text-civic-navy sm:text-3xl">{feed.schemes_assessed}</dd>
            </div>
            <div className="px-3 sm:px-6">
              <dt className="text-[11px] leading-4 text-ink-subtle sm:text-xs">All checks met</dt>
              <dd className="data-value mt-1 text-2xl font-semibold text-met-fg sm:text-3xl">{ready.length}</dd>
            </div>
            <div className="pl-3 sm:pl-6">
              <dt className="text-[11px] leading-4 text-ink-subtle sm:text-xs">Worth investigating</dt>
              <dd className="data-value mt-1 text-2xl font-semibold text-ink sm:text-3xl">{feed.matches.length}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section aria-labelledby="pipeline-heading">
        <div className="flex items-center justify-between gap-4">
          <h2 id="pipeline-heading" className="text-sm font-semibold text-ink">Application execution path</h2>
          <p className="hidden text-xs text-ink-subtle sm:block">Every stage stays reviewable</p>
        </div>
        <ol className="mt-3 grid border-y border-surface-strong sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE.map(([number, title, detail], index) => (
            <li key={number} className={`py-4 sm:px-5 ${index > 0 ? "border-t border-surface-border sm:border-l sm:border-t-0" : ""}`}>
              <span className="data-value text-[10px] font-semibold text-brand">{number}</span>
              <h3 className="mt-1 text-sm font-semibold text-ink">{title}</h3>
              <p className="mt-1 text-xs leading-5 text-ink-subtle">{detail}</p>
            </li>
          ))}
        </ol>
      </section>

      <SectionHeading
        eyebrow="Opportunity map"
        title="Your matches"
        description={<>Checked your profile against {feed.schemes_assessed} active schemes. {ready.length > 0 ? `${ready.length} meet every requirement we can check automatically.` : "None clear every automatic check yet."}</>}
      />

      {feed.suggested_profile_additions.length > 0 && (
        <aside className="notice border-unverified-border bg-unverified-bg text-unverified-fg">
          <p className="font-semibold">Add {humaniseField(feed.suggested_profile_additions[0]!)} to settle the most open requirements</p>
          {feed.suggested_profile_additions.length > 1 && <p className="mt-1 text-xs">Then: {feed.suggested_profile_additions.slice(1).map(humaniseField).join(", ")}.</p>}
          <Link href="/onboarding" className="mt-2 inline-flex min-h-11 items-center font-semibold text-brand hover:underline">Update profile <span aria-hidden="true" className="ml-1">→</span></Link>
        </aside>
      )}

      {feed.matches.length === 0 && (
        <section className="panel p-8 text-center">
          <h2 className="section-title">No scheme currently matches your profile</h2>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-ink-muted">That is usually fixable rather than final. A missing Udyam or DPIIT registration—or a sparse profile—can gate much of the corpus.</p>
          <Link href="/onboarding" className="button-primary mt-5">Review your profile</Link>
        </section>
      )}

      {ready.length > 0 && (
        <section className="space-y-4" aria-labelledby="ready-heading">
          <SectionHeading eyebrow="Best place to start" title="Every checkable requirement met" id="ready-heading" />
          {ready.map((match) => <SchemeCard key={match.scheme_version_id} match={match} />)}
        </section>
      )}

      {partial.length > 0 && (
        <section className="space-y-4" aria-labelledby="partial-heading">
          <SectionHeading eyebrow="Needs evidence" title="Possible, with open questions" id="partial-heading" />
          {partial.map((match) => <SchemeCard key={match.scheme_version_id} match={match} />)}
        </section>
      )}

      {feed.ruled_out.length > 0 && (
        <section className="panel overflow-hidden" aria-labelledby="ruled-out-heading">
          <div className="p-5 sm:p-6">
            <button
              id="ruled-out-heading"
              type="button"
              onClick={() => setShowRuledOut((value) => !value)}
              aria-expanded={showRuledOut}
              aria-controls={ruledOutId}
              className="flex min-h-11 w-full items-center justify-between gap-4 text-left text-sm font-semibold text-ink hover:text-brand"
            >
              <span>{showRuledOut ? "Hide" : "Show"} {feed.ruled_out.length} schemes you do not currently qualify for</span>
              <span aria-hidden="true" className="data-value text-lg text-brand">{showRuledOut ? "−" : "+"}</span>
            </button>
            <p className="mt-1 text-xs leading-5 text-ink-subtle">Kept visible on purpose. Knowing you are one registration away is more useful than the opportunity silently disappearing.</p>
          </div>
          {showRuledOut && (
            <div id={ruledOutId} className="divide-y divide-surface-border border-t border-surface-border bg-surface-sunken/40">
              {feed.ruled_out.map((match) => <RuledOutCard key={match.scheme_version_id} match={match} />)}
            </div>
          )}
        </section>
      )}

      <p className="notice border-info-border bg-info-bg text-xs text-info-fg">{feed.disclaimer}</p>
    </div>
  );
}
