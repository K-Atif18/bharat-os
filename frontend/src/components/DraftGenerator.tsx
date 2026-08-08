"use client";

import { useState } from "react";
import Link from "next/link";

import { ApiError, createDraft, getDraft, type Draft } from "@/lib/api";

const SOURCE_LABEL: Record<string, string> = {
  profile: "FROM PROFILE",
  generated_narrative: "DRAFTED BY AI",
  human_required: "NEEDS YOU",
};

function exportAsText(draft: Draft, schemeName: string): string {
  const lines = [`Draft application — ${schemeName}`, `Version ${draft.version}`, ""];
  for (const field of draft.fields) {
    lines.push(`## ${field.label}`);
    lines.push(`(${SOURCE_LABEL[field.source] ?? field.source})`);
    if (field.value) {
      lines.push(field.value);
    } else if (field.reason) {
      lines.push(`[Not filled: ${field.reason}]`);
    }
    lines.push("");
  }
  lines.push("---");
  lines.push(draft.review_notice);
  return lines.join("\n");
}

export function DraftGenerator({ slug, schemeName }: { slug: string; schemeName: string }) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      setDraft(await createDraft(slug));
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) {
        setError("Drafting is not yet available for this scheme.");
      } else {
        setError(caught instanceof ApiError ? caught.detail : "Could not generate a draft.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function loadExisting() {
    try {
      setDraft(await getDraft(slug));
    } catch {
      // No draft yet — leave the generate button as the primary action.
    }
  }

  function download() {
    if (!draft) return;
    const blob = new Blob([exportAsText(draft, schemeName)], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}-draft-v${draft.version}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!draft) {
    return (
      <section className="field-panel p-5">
        <h2 className="font-field text-sm font-semibold uppercase text-field-fg">DRAFT APPLICATION</h2>
        <p className="mt-1 text-sm text-field-fg-muted">
          Pre-fill what can be pre-filled from your profile, and write the narrative
          sections a reviewer expects. You review, edit and submit — nothing here files
          anything for you.
        </p>
        {error && (
          <p role="alert" className="mt-2 font-field text-xs text-field-alert">
            {error}
          </p>
        )}
        <button
          type="button"
          onClick={generate}
          disabled={busy}
          className="field-button field-button-primary mt-3"
          onFocus={loadExisting}
        >
          {busy ? "DRAFTING…" : "GENERATE DRAFT"}
        </button>
      </section>
    );
  }

  const populated = draft.fields.filter((field) => field.value).length;
  const humanRequired = draft.fields.filter((field) => field.source === "human_required").length;

  return (
    <section className="field-panel field-panel-active overflow-hidden">
      <div className="border-b border-field-rule p-5">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <p className="font-field text-[10px] font-semibold uppercase tracking-[0.16em] text-field-fg-muted">
              APPLICATION WORKSPACE GENERATED
            </p>
            <h2 className="mt-1 font-field text-lg font-semibold uppercase text-field-fg">
              DRAFT APPLICATION · VERSION {draft.version}
            </h2>
          </div>
          <button type="button" onClick={download} className="field-button">
            DOWNLOAD
          </button>
        </div>
        <p className="mt-3 font-field text-xs text-field-fg-muted">
          {populated} FIELDS PREPARED · {humanRequired} KEPT FOR YOUR INPUT
        </p>
        <Link
          href={`/schemes/${slug}/workspace`}
          className="mt-3 inline-flex items-center gap-1 font-field text-xs font-semibold uppercase text-field-fg underline decoration-field-fg-muted underline-offset-4 hover:text-field-fg-muted"
        >
          OPEN FULL WORKSPACE →
        </Link>
      </div>

      <div className="p-5">
      <p className="border border-field-alert-border bg-field-alert-bg px-3 py-2 font-field text-xs text-field-alert">
        {draft.review_notice}
      </p>

      <div className="mt-4 space-y-4">
        {draft.fields.map((field) => (
          <div key={field.key}>
            <div className="flex items-baseline justify-between">
              <h3 className="text-sm font-medium text-field-fg">{field.label}</h3>
              <span className="field-status">
                {SOURCE_LABEL[field.source] ?? field.source}
              </span>
            </div>
            {field.value ? (
              <p className="mt-1 whitespace-pre-wrap text-sm text-field-fg-muted">{field.value}</p>
            ) : (
              <p className="mt-1 font-field text-xs text-field-alert">{field.reason}</p>
            )}
            {field.instruction && (
              <p className="mt-1 font-field text-[11px] text-field-fg-subtle">ASKED OF THE AI: {field.instruction}</p>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={generate}
        disabled={busy}
        className="mt-4 font-field text-xs font-semibold uppercase text-field-fg-muted hover:text-field-fg disabled:opacity-60"
      >
        {busy ? "REGENERATING…" : "REGENERATE (CREATES A NEW VERSION)"}
      </button>
      </div>
    </section>
  );
}
