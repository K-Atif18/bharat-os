"use client";

import { useEffect, useState } from "react";

import { FieldNav } from "@/components/FieldNav";
import { ApiError, apiBaseUrl, getDeadlineCalendar, type DeadlineCalendar } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  comfortable: "COMFORTABLE",
  tight: "TIGHT",
  unreachable: "UNREACHABLE",
  closed: "CLOSED",
  no_deadline: "ROLLING",
};

const ALERT_STATUSES = new Set(["unreachable", "closed"]);

export default function DeadlinesPage() {
  const [calendar, setCalendar] = useState<DeadlineCalendar | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDeadlineCalendar()
      .then(setCalendar)
      .catch((caught) => setError(caught instanceof ApiError ? caught.detail : "Could not load your deadlines."));
  }, []);

  return (
    <div className="field-shell">
      <FieldNav />
      <main className="field-page space-y-8">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-field-rule pb-6">
          <div>
            <h1 className="field-display text-2xl sm:text-3xl">DEADLINE CALENDAR</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-field-fg-muted">
              Every scheme you are not ruled out of, with whether its deadline is actually
              reachable given your document gaps — not just the date.
            </p>
          </div>
          <a href={`${apiBaseUrl()}/deadlines/calendar.ics`} className="field-button field-button-primary">
            DOWNLOAD .ICS
          </a>
        </div>

        {error && (
          <div role="alert" className="border border-field-alert-border bg-field-alert-bg p-3 font-field text-xs text-field-alert">
            {error}
          </div>
        )}

        {calendar === null && !error && <p className="font-field text-xs uppercase text-field-fg-muted">LOADING…</p>}

        {calendar && (
          <>
            {calendar.unreachable_count > 0 && (
              <div className="border border-field-alert-border bg-field-alert-bg p-3 font-field text-xs uppercase text-field-alert">
                ⚠ {calendar.unreachable_count} {calendar.unreachable_count === 1 ? "DEADLINE" : "DEADLINES"} LIKELY UNREACHABLE GIVEN CURRENT DOCUMENT GAPS
              </div>
            )}

            {calendar.deadlines.length === 0 && (
              <p className="field-panel p-8 text-center text-sm text-field-fg-muted">No dated opportunities right now.</p>
            )}

            <div className="space-y-3">
              {calendar.deadlines.map((item) => {
                const isAlert = ALERT_STATUSES.has(item.status);
                return (
                  <article key={item.scheme_version_id} className={`field-panel p-4 ${isAlert ? "field-panel-active" : ""}`}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <p className="font-field text-sm font-medium uppercase text-field-fg">{item.name}</p>
                      <span className={isAlert ? "field-status field-status-alert" : "field-status"}>
                        {STATUS_LABEL[item.status] ?? item.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-4 font-field text-xs text-field-fg-muted">
                      {item.close_date && <span>CLOSES {item.close_date}</span>}
                      {item.days_remaining !== null && <span>{item.days_remaining}D REMAINING</span>}
                      {item.margin_days !== null && <span>{item.margin_days}D MARGIN</span>}
                    </div>
                    {item.bottleneck_document && (
                      <p className="mt-2 font-field text-xs text-field-alert">
                        BOTTLENECK: {item.bottleneck_document}
                        {item.bottleneck_days !== null && ` (~${item.bottleneck_days}D TO OBTAIN)`}
                      </p>
                    )}
                  </article>
                );
              })}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
