"use client";

import { useEffect, useState } from "react";

import { FieldNav } from "@/components/FieldNav";
import { ApiError, addDocument, deleteDocument, listDocuments, type UserDocument } from "@/lib/api";

const DOCUMENT_TYPES = [
  { value: "dpiit_certificate", label: "DPIIT Recognition Certificate" },
  { value: "gst_certificate", label: "GST Registration Certificate" },
  { value: "incorporation_certificate", label: "Certificate of Incorporation" },
  { value: "udyam_certificate", label: "Udyam Registration Certificate" },
  { value: "pan_card", label: "PAN Card" },
  { value: "audited_financials", label: "Audited Financial Statements" },
  { value: "pitch_deck", label: "Pitch Deck / Business Plan" },
  { value: "bank_statement", label: "Bank Statement (6 months)" },
  { value: "cancelled_cheque", label: "Cancelled Cheque" },
  { value: "director_aadhaar", label: "Director Aadhaar Card" },
  { value: "moa_aoa", label: "MOA / AOA" },
  { value: "itr", label: "Income Tax Return" },
  { value: "msme_certificate", label: "MSME Registration Certificate" },
] as const;

export default function VaultPage() {
  const [docs, setDocs] = useState<UserDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [type, setType] = useState<string>(DOCUMENT_TYPES[0].value);
  const [label, setLabel] = useState("");
  const [expiry, setExpiry] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    listDocuments()
      .then(setDocs)
      .catch((caught) => setError(caught instanceof ApiError ? caught.detail : "Could not load your vault."));
  }

  useEffect(load, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await addDocument({
        document_type: type as UserDocument["document_type"],
        label: label || null,
        issuing_authority_name: null,
        issue_date: null,
        expiry_date: expiry || null,
      });
      setLabel("");
      setExpiry("");
      load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not add that document.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    try {
      await deleteDocument(id);
      setDocs((current) => current?.filter((d) => d.id !== id) ?? null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not remove that document.");
    }
  }

  return (
    <div className="field-shell">
      <FieldNav />
      <main className="field-page space-y-8">
        <div className="border-b border-field-rule pb-6">
          <h1 className="field-display text-2xl sm:text-3xl">DOCUMENT VAULT</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-field-fg-muted">
            Record metadata for documents you hold — used to check what each scheme still
            needs from you. Nothing here uploads a file; this is a checklist, not storage.
          </p>
        </div>

        {error && (
          <div role="alert" className="border border-field-alert-border bg-field-alert-bg p-3 font-field text-xs text-field-alert">
            {error}
          </div>
        )}

        <section className="field-panel p-5 sm:p-6">
          <h2 className="font-field text-sm font-semibold uppercase text-field-fg">ADD A DOCUMENT</h2>
          <form onSubmit={submit} className="mt-4 grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <div>
              <label htmlFor="doc-type" className="field-input-label">TYPE</label>
              <select id="doc-type" value={type} onChange={(e) => setType(e.target.value)} className="field-input">
                {DOCUMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="doc-expiry" className="field-input-label">EXPIRY (OPTIONAL)</label>
              <input id="doc-expiry" type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} className="field-input" />
            </div>
            <button type="submit" disabled={busy} className="field-button field-button-primary">
              {busy ? "ADDING…" : "ADD"}
            </button>
          </form>
        </section>

        <section className="space-y-3">
          {docs === null && <p className="font-field text-xs uppercase text-field-fg-muted">LOADING…</p>}
          {docs !== null && docs.length === 0 && (
            <p className="field-panel p-6 text-center text-sm text-field-fg-muted">No documents recorded yet.</p>
          )}
          {docs?.map((doc) => {
            const isExpired = doc.is_expired;
            return (
              <div key={doc.id} className={`field-panel flex items-start justify-between gap-4 p-4 ${isExpired ? "field-panel-active" : ""}`}>
                <div>
                  <p className="font-medium text-field-fg">
                    {doc.label || DOCUMENT_TYPES.find((t) => t.value === doc.document_type)?.label || doc.document_type}
                  </p>
                  <p className="mt-1 font-field text-xs text-field-fg-muted">
                    ADDED {new Date(doc.created_at).toISOString().slice(0, 10)}
                    {doc.expiry_date && ` · EXPIRES ${doc.expiry_date}`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={isExpired ? "field-status field-status-alert" : "field-status"}>
                    {isExpired ? "EXPIRED" : "ON FILE"}
                  </span>
                  <button type="button" onClick={() => remove(doc.id)} className="field-button">
                    REMOVE
                  </button>
                </div>
              </div>
            );
          })}
        </section>
      </main>
    </div>
  );
}
