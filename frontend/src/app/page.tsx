"use client";

/*
THESIS: The landing page proves the product is a real running system by
booting like one — a live typed sequence of actual, checkable facts (real
scheme count, real pipeline stages) — refusing the static hero-headline-
plus-button block every AI-product marketing page ships.
OWN-WORLD: Green-phosphor CRT terminal — near-black ground, one committed
phosphor green carrying body text, rules, glow and motion; monospace type
throughout; scanline/vignette texture, a persistent falling-digit
background, and a blinking block cursor.
STORY: A visitor lands on a page with digits quietly falling in the
background, watches the system "boot" (real facts typing out line by
line, each resolving to OK), then reads the same four-stage method and
trust claims the previous editorial redesign already proved out — now
delivered with the warmth and motion a Persuade surface is allowed and
an Operate surface is not. The headline itself glitches briefly and
periodically, signalling a live system rather than a static image.
FIRST VIEWPORT: Boot sequence typing out at the top over the falling-
digit background, resolving into the headline (with its periodic glitch)
and the live ZEN Club dossier readout; the auth panel sits beside it,
restyled to the terminal grammar but with its real form fields, labels
and consent copy left untouched.
FORM: Fused challenger (green-phosphor terminal, signals-instruments
family) over the assigned direction (indoor weather sun) — index 5 of
the persuade-mode direction roll, seed key 823d3388. Reveal motion
(typewriter boot + fade) chosen by the user after a live side-by-side
comparison against four alternates (cascade, glitch-snap, matrix-decode,
radial-iris); falling-digit background and headline glitch added after
as explicit user-requested embellishments on the winning variant.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md.
*/

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthForm } from "@/components/AuthForm";
import { LoadingState } from "@/components/Ui";
import { MatrixRain } from "@/components/MatrixRain";
import { BootLine, TerminalBoot } from "@/components/TerminalBoot";
import { getAccount } from "@/lib/api";

const SCHEME_COUNT = 40;

const BOOT_LINES: BootLine[] = [
  { text: "bharat_os --init", status: "" },
  { text: `loading scheme corpus (${SCHEME_COUNT} programmes)`, status: "OK" },
  { text: "eligibility engine: kleene three-valued logic", status: "OK" },
  { text: "soft-criteria judge: confidence-scored, audited", status: "OK" },
  { text: "draft generator: profile / ai / human_required", status: "OK" },
  { text: "session ready.", status: "" },
];

export default function HomePage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [bootDone, setBootDone] = useState(false);

  useEffect(() => {
    getAccount()
      .then((account) => router.replace(account.has_profile ? "/dashboard" : "/onboarding"))
      .catch(() => setChecking(false));
  }, [router]);

  if (checking) {
    return <LoadingState label="Checking your session" />;
  }

  return (
    <div className="terminal-shell">
      <MatrixRain />

      <nav className="terminal-nav">
        <span className="terminal-glow font-semibold uppercase tracking-[0.1em]">
          BHARAT_OS
        </span>
        <span className="terminal-faint text-xs uppercase tracking-[0.14em]">
          Government process intelligence
        </span>
      </nav>

      <main className="terminal-page">
        {/* -------------------------------------------------------------
         * Fold 1 — the boot sequence and masthead. The typed lines are
         * real, checkable facts about the running system, not filler.
         * ------------------------------------------------------------- */}
        <section className="relative grid gap-10 border-b terminal-rule pb-10 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] lg:gap-14 lg:pb-14">
          <div className="relative z-10 pt-1">
            <TerminalBoot lines={BOOT_LINES} onDone={() => setBootDone(true)} />

            <h1
              className={`terminal-headline-glitch mt-8 max-w-xl font-field text-[clamp(2rem,4.6vw,3.6rem)] font-semibold uppercase leading-[1.05] transition-opacity duration-700 ${
                bootDone ? "opacity-100" : "opacity-0"
              }`}
            >
              <span className="terminal-glow-strong">Find the scheme.</span>
              <br />
              <span className="terminal-glow-strong">Prove the fit.</span>
              <br />
              <span className="terminal-glow-strong">Prepare the filing.</span>
            </h1>

            <p
              className={`mt-6 max-w-lg text-sm leading-6 text-terminal-fg transition-opacity delay-200 duration-700 ${
                bootDone ? "opacity-100" : "opacity-0"
              }`}
            >
              Bharat OS turns one business profile into a ranked, sourced, and
              draftable path through India&apos;s government funding schemes —
              checked against {SCHEME_COUNT} curated programmes, not
              summarised from memory.
            </p>

            <div
              className={`mt-9 terminal-panel p-5 transition-opacity delay-300 duration-700 ${
                bootDone ? "opacity-100" : "opacity-0"
              }`}
            >
              <p className="terminal-faint text-[10px] uppercase tracking-[0.16em]">
                {"// live example — dossier"}
              </p>
              <div className="mt-3 flex items-baseline gap-3">
                <span className="font-field text-4xl font-semibold terminal-glow-strong">Z</span>
                <div>
                  <p className="font-semibold text-terminal-fg">ZEN Club</p>
                  <p className="terminal-faint text-xs">Pune, Maharashtra</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-4 text-xs">
                <div>
                  <p className="terminal-faint uppercase tracking-[0.08em]">Sector</p>
                  <p className="mt-1 text-terminal-fg">Logistics</p>
                </div>
                <div>
                  <p className="terminal-faint uppercase tracking-[0.08em]">Employees</p>
                  <p className="mt-1 text-terminal-fg">12</p>
                </div>
                <div>
                  <p className="terminal-faint uppercase tracking-[0.08em]">Turnover</p>
                  <p className="mt-1 text-terminal-fg">₹18L</p>
                </div>
              </div>
              <p className="mt-4 border-t border-terminal-shadow pt-3 text-xs leading-6 terminal-muted">
                DPIIT recognised. This is the exact account state the judge
                demo below provisions — inspect the same eligibility
                reasoning end to end, not a scripted walkthrough.
              </p>
            </div>
          </div>

          <div
            className={`relative z-10 transition-opacity delay-500 duration-700 ${
              bootDone ? "opacity-100" : "opacity-0"
            }`}
          >
            <AuthForm />
          </div>
        </section>

        {/* -------------------------------------------------------------
         * Fold 2 — the pipeline, as a numbered log rather than an icon
         * grid, matching the boot-sequence grammar established above.
         * ------------------------------------------------------------- */}
        <section aria-labelledby="execution-flow" className="relative z-10 border-b terminal-rule py-10 lg:py-14">
          <p className="terminal-faint text-xs uppercase tracking-[0.14em]">{"// method"}</p>
          <h2
            id="execution-flow"
            className="mt-3 font-field text-xl font-semibold uppercase terminal-glow sm:text-2xl"
          >
            From profile facts to a filing-ready workspace
          </h2>
          <p className="mt-4 max-w-lg text-sm leading-6 terminal-muted">
            Four stages, each leaving its evidence visible. Nothing here
            becomes more certain merely because an AI model was involved in
            producing it — every soft judgement is labelled as a judgement,
            not a fact.
          </p>

          <ol className="mt-8 divide-y divide-terminal-shadow border-t border-terminal-shadow">
            {[
              {
                n: "01",
                title: "Match",
                body: `Every one of the ${SCHEME_COUNT} active schemes is ranked against one consistent profile — confidence × benefit value × filing difficulty, computed the same way for every user.`,
              },
              {
                n: "02",
                title: "Verify",
                body: "Hard eligibility rules run as deterministic code — Kleene three-valued logic, no model involved. Soft criteria go through a labelled AI judgement with a confidence score and audit trail.",
              },
              {
                n: "03",
                title: "Prepare",
                body: "Missing documents and filing lead times become a critical path: what to gather, in what order, before which window closes.",
              },
              {
                n: "04",
                title: "Draft",
                body: "An editable workspace with every field labelled by source — profile-sourced, AI-drafted, or requiring you personally. Nothing is ever filed on your behalf.",
              },
            ].map((step) => (
              <li
                key={step.n}
                className="grid grid-cols-[3rem_1fr] gap-x-4 gap-y-1 py-5 sm:grid-cols-[3rem_9rem_1fr] sm:items-baseline"
              >
                <span className="terminal-glow font-semibold">{step.n}</span>
                <h3 className="font-field text-sm font-semibold uppercase text-terminal-fg sm:text-base">
                  {step.title}
                </h3>
                <p className="col-span-2 text-sm leading-6 terminal-muted sm:col-span-1">{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* -------------------------------------------------------------
         * Fold 3 — trust model, kept as real, checkable claims.
         * ------------------------------------------------------------- */}
        <section aria-labelledby="trust-model" className="relative z-10 border-b terminal-rule py-10 lg:py-14">
          <p className="terminal-faint text-xs uppercase tracking-[0.14em]">{"// why the numbers are conservative"}</p>
          <h2 id="trust-model" className="mt-3 max-w-[26ch] font-field text-xl font-semibold uppercase terminal-glow sm:text-2xl">
            Confidence is measured, not performed.
          </h2>

          <dl className="mt-8 divide-y divide-terminal-shadow border-t border-terminal-shadow">
            <div className="grid gap-2 py-6 sm:grid-cols-[13rem_1fr] sm:gap-6">
              <dt className="font-field text-xs font-semibold uppercase tracking-[0.1em] terminal-glow">Missing data</dt>
              <dd className="text-sm leading-6 terminal-muted">
                Reported as <span className="font-field text-terminal-fg">cannot_verify</span>,
                a distinct third state from met and unmet. A gap in your profile is never
                silently treated as a failed eligibility check.
              </dd>
            </div>
            <div className="grid gap-2 py-6 sm:grid-cols-[13rem_1fr] sm:gap-6">
              <dt className="font-field text-xs font-semibold uppercase tracking-[0.1em] terminal-glow">Every sourced claim</dt>
              <dd className="text-sm leading-6 terminal-muted">
                Carries the official source URL and the date a human last verified it against
                that source — visible on the criterion, not buried in a footnote.
              </dd>
            </div>
            <div className="grid gap-2 py-6 sm:grid-cols-[13rem_1fr] sm:gap-6">
              <dt className="font-field text-xs font-semibold uppercase tracking-[0.1em] terminal-glow">Every draft</dt>
              <dd className="text-sm leading-6 terminal-muted">
                Stays in an applicant-reviewed workspace with no code path that submits to a
                government portal. You file it; we prepare it.
              </dd>
            </div>
          </dl>
        </section>

        <footer className="relative z-10 flex flex-col gap-1 py-6 text-xs sm:flex-row sm:items-baseline sm:justify-between">
          <p className="max-w-xl leading-6 text-terminal-fg">
            Bharat OS is an advisory tool, not legal or financial advice.
          </p>
          <p className="terminal-faint uppercase tracking-[0.08em]">
            Scheme terms change — confirm every criterion against its linked source.
          </p>
        </footer>
      </main>
    </div>
  );
}
