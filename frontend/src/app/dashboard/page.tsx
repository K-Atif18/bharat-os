"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { RuledOutCard, SchemeCard } from "@/components/SchemeCard";
import { LoadingState, SectionHeading } from "@/components/Ui";
import { ApiError, getMatches, getProfile, type MatchFeed, type Profile } from "@/lib/api";
import { humaniseField } from "@/lib/format";

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
      {/* Masthead: asymmetric — profile identity on the left, the three
         load-bearing numbers on the right as a tight ledger rather than
         three equal-weight stat tiles. */}
      <section className="folio-rule" data-folio="Workspace">
        <div className="grid gap-6 lg:grid-cols-editorial-b lg:items-start lg:gap-10">
          <div>
            <p className="eyebrow">Funding command centre</p>
            <h1 className="page-title mt-2">{profile.entity_name}</h1>
            <p className="mt-2 text-sm text-ink-muted sm:text-base">
              {profile.district ? `${profile.district}, ` : ""}{profile.state} · {humaniseField(profile.sector)}
              {profile.employee_count !== null && ` · ${profile.employee_count} employees`}
            </p>
            {profile.registrations.length > 0 && (
              <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1" aria-label="Registrations">
                {profile.registrations.map((registration) => (
                  <li key={registration} className="meta-line">{humaniseField(registration)}</li>
                ))}
              </ul>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              <Link href="/onboarding" className="button-secondary">Edit profile</Link>
              <Link href="/settings" className="button-quiet">Privacy &amp; data</Link>
            </div>
          </div>

          <dl className="grid grid-cols-3 divide-x divide-surface-strong border border-surface-strong">
            <div className="px-3 py-4 sm:px-5">
              <dt className="meta-line">Assessed</dt>
              <dd className="data-value mt-1 text-2xl font-semibold text-civic-navy sm:text-3xl">{feed.schemes_assessed}</dd>
            </div>
            <div className="px-3 py-4 sm:px-5">
              <dt className="meta-line">Fully met</dt>
              <dd className="data-value mt-1 text-2xl font-semibold text-met-fg sm:text-3xl">{ready.length}</dd>
            </div>
            <div className="px-3 py-4 sm:px-5">
              <dt className="meta-line">Worth a look</dt>
              <dd className="data-value mt-1 text-2xl font-semibold text-ink sm:text-3xl">{feed.matches.length}</dd>
            </div>
          </dl>
        </div>
      </section>

      {/* Pipeline: an inline annotated sequence rather than a 4-up card
         grid — same information, less "dashboard template" shape. */}
      <p className="meta-line -mb-2">
        Match <span className="text-ink-subtle">→</span> Verify <span className="text-ink-subtle">→</span> Prepare <span className="text-ink-subtle">→</span> Draft
        <span className="ml-2 text-ink-subtle">— every stage stays reviewable</span>
      </p>

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
