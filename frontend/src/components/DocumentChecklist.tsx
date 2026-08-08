"use client";

import { useEffect, useState } from "react";

import { ApiError, getDocumentChecklist, type DocumentChecklist } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  have: "YOU HAVE THIS",
  need: "MISSING",
  expired: "EXPIRED — NEEDS RENEWAL",
  not_applicable: "NOT NEEDED FOR YOUR PROFILE",
  optional_missing: "OPTIONAL, NOT PROVIDED",
};

/** Only the two blocking states (need, expired) spend the reserved
 * alert accent — the same discipline applied to CriterionRow. */
const ALERT_STATUSES = new Set(["need", "expired"]);

export function DocumentChecklistCard({ slug }: { slug: string }) {
  const [checklist, setChecklist] = useState<DocumentChecklist | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDocumentChecklist(slug)
      .then(setChecklist)
      .catch((caught) => setError(caught instanceof ApiError ? caught.detail : "Could not load documents."));
  }, [slug]);

  if (error) return null; // Non-critical to the page; fail quietly rather than block the deep-dive.
  if (!checklist) {
    return <p className="font-field text-xs uppercase text-field-fg-muted">CHECKING YOUR DOCUMENT VAULT…</p>;
  }

  const missing = checklist.documents.filter((d) => d.status === "need");

  return (
    <section className="field-panel p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="font-field text-sm font-semibold uppercase text-field-fg">DOCUMENTS</h2>
        <span className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">
          {checklist.have_count} HAVE · {checklist.need_count} MISSING
          {checklist.expired_count > 0 && ` · ${checklist.expired_count} EXPIRED`}
        </span>
      </div>

      {missing.length > 0 && (
        <p className="mt-2 text-sm text-field-fg-muted">
          {missing.length === 1 ? "1 document" : `${missing.length} documents`} stand between you
          and a complete application.
        </p>
      )}

      <ul className="mt-3 space-y-2">
        {checklist.documents.map((doc) => {
          const isAlert = ALERT_STATUSES.has(doc.status);
          return (
            <li
              key={doc.requirement_id}
              className={`border p-3 text-sm ${
                isAlert
                  ? "border-field-alert-border bg-field-alert-bg"
                  : "border-field-rule bg-field-bg-raised"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="font-medium text-field-fg">{doc.document_name}</span>
                <span
                  className={
                    isAlert
                      ? "field-status field-status-alert shrink-0"
                      : "field-status shrink-0"
                  }
                >
                  {STATUS_LABEL[doc.status]}
                </span>
              </div>
              {(doc.status === "need" || doc.status === "expired") && (
                <div className="mt-1 text-xs text-field-fg-muted">
                  {doc.issuing_authority && <p>Issued by: {doc.issuing_authority}</p>}
                  {doc.typical_processing_days !== null && (
                    <p>Typically takes {doc.typical_processing_days} days to obtain.</p>
                  )}
                  {doc.how_to_obtain && <p className="mt-1">{doc.how_to_obtain}</p>}
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {checklist.unused_vault_documents.length > 0 && (
        <p className="mt-3 font-field text-xs text-field-fg-subtle">
          {checklist.unused_vault_documents.length} document(s) in your vault are not required
          for this scheme.
        </p>
      )}
    </section>
  );
}
