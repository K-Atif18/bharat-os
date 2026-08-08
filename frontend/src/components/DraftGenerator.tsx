"use client";

import { useState } from "react";

import { ApiError, createDraft, getDraft, type Draft } from "@/lib/api";

const SOURCE_LABEL: Record<string, string> = {
  profile: "From your profile",
  generated_narrative: "Drafted by AI from your profile",
  human_required: "You need to provide this",
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
      <section className="rounded-lg border border-surface-border bg-surface p-5">
        <h2 className="text-sm font-medium">Draft application</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Pre-fill what can be pre-filled from your profile, and write the narrative
          sections a reviewer expects. You review, edit and submit — nothing here files
          anything for you.
        </p>
        {error && (
          <p role="alert" className="mt-2 text-sm text-unmet-fg">
            {error}
          </p>
        )}
        <button
          type="button"
          onClick={generate}
          disabled={busy}
          className="mt-3 rounded bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-60"
          onFocus={loadExisting}
        >
          {busy ? "Drafting…" : "Generate draft"}
        </button>
      </section>
    );
  }

  const populated = draft.fields.filter((field) => field.value).length;
  const humanRequired = draft.fields.filter((field) => field.source === "human_required").length;

  return (
    <section className="overflow-hidden rounded-xl border border-brand/25 bg-surface shadow-md">
      <div className="bg-gradient-to-r from-brand to-blue-700 p-5 text-white">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-200">Application workspace generated</p>
            <h2 className="mt-1 text-lg font-semibold">Draft application · version {draft.version}</h2>
          </div>
          <button type="button" onClick={download} className="rounded-lg border border-white/25 bg-white/10 px-3 py-1.5 text-xs font-medium hover:bg-white/20">
            Download draft
          </button>
        </div>
        <p className="mt-3 text-sm text-blue-100">{populated} fields prepared · {humanRequired} kept for your input</p>
      </div>

      <div className="p-5">
      <p className="rounded border border-unverified-border bg-unverified-bg px-3 py-2 text-xs text-unverified-fg">
        {draft.review_notice}
      </p>

      <div className="mt-4 space-y-4">
        {draft.fields.map((field) => (
          <div key={field.key}>
            <div className="flex items-baseline justify-between">
              <h3 className="text-sm font-medium">{field.label}</h3>
              <span className="text-xs text-ink-subtle">
                {SOURCE_LABEL[field.source] ?? field.source}
              </span>
            </div>
            {field.value ? (
              <p className="mt-1 whitespace-pre-wrap text-sm text-ink-muted">{field.value}</p>
            ) : (
              <p className="mt-1 text-sm text-unverified-fg">{field.reason}</p>
            )}
            {field.instruction && (
              <p className="mt-1 text-xs text-ink-subtle">Asked of the AI: {field.instruction}</p>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={generate}
        disabled={busy}
        className="mt-4 text-xs font-medium text-brand hover:underline disabled:opacity-60"
      >
        {busy ? "Regenerating…" : "Regenerate (creates a new version)"}
      </button>
      </div>
    </section>
  );
}
