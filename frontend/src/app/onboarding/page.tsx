"use client";

/*
THESIS: The business-profile form is an intake ledger, not a marketing
form — every field labeled plainly, every optional/sensitive distinction
stated as fact, matching the field system's instrument-panel register.
OWN-WORLD: Field system — black ground, monospace type, hairline rules.
Real form logic, validation, and every consent/data-minimization copy
string are unchanged from the civic-paper version; only the visual
language changed.
STORY: A user fills in business facts (required for matching), then
sensitive facts (turnover, category — explicitly labeled encrypted and
optional), then submits to see their real matches.
FORM: Rollout of the already-committed field-system direction (seed key
ca281bee, index 3) — this page extends that established world.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md.
*/

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FieldLoadingState, FieldPageIntro } from "@/components/Ui";
import { FieldNav } from "@/components/FieldNav";
import { ApiError, getProfile, saveProfile, type ProfileInput } from "@/lib/api";

const STATES = [
  "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
  "Madhya Pradesh", "Maharashtra", "Manipur", "Odisha", "Punjab", "Rajasthan",
  "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal",
];

const SECTORS = [
  "manufacturing", "edtech", "fintech", "healthcare", "agritech", "software",
  "information-technology", "biotechnology", "handicrafts", "traditional-crafts",
  "retail", "logistics", "services", "deeptech",
];

const STAGES = [
  { value: "idea", label: "Idea — not trading yet" },
  { value: "early", label: "Early — trading, finding product fit" },
  { value: "growth", label: "Growth — scaling a working model" },
  { value: "mature", label: "Mature — established operations" },
];

const REGISTRATIONS = [
  { value: "dpiit", label: "DPIIT startup recognition" },
  { value: "udyam", label: "Udyam (MSME) registration" },
  { value: "gst", label: "GST registration" },
  { value: "company_incorporation", label: "Company or LLP incorporation" },
  { value: "fcra", label: "FCRA registration" },
];

const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "obc", label: "OBC" },
  { value: "sc", label: "Scheduled Caste" },
  { value: "st", label: "Scheduled Tribe" },
  { value: "ews", label: "EWS" },
];

type Draft = {
  entity_name: string;
  state: string;
  district: string;
  sector: string;
  stage: string;
  employee_count: string;
  incorporation_date: string;
  is_woman_led: "" | "yes" | "no";
  registrations: string[];
  annual_turnover_inr: string;
  social_category: string;
};

const EMPTY: Draft = {
  entity_name: "", state: "", district: "", sector: "", stage: "", employee_count: "",
  incorporation_date: "", is_woman_led: "", registrations: [], annual_turnover_inr: "", social_category: "",
};

function toPayload(draft: Draft): ProfileInput {
  return {
    entity_name: draft.entity_name,
    state: draft.state,
    district: draft.district || null,
    sector: draft.sector,
    stage: draft.stage as ProfileInput["stage"],
    employee_count: draft.employee_count === "" ? null : Number(draft.employee_count),
    incorporation_date: draft.incorporation_date || null,
    is_woman_led: draft.is_woman_led === "" ? null : draft.is_woman_led === "yes",
    registrations: draft.registrations as ProfileInput["registrations"],
    annual_turnover_inr: draft.annual_turnover_inr === "" ? null : Number(draft.annual_turnover_inr),
    social_category: (draft.social_category || null) as ProfileInput["social_category"],
  };
}

export default function OnboardingPage() {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    getProfile()
      .then((profile) =>
        setDraft({
          entity_name: profile.entity_name,
          state: profile.state,
          district: profile.district ?? "",
          sector: profile.sector,
          stage: profile.stage,
          employee_count: profile.employee_count?.toString() ?? "",
          incorporation_date: profile.incorporation_date ?? "",
          is_woman_led: profile.is_woman_led === null ? "" : profile.is_woman_led ? "yes" : "no",
          registrations: profile.registrations,
          annual_turnover_inr: profile.annual_turnover_inr?.toString() ?? "",
          social_category: profile.social_category ?? "",
        }),
      )
      .catch((caught) => {
        if (caught instanceof ApiError && caught.isUnauthenticated) router.replace("/");
      })
      .finally(() => setChecking(false));
  }, [router]);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await saveProfile(toPayload(draft));
      router.push("/dashboard");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not save your profile.");
    } finally {
      setBusy(false);
    }
  }

  if (checking) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <FieldLoadingState label="Loading your business profile" />
        </div>
      </div>
    );
  }

  return (
    <div className="field-shell">
      <FieldNav />
      <main className="field-page mx-auto max-w-5xl space-y-8">
        <FieldPageIntro
          index="01"
          title="TELL US ABOUT YOUR BUSINESS"
          description={<>We ask only for facts scheme rules actually test. Optional gaps remain <strong className="text-field-fg">cannot verify</strong>—they never become an assumed failure.</>}
          actions={<Link href="/dashboard" className="field-button">BACK TO DASHBOARD</Link>}
        />

        <form onSubmit={submit} className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_280px]" aria-busy={busy}>
          <div className="space-y-6">
            <section className="field-panel p-5 sm:p-7" aria-labelledby="business-facts">
              <div className="border-b border-field-rule pb-5">
                <p className="font-field text-[11px] uppercase tracking-[0.1em] text-field-fg-muted">CORE MATCHING INPUTS</p>
                <h2 id="business-facts" className="mt-1 font-field text-lg font-semibold uppercase text-field-fg">BUSINESS FACTS</h2>
                <p className="mt-2 text-sm leading-6 text-field-fg-muted">These establish geography, sector, stage, and the registrations that gate many schemes.</p>
              </div>

              <div className="mt-6 space-y-5">
                <div>
                  <label htmlFor="entity_name" className="field-input-label">Business name</label>
                  <input id="entity_name" required value={draft.entity_name} onChange={(e) => set("entity_name", e.target.value)} className="field-input" />
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <label htmlFor="state" className="field-input-label">State</label>
                    <select id="state" required value={draft.state} onChange={(e) => set("state", e.target.value)} className="field-input">
                      <option value="">Select a state</option>
                      {STATES.map((state) => <option key={state} value={state}>{state}</option>)}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="district" className="field-input-label">District <span className="text-field-fg-subtle">(optional)</span></label>
                    <input id="district" value={draft.district} onChange={(e) => set("district", e.target.value)} className="field-input" />
                  </div>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <label htmlFor="sector" className="field-input-label">Sector</label>
                    <select id="sector" required value={draft.sector} onChange={(e) => set("sector", e.target.value)} className="field-input">
                      <option value="">Select a sector</option>
                      {SECTORS.map((sector) => <option key={sector} value={sector}>{sector.replace(/-/g, " ")}</option>)}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="stage" className="field-input-label">Stage</label>
                    <select id="stage" required value={draft.stage} onChange={(e) => set("stage", e.target.value)} className="field-input">
                      <option value="">Select a stage</option>
                      {STAGES.map((stage) => <option key={stage.value} value={stage.value}>{stage.label}</option>)}
                    </select>
                  </div>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <label htmlFor="employee_count" className="field-input-label">Employees <span className="text-field-fg-subtle">(optional)</span></label>
                    <input id="employee_count" type="number" min={0} inputMode="numeric" value={draft.employee_count} onChange={(e) => set("employee_count", e.target.value)} className="field-input" />
                  </div>
                  <div>
                    <label htmlFor="incorporation_date" className="field-input-label">Incorporation date <span className="text-field-fg-subtle">(optional)</span></label>
                    <input id="incorporation_date" type="date" value={draft.incorporation_date} onChange={(e) => set("incorporation_date", e.target.value)} aria-describedby="incorporation-hint" className="field-input" />
                    <p id="incorporation-hint" className="field-input-hint">Settles scheme age limits without asking you to calculate them.</p>
                  </div>
                </div>

                <fieldset className="border-t border-field-rule pt-5">
                  <legend className="font-field text-sm font-semibold uppercase text-field-fg">REGISTRATIONS YOU HOLD</legend>
                  <p className="mt-1 text-xs leading-5 text-field-fg-subtle">Tick none if you hold none. That is useful evidence, not a blank response.</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {REGISTRATIONS.map((registration) => (
                      <label key={registration.value} className="field-choice-row">
                        <input
                          type="checkbox"
                          checked={draft.registrations.includes(registration.value)}
                          onChange={(e) => set("registrations", e.target.checked ? [...draft.registrations, registration.value] : draft.registrations.filter((item) => item !== registration.value))}
                        />
                        <span className="font-medium text-field-fg">{registration.label}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              </div>
            </section>

            <section className="field-panel p-5 sm:p-7" aria-labelledby="sensitive-facts">
              <div className="flex gap-4 border-b border-field-rule pb-5">
                <span aria-hidden="true" className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center border border-field-rule-strong font-field text-field-fg">◇</span>
                <div>
                  <p className="font-field text-[11px] uppercase tracking-[0.1em] text-field-fg-muted">OPTIONAL AND PROTECTED</p>
                  <h2 id="sensitive-facts" className="mt-1 font-field text-lg font-semibold uppercase text-field-fg">MORE SENSITIVE FACTS</h2>
                  <p className="mt-2 text-sm leading-6 text-field-fg-muted">Encrypted before storage and excluded from logs. Skip any field and related checks remain unresolved.</p>
                </div>
              </div>

              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <div>
                  <label htmlFor="annual_turnover_inr" className="field-input-label">Annual turnover in rupees</label>
                  <input id="annual_turnover_inr" type="number" min={0} inputMode="numeric" value={draft.annual_turnover_inr} onChange={(e) => set("annual_turnover_inr", e.target.value)} aria-describedby="turnover-hint" className="field-input" />
                  <p id="turnover-hint" className="field-input-hint">Used only to test turnover ceilings and enterprise classifications.</p>
                </div>
                <div>
                  <label htmlFor="social_category" className="field-input-label">Social category</label>
                  <select id="social_category" value={draft.social_category} onChange={(e) => set("social_category", e.target.value)} aria-describedby="category-hint" className="field-input">
                    <option value="">Prefer not to say</option>
                    {CATEGORIES.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}
                  </select>
                  <p id="category-hint" className="field-input-hint">Used only where an official scheme reserves or varies benefits by category.</p>
                </div>
              </div>

              <fieldset className="mt-5 border-t border-field-rule pt-5">
                <legend className="font-field text-sm font-semibold uppercase text-field-fg">IS THE BUSINESS WOMAN-LED?</legend>
                <p className="mt-1 text-xs leading-5 text-field-fg-subtle">Some schemes carry different benefits or routes for woman-led enterprises.</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  {(["yes", "no", ""] as const).map((value) => (
                    <label key={value || "unset"} className="field-choice-row items-center">
                      <input type="radio" name="is_woman_led" checked={draft.is_woman_led === value} onChange={() => set("is_woman_led", value)} />
                      <span className="font-medium text-field-fg">{value === "yes" ? "Yes" : value === "no" ? "No" : "Prefer not to say"}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </section>
          </div>

          <aside className="space-y-4 lg:sticky lg:top-28">
            <div className="field-panel p-5">
              <p className="font-field text-[11px] uppercase tracking-[0.1em] text-field-fg-muted">BEFORE YOU CONTINUE</p>
              <h2 className="mt-2 font-field text-lg font-semibold uppercase text-field-fg">WHAT HAPPENS NEXT</h2>
              <ol className="mt-4 space-y-4 text-sm text-field-fg-muted">
                <li className="flex gap-3"><span className="font-field text-field-fg">01</span><span>Profile facts are checked against all active schemes.</span></li>
                <li className="flex gap-3"><span className="font-field text-field-fg">02</span><span>Unknown facts remain open instead of becoming failures.</span></li>
                <li className="flex gap-3"><span className="font-field text-field-fg">03</span><span>You see sources, missing evidence, and practical next steps.</span></li>
              </ol>
            </div>

            <div aria-live="polite">
              {error && <p role="alert" className="border border-field-alert-border bg-field-alert-bg p-3 font-field text-xs text-field-alert">{error}</p>}
            </div>

            <button type="submit" disabled={busy} className="field-button field-button-primary w-full" aria-busy={busy}>
              {busy ? "CHECKING SCHEMES…" : "SEE WHAT I QUALIFY FOR"}
            </button>
            <p className="text-center text-xs leading-5 text-field-fg-subtle">Advisory assessment only. No application is submitted.</p>
          </aside>
        </form>
      </main>
    </div>
  );
}
