"use client";

import { useEffect, useState } from "react";

import {
  ApiError,
  approveRevision,
  listPendingRevisions,
  rejectRevision,
  type PendingRevision,
} from "@/lib/api";

/**
 * The human-in-the-loop console.
 *
 * A queue that becomes a bottleneck is a documented failure mode for this
 * product, so the interaction is deliberately fast: one click to approve, one
 * short reason to reject, nothing else required to move to the next item.
 */
export default function ReviewQueuePage() {
  const [items, setItems] = useState<PendingRevision[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  function load() {
    listPendingRevisions()
      .then(setItems)
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 403) {
          setError("This page requires reviewer access.");
        } else {
          setError(caught instanceof ApiError ? caught.detail : "Could not load the queue.");
        }
      });
  }

  useEffect(load, []);

  async function handleApprove(id: string) {
    await approveRevision(id);
    setItems((current) => current?.filter((item) => item.id !== id) ?? null);
  }

  async function handleReject(id: string) {
    if (!rejectNote.trim()) return;
    await rejectRevision(id, rejectNote);
    setItems((current) => current?.filter((item) => item.id !== id) ?? null);
    setRejectingId(null);
    setRejectNote("");
  }

  if (error) {
    return (
      <div role="alert" className="rounded-lg border border-unmet-border bg-unmet-bg p-4 text-sm text-unmet-fg">
        {error}
      </div>
    );
  }

  if (!items) {
    return <p className="text-sm text-ink-subtle">Loading the queue…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Verification queue</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Changes detected by crawlers and PDF extraction, oldest first. Approving does not
          publish anything automatically — it marks the extraction as reviewed and correct;
          turning it into a scheme update is a separate step.
        </p>
      </div>

      {items.length === 0 && (
        <p className="rounded border border-surface-border bg-surface px-4 py-8 text-center text-sm text-ink-muted">
          Nothing pending.
        </p>
      )}

      <div className="space-y-4">
        {items.map((item) => (
          <article key={item.id} className="rounded-lg border border-surface-border bg-surface p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium">{item.scheme_slug ?? "Unlinked source"}</p>
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-brand hover:underline"
                >
                  {item.source_url}
                </a>
              </div>
              {item.extraction_confidence !== null && (
                <span className="shrink-0 rounded-full bg-surface-sunken px-2 py-0.5 text-xs">
                  {Math.round(item.extraction_confidence * 100)}% extraction confidence
                </span>
              )}
            </div>

            <pre className="mt-3 max-h-56 overflow-auto whitespace-pre-wrap rounded bg-surface-sunken p-3 text-xs">
              {JSON.stringify(item.extracted_content, null, 2)}
            </pre>

            {rejectingId === item.id ? (
              <div className="mt-3 space-y-2">
                <label htmlFor={`reason-${item.id}`} className="block text-xs font-medium">
                  Reason for rejection (required)
                </label>
                <input
                  id={`reason-${item.id}`}
                  value={rejectNote}
                  onChange={(e) => setRejectNote(e.target.value)}
                  className="w-full rounded border border-surface-border px-2 py-1 text-sm"
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleReject(item.id)}
                    disabled={!rejectNote.trim()}
                    className="rounded bg-unmet-fg px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                  >
                    Confirm rejection
                  </button>
                  <button
                    type="button"
                    onClick={() => setRejectingId(null)}
                    className="text-xs text-ink-subtle hover:underline"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => handleApprove(item.id)}
                  className="rounded bg-met-fg px-3 py-1.5 text-xs font-medium text-white"
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => setRejectingId(item.id)}
                  className="rounded border border-unmet-border px-3 py-1.5 text-xs font-medium text-unmet-fg"
                >
                  Reject
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
