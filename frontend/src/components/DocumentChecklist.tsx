"use client";

import { useEffect, useState } from "react";

import { ApiError, getDocumentChecklist, type DocumentChecklist } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  have: "You have this",
  need: "Missing",
  expired: "Expired — needs renewal",
  not_applicable: "Not needed for your profile",
  optional_missing: "Optional, not provided",
};

const STATUS_STYLE: Record<string, string> = {
  have: "border-met-border bg-met-bg text-met-fg",
  need: "border-unmet-border bg-unmet-bg text-unmet-fg",
  expired: "border-unmet-border bg-unmet-bg text-unmet-fg",
  not_applicable: "border-surface-border bg-surface-sunken text-ink-subtle",
  optional_missing: "border-unverified-border bg-unverified-bg text-unverified-fg",
};

export function DocumentChecklistCard({ slug }: { slug: string }) {
  const [checklist, setChecklist] = useState<DocumentChecklist | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDocumentChecklist(slug)
      .then(setChecklist)
      .catch((caught) => setError(caught instanceof ApiError ? caught.detail : "Could not load documents."));
  }, [slug]);

  if (error) return null; // Non-critical to the page; fail quietly rather than block the deep-dive.
  if (!checklist) return <p className="text-sm text-ink-subtle">Checking your document vault…</p>;

  const missing = checklist.documents.filter((d) => d.status === "need");

  return (
    <section className="rounded-lg border border-surface-border bg-surface p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-medium">Documents</h2>
        <span className="text-xs text-ink-subtle">
          {checklist.have_count} have · {checklist.need_count} missing
          {checklist.expired_count > 0 && ` · ${checklist.expired_count} expired`}
        </span>
      </div>

      {missing.length > 0 && (
        <p className="mt-2 text-sm text-ink-muted">
          {missing.length === 1 ? "1 document" : `${missing.length} documents`} stand between you
          and a complete application.
        </p>
      )}

      <ul className="mt-3 space-y-2">
        {checklist.documents.map((doc) => (
          <li
            key={doc.requirement_id}
            className={`rounded border px-3 py-2 text-sm ${STATUS_STYLE[doc.status]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <span className="font-medium">{doc.document_name}</span>
              <span className="shrink-0 text-xs">{STATUS_LABEL[doc.status]}</span>
            </div>
            {(doc.status === "need" || doc.status === "expired") && (
              <div className="mt-1 text-xs opacity-90">
                {doc.issuing_authority && <p>Issued by: {doc.issuing_authority}</p>}
                {doc.typical_processing_days !== null && (
                  <p>Typically takes {doc.typical_processing_days} days to obtain.</p>
                )}
                {doc.how_to_obtain && <p className="mt-1">{doc.how_to_obtain}</p>}
              </div>
            )}
          </li>
        ))}
      </ul>

      {checklist.unused_vault_documents.length > 0 && (
        <p className="mt-3 text-xs text-ink-subtle">
          {checklist.unused_vault_documents.length} document(s) in your vault are not required
          for this scheme.
        </p>
      )}
    </section>
  );
}
