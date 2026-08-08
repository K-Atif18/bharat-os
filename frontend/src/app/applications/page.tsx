"use client";

import { useEffect, useState } from "react";

import { FieldNav } from "@/components/FieldNav";
import { ApiError, listApplications, recordOutcome, updateApplicationStatus, type Application, type ApplicationStatus, type OutcomeInput } from "@/lib/api";

const STAGES: ApplicationStatus[] = ["draft", "ready_for_review", "submitted", "under_review", "approved", "rejected", "withdrawn"];
const ALERT_STAGES = new Set<ApplicationStatus>(["rejected", "withdrawn"]);
const OUTCOME_TYPES: OutcomeInput["outcome_type"][] = ["approved", "partially_approved", "rejected", "lapsed"];

export default function ApplicationsPage() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [reportingId, setReportingId] = useState<string | null>(null);
  const [outcomeType, setOutcomeType] = useState<OutcomeInput["outcome_type"]>("approved");
  const [rejectionReason, setRejectionReason] = useState("");

  function load() {
    listApplications()
      .then(setApps)
      .catch((caught) => setError(caught instanceof ApiError ? caught.detail : "Could not load your applications."));
  }

  useEffect(load, []);

  async function advance(app: Application, status: ApplicationStatus) {
    setBusyId(app.id);
    try {
      const updated = await updateApplicationStatus(app.id, status);
      setApps((current) => current?.map((a) => (a.id === app.id ? updated : a)) ?? null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not update that application.");
    } finally {
      setBusyId(null);
    }
  }

  async function submitOutcome(app: Application) {
    setBusyId(app.id);
    try {
      await recordOutcome(app.id, {
        outcome_type: outcomeType,
        decided_at: new Date().toISOString(),
        rejection_reason: outcomeType === "rejected" ? rejectionReason || null : null,
      });
      setReportingId(null);
      setRejectionReason("");
      load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not record that outcome.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="field-shell">
      <FieldNav />
      <main className="field-page space-y-8">
        <div className="border-b border-field-rule pb-6">
          <h1 className="field-display text-2xl sm:text-3xl">MY APPLICATIONS</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-field-fg-muted">
            Every status change here is you telling us what happened — nothing on this page
            files anything on your behalf.
          </p>
        </div>

        {error && (
          <div role="alert" className="border border-field-alert-border bg-field-alert-bg p-3 font-field text-xs text-field-alert">
            {error}
          </div>
        )}

        {apps === null && <p className="font-field text-xs uppercase text-field-fg-muted">LOADING…</p>}
        {apps !== null && apps.length === 0 && (
          <p className="field-panel p-8 text-center text-sm text-field-fg-muted">
            No applications tracked yet. Start one from a scheme&apos;s deep-dive page.
          </p>
        )}

        <div className="space-y-4">
          {apps?.map((app) => {
            const isAlert = ALERT_STAGES.has(app.status);
            const nextStages = STAGES.filter((s) => s !== app.status);
            return (
              <article key={app.id} className={`field-panel p-5 ${isAlert ? "field-panel-active" : ""}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-field text-sm font-medium uppercase text-field-fg">{app.scheme_version_id}</p>
                    <p className="mt-1 font-field text-xs text-field-fg-muted">
                      UPDATED {new Date(app.last_status_update ?? app.created_at).toISOString().slice(0, 10)}
                    </p>
                  </div>
                  <span className={isAlert ? "field-status field-status-alert" : "field-status"}>
                    {app.status.toUpperCase()}
                  </span>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {nextStages.map((stage) => (
                    <button
                      key={stage}
                      type="button"
                      disabled={busyId === app.id}
                      onClick={() => advance(app, stage)}
                      className="field-button"
                    >
                      {busyId === app.id ? "…" : `MARK ${stage.toUpperCase()}`}
                    </button>
                  ))}
                  {app.status !== "approved" && app.status !== "rejected" && (
                    <button
                      type="button"
                      onClick={() => setReportingId(app.id)}
                      className="field-button border-field-alert text-field-alert"
                    >
                      REPORT OUTCOME
                    </button>
                  )}
                </div>

                {reportingId === app.id && (
                  <div className="mt-4 border border-field-rule-strong p-4">
                    <p className="font-field text-xs uppercase text-field-fg-muted">
                      REPORTING AN OUTCOME. EXACT TURNOVER IS NEVER SENT — ONLY A BAND, AT CAPTURE TIME.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {OUTCOME_TYPES.map((t) => (
                        <label key={t} className="field-choice-row">
                          <input
                            type="radio"
                            name={`outcome-${app.id}`}
                            checked={outcomeType === t}
                            onChange={() => setOutcomeType(t)}
                          />
                          <span className="text-field-fg">{t.replace("_", " ").toUpperCase()}</span>
                        </label>
                      ))}
                    </div>
                    {outcomeType === "rejected" && (
                      <div className="mt-3">
                        <label htmlFor={`reason-${app.id}`} className="field-input-label">REJECTION REASON</label>
                        <input
                          id={`reason-${app.id}`}
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          className="field-input"
                        />
                      </div>
                    )}
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        disabled={busyId === app.id}
                        onClick={() => submitOutcome(app)}
                        className="field-button field-button-primary"
                      >
                        {busyId === app.id ? "SAVING…" : "SUBMIT OUTCOME"}
                      </button>
                      <button type="button" onClick={() => setReportingId(null)} className="field-button">
                        CANCEL
                      </button>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </main>
    </div>
  );
}
