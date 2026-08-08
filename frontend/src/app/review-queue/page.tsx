"use client";

/*
THESIS: The verification queue is a reviewer's operator console, not a
content-moderation feed — one click to approve, one required reason to
reject, nothing else in the way of moving to the next item.
OWN-WORLD: Field system — black ground, monospace type, hairline rules,
raw extracted JSON rendered as instrument output rather than a styled
card. Reject action spends the reserved alert accent; approve stays
neutral (it's the expected, unremarkable path).
STORY: A reviewer sees pending crawler/PDF extractions oldest first,
inspects the raw extracted content and its confidence score, then
approves or rejects with a required reason — approving never publishes
anything automatically, it only marks the extraction reviewed.
FORM: Rollout of the already-committed field-system direction (seed key
ca281bee, index 3) — this page extends that established world.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md.
*/

import { useEffect, useState } from "react";

import { FieldNav } from "@/components/FieldNav";
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
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <div role="alert" className="field-panel field-panel-active p-4">
            <p className="text-field-fg">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!items) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <p className="font-field text-xs uppercase text-field-fg-muted">LOADING THE QUEUE…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="field-shell">
      <FieldNav />
      <main className="field-page space-y-6">
        <div className="border-b border-field-rule pb-6">
          <h1 className="field-display text-2xl sm:text-3xl">VERIFICATION QUEUE</h1>
          <p className="mt-2 text-sm text-field-fg-muted">
            Changes detected by crawlers and PDF extraction, oldest first. Approving does not
            publish anything automatically — it marks the extraction as reviewed and correct;
            turning it into a scheme update is a separate step.
          </p>
        </div>

        {items.length === 0 && (
          <p className="field-panel px-4 py-8 text-center text-sm text-field-fg-muted">
            NOTHING PENDING.
          </p>
        )}

        <div className="space-y-4">
          {items.map((item) => (
            <article key={item.id} className="field-panel p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-field text-sm font-medium text-field-fg">{item.scheme_slug ?? "UNLINKED SOURCE"}</p>
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-field text-xs text-field-fg-muted underline underline-offset-2 hover:text-field-fg"
                  >
                    {item.source_url}
                  </a>
                </div>
                {item.extraction_confidence !== null && (
                  <span className="field-status shrink-0">
                    {Math.round(item.extraction_confidence * 100)}% CONFIDENCE
                  </span>
                )}
              </div>

              <pre className="mt-3 max-h-56 overflow-auto whitespace-pre-wrap border border-field-rule bg-black p-3 font-field text-xs text-field-fg-muted">
                {JSON.stringify(item.extracted_content, null, 2)}
              </pre>

              {rejectingId === item.id ? (
                <div className="mt-3 space-y-2">
                  <label htmlFor={`reason-${item.id}`} className="field-input-label">
                    REASON FOR REJECTION (REQUIRED)
                  </label>
                  <input
                    id={`reason-${item.id}`}
                    value={rejectNote}
                    onChange={(e) => setRejectNote(e.target.value)}
                    className="field-input mt-0"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleReject(item.id)}
                      disabled={!rejectNote.trim()}
                      className="field-button border-field-alert text-field-alert hover:bg-field-alert hover:text-field-bg"
                    >
                      CONFIRM REJECTION
                    </button>
                    <button
                      type="button"
                      onClick={() => setRejectingId(null)}
                      className="field-button"
                    >
                      CANCEL
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleApprove(item.id)}
                    className="field-button field-button-primary"
                  >
                    APPROVE
                  </button>
                  <button
                    type="button"
                    onClick={() => setRejectingId(item.id)}
                    className="field-button border-field-alert text-field-alert"
                  >
                    REJECT
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      </main>
    </div>
  );
}
