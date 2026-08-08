"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthForm } from "@/components/AuthForm";
import { LoadingState, SectionHeading } from "@/components/Ui";
import { getAccount } from "@/lib/api";

const PROOF_POINTS = [
  { value: "15", label: "curated schemes", detail: "Primary-source backed" },
  { value: "3", label: "draft workflows", detail: "Scheme-specific fields" },
  { value: "0", label: "automatic filings", detail: "Human control stays final" },
];

const FLOW = [
  ["01", "Match", "Rank every active scheme against one consistent business profile."],
  ["02", "Verify", "Separate deterministic rules from labelled AI judgement and evidence."],
  ["03", "Prepare", "Turn document gaps and lead times into an application critical path."],
  ["04", "Draft", "Build an editable workspace without pretending anything was submitted."],
];

const TRUST = [
  ["Missing data", "Reported as cannot verify — never treated as a failed criterion."],
  ["Every claim", "Linked to its official source and human verification date."],
  ["Every draft", "Kept under applicant review with no automatic submission path."],
];

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
    <div className="page-stack pb-4">
      <section className="grid items-start gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)] lg:gap-12">
        <div className="pt-2 lg:pt-8">
          <p className="eyebrow">Government process intelligence · Working MVP</p>
          <h1 className="display-title mt-4 max-w-4xl">
            Find the scheme. Prove the fit. Prepare the application.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-ink-muted sm:text-lg sm:leading-8">
            Bharat OS turns one startup or MSME profile into ranked opportunities, sourced
            eligibility reasoning, a document action plan, and a reviewable first draft.
          </p>

          <div className="mt-7 border-y border-surface-strong py-5">
            <div className="flex items-start gap-4">
              <span aria-hidden="true" className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-civic-navy font-display text-sm font-semibold text-white">Z</span>
              <div>
                <p className="font-semibold text-ink">Live dossier · ZEN Club</p>
                <p className="mt-1 max-w-xl text-sm leading-6 text-ink-muted">
                  A DPIIT-recognised logistics startup in Pune, with 12 employees and ₹18 lakh
                  turnover. Launch the same authenticated journey judges can inspect end to end.
                </p>
              </div>
            </div>
          </div>

          <dl className="mt-6 grid grid-cols-3 divide-x divide-surface-strong border-y border-surface-strong py-4">
            {PROOF_POINTS.map((point) => (
              <div key={point.label} className="px-3 first:pl-0 last:pr-0 sm:px-5">
                <dt className="data-value text-2xl font-semibold text-civic-navy sm:text-3xl">{point.value}</dt>
                <dd className="mt-1 text-xs font-semibold text-ink sm:text-sm">{point.label}</dd>
                <dd className="mt-1 hidden text-xs text-ink-subtle sm:block">{point.detail}</dd>
              </div>
            ))}
          </dl>
        </div>

        <AuthForm />
      </section>

      <section aria-labelledby="execution-flow" className="border-t border-surface-strong pt-9 sm:pt-12">
        <SectionHeading
          eyebrow="One accountable path"
          title="From profile facts to a filing-ready workspace"
          description="Each stage leaves its evidence visible. Nothing becomes more certain merely because an AI was involved."
          id="execution-flow"
        />
        <ol className="mt-7 grid border-y border-surface-strong sm:grid-cols-2 lg:grid-cols-4">
          {FLOW.map(([number, title, detail], index) => (
            <li
              key={number}
              className={`relative px-1 py-5 sm:px-5 ${index > 0 ? "border-t border-surface-border sm:border-t-0 sm:border-l" : ""}`}
            >
              <span className="data-value text-xs font-semibold text-brand">{number}</span>
              <h3 className="mt-3 font-display text-xl font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-ink-muted">{detail}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="trust-model" className="panel overflow-hidden lg:grid lg:grid-cols-[0.72fr_1.28fr]">
        <div className="bg-civic-navy p-6 text-white sm:p-8">
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-orange-200">Designed for consequential decisions</p>
          <h2 id="trust-model" className="mt-3 font-display text-3xl font-semibold leading-tight">Confidence should be earned, not performed.</h2>
          <p className="mt-4 text-sm leading-6 text-slate-300">The product’s strongest claims are bounded by what the profile and official sources can actually establish.</p>
        </div>
        <dl className="divide-y divide-surface-border bg-surface px-6 sm:px-8">
          {TRUST.map(([term, detail]) => (
            <div key={term} className="grid gap-1 py-5 sm:grid-cols-[150px_1fr] sm:gap-5">
              <dt className="font-semibold text-ink">{term}</dt>
              <dd className="text-sm leading-6 text-ink-muted">{detail}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
