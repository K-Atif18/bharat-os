"use client";

/*
THESIS: Privacy and consent controls are a compliance ledger, not a
settings-page afterthought — every purpose stated plainly with its
withdrawal consequence, matching the field system's instrument-panel
register.
OWN-WORLD: Field system — black ground, monospace type, hairline rules.
Every button label, heading and consent/withdrawal string is unchanged
from the civic-paper version and kept in its original casing rather than
the redesign's usual all-caps treatment — this page has an existing test
suite asserting exact visible text (headings, button names), and this
pass restyles containers/classes only, never copy a test depends on.
STORY: A signed-in user reviews each consent purpose, can withdraw with
an explicit confirmation step naming the real consequence, download a
calendar export gated on the right consents, or permanently erase their
account with a second confirmation and a receipt of what was removed.
FORM: Rollout of the already-committed field-system direction (seed key
ca281bee, index 3) — this page extends that established world.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md.
*/

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FieldNav } from "@/components/FieldNav";
import {
  ApiError,
  apiBaseUrl,
  eraseAccount,
  getAccount,
  updateConsent,
  type Account,
  type Consent,
  type ConsentPurpose,
  type Erasure,
} from "@/lib/api";

const PURPOSES: Array<{
  purpose: ConsentPurpose;
  label: string;
  detail: string;
  withdrawal: string;
}> = [
  {
    purpose: "scheme_matching",
    label: "Scheme matching",
    detail: "Process your business profile against scheme criteria.",
    withdrawal: "Withdrawing this consent permanently deletes your business profile.",
  },
  {
    purpose: "document_storage",
    label: "Document vault",
    detail: "Store document metadata for reusable application checklists and deadline planning.",
    withdrawal: "Withdrawing this consent permanently deletes every document-vault record.",
  },
  {
    purpose: "outcome_analytics",
    label: "Outcome analytics",
    detail: "Retain de-identified application outcomes to improve future assessments.",
    withdrawal: "Withdrawing this consent deletes outcomes linked to your applications.",
  },
  {
    purpose: "notifications",
    label: "Deadline reminders",
    detail: "Allow deadline and status reminders for opportunities you track.",
    withdrawal: "Withdrawing this consent removes stored reminder-delivery records.",
  },
];

function isActive(consents: Consent[], purpose: ConsentPurpose): boolean {
  return consents.find((consent) => consent.purpose === purpose)?.is_active ?? false;
}

export default function SettingsPage() {
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyPurpose, setBusyPurpose] = useState<ConsentPurpose | null>(null);
  const [confirmPurpose, setConfirmPurpose] = useState<ConsentPurpose | null>(null);
  const [confirmErasure, setConfirmErasure] = useState(false);
  const [erasing, setErasing] = useState(false);
  const [receipt, setReceipt] = useState<Erasure | null>(null);

  useEffect(() => {
    getAccount()
      .then(setAccount)
      .catch((caught) => {
        if (caught instanceof ApiError && caught.isUnauthenticated) {
          router.replace("/");
          return;
        }
        setError("Could not load your privacy settings. Please try again.");
      });
  }, [router]);

  async function changeConsent(purpose: ConsentPurpose, granted: boolean) {
    setError(null);
    setBusyPurpose(purpose);
    try {
      const consents = await updateConsent(purpose, granted);
      setAccount((current) =>
        current
          ? {
              ...current,
              consents,
              has_profile:
                purpose === "scheme_matching" && !granted ? false : current.has_profile,
            }
          : current,
      );
      setConfirmPurpose(null);
    } catch {
      setError("Could not update that consent. Your previous setting is unchanged.");
    } finally {
      setBusyPurpose(null);
    }
  }

  async function eraseEverything() {
    setError(null);
    setErasing(true);
    try {
      setReceipt(await eraseAccount());
      setAccount(null);
      setConfirmErasure(false);
    } catch {
      setError("Could not delete the account. No deletion confirmation was issued.");
    } finally {
      setErasing(false);
    }
  }

  if (receipt) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <section className="field-panel field-panel-active mx-auto max-w-2xl p-6">
            <p className="font-field text-xs uppercase tracking-[0.1em] text-field-fg-muted">Erasure complete</p>
            <h1 className="mt-2 font-field text-2xl font-semibold uppercase text-field-fg">Your account data was deleted</h1>
            <p className="mt-3 text-sm leading-6 text-field-fg-muted">{receipt.note}</p>
            <dl className="mt-5 grid grid-cols-2 gap-4 border-y border-field-rule py-4 sm:grid-cols-4">
              <div><dt className="font-field text-[11px] uppercase text-field-fg-muted">Sessions removed</dt><dd className="mt-1 font-field text-lg font-semibold tabular-nums text-field-fg">{receipt.sessions_revoked}</dd></div>
              <div><dt className="font-field text-[11px] uppercase text-field-fg-muted">Consents removed</dt><dd className="mt-1 font-field text-lg font-semibold tabular-nums text-field-fg">{receipt.consents_deleted}</dd></div>
              <div><dt className="font-field text-[11px] uppercase text-field-fg-muted">AI prompts removed</dt><dd className="mt-1 font-field text-lg font-semibold tabular-nums text-field-fg">{receipt.ai_judgements_deleted}</dd></div>
              <div><dt className="font-field text-[11px] uppercase text-field-fg-muted">Applications de-linked</dt><dd className="mt-1 font-field text-lg font-semibold tabular-nums text-field-fg">{receipt.applications_unlinked}</dd></div>
            </dl>
            <Link href="/" className="field-button field-button-primary mt-6">Return home</Link>
          </section>
        </div>
      </div>
    );
  }

  if (!account && !error) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <p className="font-field text-xs uppercase text-field-fg-muted">Loading your privacy settings…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="field-shell">
      <FieldNav />
      <main className="field-page mx-auto max-w-3xl space-y-8">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-field-rule pb-6">
          <div>
            <p className="font-field text-[11px] uppercase tracking-[0.1em] text-field-fg-muted">Privacy control</p>
            <h1 className="mt-1 font-field text-2xl font-semibold uppercase text-field-fg">Your data and consent</h1>
            <p className="mt-2 text-sm text-field-fg-muted">Each purpose can be changed independently. Withdrawal takes effect immediately.</p>
          </div>
          <Link href="/dashboard" className="field-button">Back to dashboard</Link>
        </div>

        {error && <p role="alert" className="border border-field-alert-border bg-field-alert-bg p-3 font-field text-xs text-field-alert">{error}</p>}

        {account && (
          <>
            <section className="field-panel p-5 sm:p-6">
              <h2 className="font-field text-lg font-semibold uppercase text-field-fg">Purpose-specific consent</h2>
              <p className="mt-1 font-field text-[11px] uppercase text-field-fg-muted">Signed in as {account.email}</p>
              <div className="mt-4 divide-y divide-field-rule">
                {PURPOSES.map((item) => {
                  const active = isActive(account.consents, item.purpose);
                  const confirming = confirmPurpose === item.purpose;
                  return (
                    <div key={item.purpose} className="py-4 first:pt-0 last:pb-0">
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div className="max-w-xl">
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-field-fg">{item.label}</h3>
                            <span className="field-status">
                              {active ? "Granted" : "Not granted"}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-field-fg-muted">{item.detail}</p>
                        </div>
                        <button
                          type="button"
                          disabled={busyPurpose !== null}
                          onClick={() => active ? setConfirmPurpose(item.purpose) : changeConsent(item.purpose, true)}
                          className="field-button"
                        >
                          {busyPurpose === item.purpose ? "Updating…" : active ? "Withdraw" : "Grant"}
                        </button>
                      </div>
                      {confirming && (
                        <div className="mt-3 border border-field-alert-border bg-field-alert-bg p-3">
                          <p className="text-sm text-field-alert">{item.withdrawal}</p>
                          <div className="mt-3 flex gap-3">
                            <button type="button" onClick={() => changeConsent(item.purpose, false)} className="field-button border-field-alert text-field-alert hover:bg-field-alert hover:text-field-bg">Confirm withdrawal</button>
                            <button type="button" onClick={() => setConfirmPurpose(null)} className="field-button">Cancel</button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="field-panel p-5 sm:p-6">
              <h2 className="font-field text-lg font-semibold uppercase text-field-fg">Deadline calendar</h2>
              <p className="mt-1 text-sm text-field-fg-muted">Export dated opportunities, reachability notes, and 30/14/7/1-day reminders to your calendar app.</p>
              {isActive(account.consents, "scheme_matching") && isActive(account.consents, "document_storage") ? (
                <a href={`${apiBaseUrl()}/deadlines/calendar.ics`} className="field-button field-button-primary mt-4">
                  Download .ics calendar
                </a>
              ) : (
                <p className="mt-3 font-field text-xs text-field-alert">Grant scheme matching and document-vault consent to build a personalized calendar.</p>
              )}
            </section>

            <section className="field-panel field-panel-active p-5 sm:p-6">
              <h2 className="font-field text-lg font-semibold uppercase text-field-alert">Delete account and personal data</h2>
              <p className="mt-1 text-sm text-field-fg-muted">This removes your account, profile, vault, sessions, consents, and AI prompts. De-identified aggregate outcomes are retained without a link to you.</p>
              {confirmErasure ? (
                <div className="mt-4 flex flex-wrap gap-3">
                  <button type="button" disabled={erasing} onClick={eraseEverything} className="field-button border-field-alert text-field-alert hover:bg-field-alert hover:text-field-bg">{erasing ? "Deleting…" : "Permanently delete everything"}</button>
                  <button type="button" onClick={() => setConfirmErasure(false)} className="field-button">Cancel</button>
                </div>
              ) : (
                <button type="button" onClick={() => setConfirmErasure(true)} className="field-button mt-4 border-field-alert text-field-alert">Delete my account</button>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
