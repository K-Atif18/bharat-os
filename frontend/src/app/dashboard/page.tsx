"use client";

/*
THESIS: The dashboard is an instrument readout of one applicant's real
funding position — assessed/met/open counts as tabular data, matches as
labeled status panels — refusing the generic stat-tile-plus-card-grid
dashboard template.
OWN-WORLD: Field system — black ground, monospace type, hairline rules,
tabular readouts, one reserved accent for ruled-out/blocked states.
STORY: A returning applicant sees their real numbers first (schemes
assessed, fully met, worth a look), then reads their actual matches
grouped by how close each is to actionable, with a ruled-out section
kept visible rather than hidden — the same trust posture as the rest of
this redesign.
FIRST VIEWPORT: FieldNav, then a readout strip (assessed / fully met /
worth a look) beside the profile identity, then the pipeline caption
inherited from the landing page's method section.
FORM: Rollout of the field-system direction already committed for the
application workspace (seed key ca281bee, index 3, data-sublime/Ikeda
family) — this page extends that established world rather than running
a new direction roll, per the redesign's own "extend an established
surface" rule.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md.
*/

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { FieldNav } from "@/components/FieldNav";
import { RuledOutCard, SchemeCard } from "@/components/SchemeCard";
import { FieldLoadingState, FieldSectionHeading } from "@/components/Ui";
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
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <div role="alert" className="field-panel field-panel-active mx-auto max-w-3xl p-6">
            <p className="font-semibold text-field-fg">{error}</p>
            <p className="mt-1 text-sm text-field-fg-muted">
              If the API is not running, start it with <code className="font-field">make dev-backend</code>.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!feed || !profile) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <FieldLoadingState label="Checking your business against every scheme" />
        </div>
      </div>
    );
  }

  const ready = feed.matches.filter((match) => match.outcome === "eligible");
  const partial = feed.matches.filter((match) => match.outcome !== "eligible");

  return (
    <div className="field-shell">
      <FieldNav />

      <main className="field-page space-y-8">
        <section className="field-section-label">
          <span className="field-index">01</span>
          <span>WORKSPACE</span>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:items-start lg:gap-10">
          <div>
            <p className="font-field text-xs uppercase tracking-[0.14em] text-field-fg-muted">FUNDING COMMAND CENTRE</p>
            <h1 className="field-display mt-2">{profile.entity_name}</h1>
            <p className="mt-2 text-sm text-field-fg-muted sm:text-base">
              {profile.district ? `${profile.district}, ` : ""}{profile.state} · {humaniseField(profile.sector)}
              {profile.employee_count !== null && ` · ${profile.employee_count} employees`}
            </p>
            {profile.registrations.length > 0 && (
              <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1 font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-subtle" aria-label="Registrations">
                {profile.registrations.map((registration) => (
                  <li key={registration}>{humaniseField(registration)}</li>
                ))}
              </ul>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              <Link href="/onboarding" className="field-button">EDIT PROFILE</Link>
              <Link href="/settings" className="field-button">PRIVACY &amp; DATA</Link>
            </div>
          </div>

          <div className="field-panel px-4 py-1 sm:px-6">
            <div className="field-readout">
              <span className="field-readout-label">ASSESSED</span>
              <span className="field-readout-value">{feed.schemes_assessed}</span>
            </div>
            <div className="field-readout">
              <span className="field-readout-label">FULLY MET</span>
              <span className="field-readout-value">{ready.length}</span>
            </div>
            <div className="field-readout">
              <span className="field-readout-label">WORTH A LOOK</span>
              <span className="field-readout-value">{feed.matches.length}</span>
            </div>
          </div>
        </div>

        <div className="field-wave-rule" role="separator" aria-hidden="true" />

        <p className="font-field text-xs uppercase tracking-[0.1em] text-field-fg-muted">
          MATCH → VERIFY → PREPARE → DRAFT — every stage stays reviewable
        </p>

        <FieldSectionHeading
          index="02"
          title="YOUR MATCHES"
          description={
            <>
              Checked your profile against {feed.schemes_assessed} active schemes.{" "}
              {ready.length > 0
                ? `${ready.length} meet every requirement we can check automatically.`
                : "None clear every automatic check yet."}
            </>
          }
        />

        {feed.suggested_profile_additions.length > 0 && (
          <aside className="field-panel field-panel-active p-4">
            <p className="font-semibold text-field-fg">
              Add {humaniseField(feed.suggested_profile_additions[0]!)} to settle the most open requirements
            </p>
            {feed.suggested_profile_additions.length > 1 && (
              <p className="mt-1 text-xs text-field-fg-muted">
                Then: {feed.suggested_profile_additions.slice(1).map(humaniseField).join(", ")}.
              </p>
            )}
            <Link href="/onboarding" className="mt-2 inline-flex min-h-11 items-center font-field text-xs font-semibold uppercase text-field-fg hover:text-field-fg-muted">
              UPDATE PROFILE <span aria-hidden="true" className="ml-1">→</span>
            </Link>
          </aside>
        )}

        {feed.matches.length === 0 && (
          <section className="field-panel p-8 text-center">
            <h2 className="font-field text-lg font-semibold uppercase text-field-fg">No scheme currently matches your profile</h2>
            <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-field-fg-muted">
              That is usually fixable rather than final. A missing Udyam or DPIIT registration—or a sparse profile—can gate much of the corpus.
            </p>
            <Link href="/onboarding" className="field-button field-button-primary mt-5">REVIEW YOUR PROFILE</Link>
          </section>
        )}

        {ready.length > 0 && (
          <section className="space-y-4" aria-labelledby="ready-heading">
            <FieldSectionHeading index="03" title="EVERY CHECKABLE REQUIREMENT MET" id="ready-heading" />
            {ready.map((match) => <SchemeCard key={match.scheme_version_id} match={match} />)}
          </section>
        )}

        {partial.length > 0 && (
          <section className="space-y-4" aria-labelledby="partial-heading">
            <FieldSectionHeading index="04" title="POSSIBLE, WITH OPEN QUESTIONS" id="partial-heading" />
            {partial.map((match) => <SchemeCard key={match.scheme_version_id} match={match} />)}
          </section>
        )}

        {feed.ruled_out.length > 0 && (
          <section className="field-panel overflow-hidden" aria-labelledby="ruled-out-heading">
            <div className="p-5 sm:p-6">
              <button
                id="ruled-out-heading"
                type="button"
                onClick={() => setShowRuledOut((value) => !value)}
                aria-expanded={showRuledOut}
                aria-controls={ruledOutId}
                className="flex min-h-11 w-full items-center justify-between gap-4 text-left font-field text-sm font-semibold uppercase text-field-fg hover:text-field-fg-muted"
              >
                <span>{showRuledOut ? "HIDE" : "SHOW"} {feed.ruled_out.length} SCHEMES YOU DO NOT CURRENTLY QUALIFY FOR</span>
                <span aria-hidden="true" className="font-field text-lg">{showRuledOut ? "−" : "+"}</span>
              </button>
              <p className="mt-1 text-xs leading-5 text-field-fg-subtle">
                Kept visible on purpose. Knowing you are one registration away is more useful than the opportunity silently disappearing.
              </p>
            </div>
            {showRuledOut && (
              <div id={ruledOutId} className="divide-y divide-field-rule border-t border-field-rule">
                {feed.ruled_out.map((match) => <RuledOutCard key={match.scheme_version_id} match={match} />)}
              </div>
            )}
          </section>
        )}

        <p className="field-panel p-4 font-field text-[11px] uppercase leading-6 tracking-[0.04em] text-field-fg-muted">
          {feed.disclaimer}
        </p>
      </main>
    </div>
  );
}
