"use client";

/*
THESIS: A draft is an instrument readout, not a form — the page proves every
field's provenance (profile / AI / you) with the same precision it would
report a sensor value, refusing the generic "review your application" card
layout every AI-drafting tool ships.
OWN-WORLD: Field system — pure black ground, monospace type, hairline rules,
tabular data readouts (LABEL ... VALUE), one reserved accent (field-alert,
#FF3B30) for fields still requiring human input, always paired with a text
status label so color is never the only signal.
STORY: The user opens a workspace for one scheme, sees the draft's own
metadata (version, generated-at, field counts) as instrument readouts, then
reads every field as a labeled, sourced value — populated fields show their
provenance, human-required fields are marked with the one reserved accent
and the reason nothing was filled. They leave knowing exactly what is done,
what is theirs to write, and that nothing here has been submitted anywhere.
FIRST VIEWPORT: A sticky field-nav (scheme name, draft version, back link) —
below it a readout strip (version / generated / fields populated / fields
needing you) spanning the full width, then the first draft field begins
immediately below, no hero, no marketing space.
FORM: Assigned direction (data-sublime field, Ikeda-datamatics-derived),
index 3 of the operate-mode direction roll, seed key ca281bee.
FINISH: unreviewed and undocumented is unfinished; this build ends with the
finish review, the verdict, and DESIGN.md.
*/

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FieldNav } from "@/components/FieldNav";
import {
  ApiError,
  createDraft,
  getDeepDive,
  getDraft,
  type DeepDive,
  type Draft,
} from "@/lib/api";

const SOURCE_LABEL: Record<string, string> = {
  profile: "FROM PROFILE",
  generated_narrative: "DRAFTED BY AI",
  human_required: "NEEDS YOU",
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date
    .toISOString()
    .replace("T", " ")
    .replace(/\.\d+Z$/, " UTC");
}

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

export default function DraftWorkspacePage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [scheme, setScheme] = useState<DeepDive | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getDeepDive(params.slug)
      .then(setScheme)
      .catch((caught) => {
        if (caught instanceof ApiError && caught.isUnauthenticated) {
          router.replace("/");
        } else if (caught instanceof ApiError && caught.status === 409) {
          router.replace("/onboarding");
        }
      });

    getDraft(params.slug)
      .then(setDraft)
      .catch(() => setDraft(null))
      .finally(() => setLoaded(true));
  }, [params.slug, router]);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      setDraft(await createDraft(params.slug));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not generate a draft.");
    } finally {
      setBusy(false);
    }
  }

  function download() {
    if (!draft || !scheme) return;
    const blob = new Blob([exportAsText(draft, scheme.name)], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${params.slug}-draft-v${draft.version}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const schemeName = scheme?.name ?? params.slug;
  const populatedCount = draft?.fields.filter((f) => f.value).length ?? 0;
  const totalCount = draft?.fields.length ?? 0;

  return (
    <div className="field-shell">
      <FieldNav trail={schemeName} />
      <div className="border-b border-field-rule px-4 py-2 sm:px-6">
        <Link href={`/schemes/${params.slug}`} className="field-nav-key">
          ← BACK TO {schemeName}
        </Link>
      </div>

      <main className="field-page">
        <header className="field-section-label">
          <span className="field-index">01</span>
          <span>APPLICATION DRAFT</span>
        </header>

        {!loaded && (
          <p className="mt-6 font-field text-xs uppercase tracking-[0.12em] text-field-fg-muted">
            LOADING…
          </p>
        )}

        {loaded && !draft && (
          <div className="field-panel mt-6 p-6">
            <p className="font-field text-sm text-field-fg">
              No draft exists yet for this scheme.
            </p>
            <p className="mt-2 font-field text-xs leading-6 text-field-fg-muted">
              Generating pre-fills what your profile already answers and drafts the
              narrative sections a reviewer expects. You review, edit and submit —
              nothing here files anything for you.
            </p>
            {error && (
              <p role="alert" className="mt-3 font-field text-xs text-field-alert">
                {error}
              </p>
            )}
            <button
              type="button"
              onClick={generate}
              disabled={busy}
              className="field-button field-button-primary mt-4"
            >
              {busy ? "GENERATING…" : "GENERATE DRAFT"}
            </button>
          </div>
        )}

        {draft && (
          <>
            <div className="field-panel mt-6 px-4 py-1 sm:px-6">
              <div className="field-readout">
                <span className="field-readout-label">VERSION</span>
                <span className="field-readout-value">{draft.version}</span>
              </div>
              <div className="field-readout">
                <span className="field-readout-label">GENERATED</span>
                <span className="field-readout-value">
                  {formatTimestamp(draft.created_at)}
                </span>
              </div>
              <div className="field-readout">
                <span className="field-readout-label">FIELDS POPULATED</span>
                <span className="field-readout-value">
                  {populatedCount} / {totalCount}
                </span>
              </div>
              <div className="field-readout">
                <span className="field-readout-label">NEEDS YOU</span>
                <span
                  className={
                    draft.human_required_count > 0
                      ? "field-readout-value text-field-alert"
                      : "field-readout-value"
                  }
                >
                  {draft.human_required_count}
                </span>
              </div>
            </div>

            <div className="field-wave-rule mt-8" role="separator" aria-hidden="true" />

            <div className="mt-8 flex items-baseline justify-between gap-4">
              <span className="field-section-label border-none pb-0">
                <span className="field-index">02</span>
                <span>FIELDS</span>
              </span>
              <div className="flex gap-2">
                <button type="button" onClick={download} className="field-button">
                  DOWNLOAD
                </button>
                <button
                  type="button"
                  onClick={generate}
                  disabled={busy}
                  className="field-button"
                >
                  {busy ? "REGENERATING…" : "REGENERATE"}
                </button>
              </div>
            </div>

            <ol className="mt-6 space-y-0">
              {draft.fields.map((field, index) => {
                const isAlert = field.source === "human_required" && !field.value;
                return (
                  <li
                    key={field.key}
                    className={`field-panel border-t-0 px-4 py-5 sm:px-6 ${
                      index === 0 ? "border-t" : ""
                    } ${isAlert ? "field-panel-active" : ""}`}
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="font-field text-sm font-medium text-field-fg">
                        {field.label}
                      </h3>
                      <span
                        className={
                          isAlert ? "field-status field-status-alert" : "field-status"
                        }
                      >
                        {SOURCE_LABEL[field.source] ?? field.source}
                      </span>
                    </div>
                    {field.value ? (
                      <p className="mt-3 whitespace-pre-wrap font-sans text-sm leading-6 text-field-fg-muted">
                        {field.value}
                      </p>
                    ) : (
                      <p className="mt-3 font-field text-xs leading-6 text-field-alert">
                        {field.reason}
                      </p>
                    )}
                    {field.instruction && (
                      <p className="mt-3 font-field text-[11px] uppercase tracking-[0.06em] text-field-fg-subtle">
                        ASKED OF THE AI: {field.instruction}
                      </p>
                    )}
                  </li>
                );
              })}
            </ol>

            <div className="field-wave-rule mt-8" role="separator" aria-hidden="true" />

            <p className="field-panel mt-8 p-4 font-field text-[11px] uppercase leading-6 tracking-[0.04em] text-field-fg-muted sm:p-6">
              {draft.review_notice}
            </p>
          </>
        )}
      </main>
    </div>
  );
}
