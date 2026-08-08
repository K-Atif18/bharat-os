"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthForm } from "@/components/AuthForm";
import { LoadingState } from "@/components/Ui";
import { getAccount } from "@/lib/api";

const SCHEME_COUNT = 40;

/**
 * Landing page — the one marketing surface in this product.
 *
 * Every other page in Bharat OS is a repeated-use operational tool and is
 * deliberately dense/scannable rather than editorial-first (see the design
 * direction note in the redesign plan). This page carries the full craft
 * budget: asymmetric composition, one oversized numeral as the bold moment,
 * monospace metadata throughout, and enough specific, checkable detail that
 * it reads as a dossier rather than a pitch.
 */
export default function HomePage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    getAccount()
      .then((account) => router.replace(account.has_profile ? "/dashboard" : "/onboarding"))
      .catch(() => setChecking(false));
  }, [router]);

  if (checking) {
    return <LoadingState label="Checking your session" />;
  }

  return (
    <div className="pb-6">
      {/* ---------------------------------------------------------------
       * Fold 1 — asymmetric masthead. The bold moment is the oversized
       * "40" — a specific, checkable number, not a decorative numeral.
       * No centered headline/subhead/two-button block anywhere here.
       * --------------------------------------------------------------- */}
      <section className="grid gap-10 border-b border-surface-strong pb-10 lg:grid-cols-editorial-a lg:gap-14 lg:pb-14">
        <div className="pt-1">
          <div className="flex items-baseline gap-3">
            <span className="meta-line">Vol. 01 — Government process intelligence</span>
            <span className="meta-line text-brand">Working MVP</span>
          </div>

          <h1 className="mt-5 max-w-xl font-display text-[clamp(2.1rem,4.4vw,3.4rem)] font-semibold leading-[1.05] tracking-tightest text-ink">
            Find the scheme.
            <br />
            Prove the fit.
            <br />
            Prepare the filing.
          </h1>

          <p className="lede mt-6 max-w-lg">
            <strong>Bharat OS turns one business profile into a ranked, sourced, and
            draftable path</strong> through India&apos;s government funding schemes —
            checked against {SCHEME_COUNT} curated programmes, not summarised from
            memory.
          </p>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-end sm:gap-8">
            <span className="bold-moment text-brand">{SCHEME_COUNT}</span>
            <div className="pb-1">
              <p className="font-semibold text-ink">schemes in the working corpus</p>
              <p className="mt-1 max-w-[26ch] text-sm leading-5 text-ink-muted">
                Each with hard rules, sourced criteria, and document requirements — not a directory listing.
              </p>
            </div>
          </div>

          <dl className="folio-rule mt-10 grid grid-cols-[auto_1fr_1fr] gap-x-4 gap-y-3" data-folio="Dossier — Live example">
            <div className="col-span-3 flex items-center gap-3">
              <span aria-hidden="true" className="grid h-8 w-8 shrink-0 place-items-center bg-civic-navy font-display text-xs font-semibold text-white">Z</span>
              <div>
                <dt className="font-semibold text-ink">ZEN Club</dt>
                <dd className="meta-line mt-0.5">Pune, Maharashtra</dd>
              </div>
            </div>
            <div className="col-start-1 col-end-2 ml-11">
              <dt className="meta-line">Sector</dt>
              <dd className="mt-0.5 text-sm text-ink">Logistics</dd>
            </div>
            <div>
              <dt className="meta-line">Employees</dt>
              <dd className="mt-0.5 text-sm text-ink">12</dd>
            </div>
            <div>
              <dt className="meta-line">Turnover</dt>
              <dd className="mt-0.5 text-sm text-ink">₹18L</dd>
            </div>
            <div className="col-span-3 ml-11 mt-1">
              <dt className="meta-line">DPIIT status</dt>
              <dd className="mt-0.5 text-sm leading-6 text-ink-muted">
                Recognised. This is the exact account state the judge demo
                below provisions — inspect the same eligibility reasoning
                end to end, not a scripted walkthrough.
              </dd>
            </div>
          </dl>
        </div>

        <AuthForm />
      </section>

      {/* ---------------------------------------------------------------
       * Fold 2 — the pipeline, rendered as an annotated sequence rather
       * than a 4-up icon grid. Numbers are index marks, not badges.
       * --------------------------------------------------------------- */}
      <section aria-labelledby="execution-flow" className="split-b border-b border-surface-strong py-10 lg:py-14">
        <div>
          <p className="meta-line">§1 · Method</p>
          <h2 className="mt-3 font-display text-2xl font-semibold leading-tight tracking-[-0.02em] text-ink sm:text-3xl">
            From profile facts to a filing-ready workspace
          </h2>
          <p className="mt-4 max-w-sm text-sm leading-6 text-ink-muted">
            Four stages, each leaving its evidence visible. Nothing here
            becomes more certain merely because an AI model was involved in
            producing it — every soft judgement is labelled as a judgement,
            not a fact.
          </p>
        </div>

        <ol className="divide-y divide-surface-border border-t border-surface-strong sm:border-t-0">
          <li className="grid grid-cols-[2.5rem_1fr] gap-x-4 gap-y-1 py-5 sm:grid-cols-[2.5rem_9rem_1fr] sm:items-baseline">
            <span className="index-mark">01</span>
            <h3 className="font-display text-base font-semibold text-ink sm:text-lg">Match</h3>
            <p className="col-span-2 text-sm leading-6 text-ink-muted sm:col-span-1">
              Every one of the {SCHEME_COUNT} active schemes is ranked against
              one consistent profile — confidence × benefit value × filing
              difficulty, computed the same way for every user.
            </p>
          </li>
          <li className="grid grid-cols-[2.5rem_1fr] gap-x-4 gap-y-1 py-5 sm:grid-cols-[2.5rem_9rem_1fr] sm:items-baseline">
            <span className="index-mark">02</span>
            <h3 className="font-display text-base font-semibold text-ink sm:text-lg">Verify</h3>
            <p className="col-span-2 text-sm leading-6 text-ink-muted sm:col-span-1">
              Hard eligibility rules run as deterministic code — Kleene
              three-valued logic, no model involved. Soft criteria go through
              a labelled AI judgement with a confidence score and audit trail.
            </p>
          </li>
          <li className="grid grid-cols-[2.5rem_1fr] gap-x-4 gap-y-1 py-5 sm:grid-cols-[2.5rem_9rem_1fr] sm:items-baseline">
            <span className="index-mark">03</span>
            <h3 className="font-display text-base font-semibold text-ink sm:text-lg">Prepare</h3>
            <p className="col-span-2 text-sm leading-6 text-ink-muted sm:col-span-1">
              Missing documents and filing lead times become a critical path:
              what to gather, in what order, before which window closes.
            </p>
          </li>
          <li className="grid grid-cols-[2.5rem_1fr] gap-x-4 gap-y-1 py-5 sm:grid-cols-[2.5rem_9rem_1fr] sm:items-baseline">
            <span className="index-mark">04</span>
            <h3 className="font-display text-base font-semibold text-ink sm:text-lg">Draft</h3>
            <p className="col-span-2 text-sm leading-6 text-ink-muted sm:col-span-1">
              An editable workspace with every field labelled by source —
              profile-sourced, AI-drafted, or requiring you personally.
              Nothing is ever filed on your behalf.
            </p>
          </li>
        </ol>
      </section>

      {/* ---------------------------------------------------------------
       * Fold 3 — trust model. Kept as an asymmetric navy/paper split,
       * but rewritten with more specific, checkable claims and fewer
       * abstractions.
       * --------------------------------------------------------------- */}
      <section aria-labelledby="trust-model" className="grid overflow-hidden border-b border-surface-strong lg:grid-cols-editorial-c">
        <div className="bg-civic-navy px-5 py-10 text-white sm:px-8 sm:py-14 lg:col-span-1">
          <p className="meta-line text-orange-200">§2 · Why the numbers are conservative</p>
          <h2 id="trust-model" className="mt-4 max-w-[16ch] font-display text-3xl font-semibold leading-[1.08] tracking-tightest sm:text-4xl">
            Confidence is measured, not performed.
          </h2>
        </div>

        <dl className="col-span-2 divide-y divide-surface-border bg-surface py-2 lg:col-span-2 lg:py-0">
          <div className="grid gap-2 py-6 sm:grid-cols-[13rem_1fr] sm:gap-6 lg:py-8">
            <dt className="font-mono text-xs font-semibold uppercase tracking-[0.1em] text-brand">Missing data</dt>
            <dd className="text-sm leading-6 text-ink-muted">
              Reported as <span className="font-mono text-ink">cannot_verify</span>,
              a distinct third state from met and unmet. A gap in your profile
              is never silently treated as a failed eligibility check.
            </dd>
          </div>
          <div className="grid gap-2 py-6 sm:grid-cols-[13rem_1fr] sm:gap-6 lg:py-8">
            <dt className="font-mono text-xs font-semibold uppercase tracking-[0.1em] text-brand">Every sourced claim</dt>
            <dd className="text-sm leading-6 text-ink-muted">
              Carries the official source URL and the date a human last
              verified it against that source — visible on the criterion,
              not buried in a footnote.
            </dd>
          </div>
          <div className="grid gap-2 py-6 sm:grid-cols-[13rem_1fr] sm:gap-6 lg:py-8">
            <dt className="font-mono text-xs font-semibold uppercase tracking-[0.1em] text-brand">Every draft</dt>
            <dd className="text-sm leading-6 text-ink-muted">
              Stays in an applicant-reviewed workspace with no code path that
              submits to a government portal. You file it; we prepare it.
            </dd>
          </div>
        </dl>
      </section>

      <footer className="folio-rule mt-10 flex flex-col gap-1 pb-2 sm:flex-row sm:items-baseline sm:justify-between" data-folio="§3 · Standing notice">
        <p className="max-w-xl text-sm font-medium leading-6 text-ink">
          Bharat OS is an advisory tool, not legal or financial advice.
        </p>
        <p className="meta-line">Scheme terms change — confirm every criterion against its linked source.</p>
      </footer>
    </div>
  );
}
