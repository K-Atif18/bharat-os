"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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
      <section className="mx-auto max-w-2xl rounded-2xl border border-met-border bg-met-bg p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-met-fg">
          Erasure complete
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Your account data was deleted</h1>
        <p className="mt-3 text-sm leading-6 text-ink-muted">{receipt.note}</p>
        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
          <div><dt className="text-ink-subtle">Sessions removed</dt><dd className="font-semibold">{receipt.sessions_revoked}</dd></div>
          <div><dt className="text-ink-subtle">Consents removed</dt><dd className="font-semibold">{receipt.consents_deleted}</dd></div>
          <div><dt className="text-ink-subtle">AI prompts removed</dt><dd className="font-semibold">{receipt.ai_judgements_deleted}</dd></div>
          <div><dt className="text-ink-subtle">Applications de-linked</dt><dd className="font-semibold">{receipt.applications_unlinked}</dd></div>
        </dl>
        <Link href="/" className="mt-6 inline-block rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white">
          Return home
        </Link>
      </section>
    );
  }

  if (!account && !error) {
    return <p className="text-sm text-ink-subtle">Loading your privacy settings…</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Privacy control</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Your data and consent</h1>
          <p className="mt-2 text-sm text-ink-muted">Each purpose can be changed independently. Withdrawal takes effect immediately.</p>
        </div>
        <Link href="/dashboard" className="rounded-lg border border-surface-border bg-white px-4 py-2 text-sm font-medium hover:bg-surface-sunken">
          Back to dashboard
        </Link>
      </div>

      {error && <p role="alert" className="rounded-lg border border-unmet-border bg-unmet-bg p-3 text-sm text-unmet-fg">{error}</p>}

      {account && (
        <>
          <section className="rounded-2xl border border-surface-border bg-surface p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Purpose-specific consent</h2>
            <p className="mt-1 text-sm text-ink-subtle">Signed in as {account.email}</p>
            <div className="mt-4 divide-y divide-surface-border">
              {PURPOSES.map((item) => {
                const active = isActive(account.consents, item.purpose);
                const confirming = confirmPurpose === item.purpose;
                return (
                  <div key={item.purpose} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="max-w-xl">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold">{item.label}</h3>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${active ? "bg-met-bg text-met-fg" : "bg-surface-sunken text-ink-subtle"}`}>
                            {active ? "Granted" : "Not granted"}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-ink-muted">{item.detail}</p>
                      </div>
                      <button
                        type="button"
                        disabled={busyPurpose !== null}
                        onClick={() => active ? setConfirmPurpose(item.purpose) : changeConsent(item.purpose, true)}
                        className="rounded-lg border border-surface-border px-3 py-2 text-sm font-medium hover:bg-surface-sunken disabled:opacity-50"
                      >
                        {busyPurpose === item.purpose ? "Updating…" : active ? "Withdraw" : "Grant"}
                      </button>
                    </div>
                    {confirming && (
                      <div className="mt-3 rounded-lg border border-unmet-border bg-unmet-bg p-3">
                        <p className="text-sm text-unmet-fg">{item.withdrawal}</p>
                        <div className="mt-3 flex gap-3">
                          <button type="button" onClick={() => changeConsent(item.purpose, false)} className="rounded bg-unmet-fg px-3 py-1.5 text-xs font-medium text-white">Confirm withdrawal</button>
                          <button type="button" onClick={() => setConfirmPurpose(null)} className="text-xs font-medium text-ink-muted hover:underline">Cancel</button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-2xl border border-surface-border bg-surface p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Deadline calendar</h2>
            <p className="mt-1 text-sm text-ink-muted">Export dated opportunities, reachability notes, and 30/14/7/1-day reminders to your calendar app.</p>
            {isActive(account.consents, "scheme_matching") && isActive(account.consents, "document_storage") ? (
              <a href={`${apiBaseUrl()}/deadlines/calendar.ics`} className="mt-4 inline-block rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover">
                Download .ics calendar
              </a>
            ) : (
              <p className="mt-3 text-xs text-unverified-fg">Grant scheme matching and document-vault consent to build a personalized calendar.</p>
            )}
          </section>

          <section className="rounded-2xl border border-unmet-border bg-unmet-bg p-5">
            <h2 className="text-lg font-semibold text-unmet-fg">Delete account and personal data</h2>
            <p className="mt-1 text-sm text-ink-muted">This removes your account, profile, vault, sessions, consents, and AI prompts. De-identified aggregate outcomes are retained without a link to you.</p>
            {confirmErasure ? (
              <div className="mt-4 flex flex-wrap gap-3">
                <button type="button" disabled={erasing} onClick={eraseEverything} className="rounded-lg bg-unmet-fg px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{erasing ? "Deleting…" : "Permanently delete everything"}</button>
                <button type="button" onClick={() => setConfirmErasure(false)} className="text-sm font-medium text-ink-muted hover:underline">Cancel</button>
              </div>
            ) : (
              <button type="button" onClick={() => setConfirmErasure(true)} className="mt-4 rounded-lg border border-unmet-border bg-white px-4 py-2 text-sm font-medium text-unmet-fg">Delete my account</button>
            )}
          </section>
        </>
      )}
    </div>
  );
}
