import { FieldSectionHeading } from "@/components/Ui";
import type { SchemeIntelligence } from "@/lib/api";

const TURNOVER_BAND_LABELS: Record<string, string> = {
  "under-10L": "Under ₹10L",
  "10L-1Cr": "₹10L – ₹1Cr",
  "1Cr-5Cr": "₹1Cr – ₹5Cr",
  "5Cr-100Cr": "₹5Cr – ₹100Cr",
  "100Cr+": "₹100Cr+",
};

/**
 * Outcome intelligence — "what actually happens", not what the guidelines
 * claim. Aggregated, de-identified statistics from recorded outcomes for one
 * scheme: approval rate, common rejection reasons, timelines, and approval
 * rate segmented by turnover band. Never a single applicant's row.
 *
 * Mirrors the deep-dive page's own freshness-panel pattern: this is fetched
 * and rendered independently of the eligibility breakdown, and its absence
 * (a scheme with zero recorded outcomes) is a normal, expected state, not an
 * error — the calling page renders this component only once data has
 * resolved, and this component itself decides what "no data yet" looks like.
 */
export function IntelligencePanel({ intel }: { intel: SchemeIntelligence }) {
  if (intel.total_outcomes_recorded === 0) {
    return (
      <section className="field-panel p-6 sm:p-7">
        <FieldSectionHeading index="05" title="WHAT ACTUALLY HAPPENS" />
        <p className="mt-4 text-sm leading-6 text-field-fg-muted">
          No outcomes recorded yet for this scheme. Real approval rates, timelines and
          rejection reasons will appear here once applicants report their results.
        </p>
      </section>
    );
  }

  const bands = Object.entries(intel.approval_rate_by_turnover_band).filter(
    ([, rate]) => rate !== null,
  ) as [string, number][];

  return (
    <section className="field-panel p-6 sm:p-7">
      <FieldSectionHeading
        index="05"
        title="WHAT ACTUALLY HAPPENS"
        description="Aggregated from recorded application outcomes for this scheme — never a single applicant's result."
      />

      {!intel.has_real_outcomes && (
        <div role="status" className="mt-4 border border-field-alert-border bg-field-alert-bg p-3">
          <span className="font-field text-xs font-semibold uppercase text-field-alert">⚠ BASED ON SYNTHETIC DATA, NOT REAL OUTCOMES.</span>{" "}
          <span className="text-sm text-field-fg-muted">
            This demonstrates the measurement working, not this scheme&apos;s actual approval rate.
          </span>
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-3">
        <div>
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Approval rate</p>
          <p className="mt-1 font-field text-3xl font-semibold tabular-nums text-field-fg">
            {intel.approval_rate !== null ? `${Math.round(intel.approval_rate * 100)}%` : "—"}
          </p>
        </div>
        <div>
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Avg. days to decision</p>
          <p className="mt-1 font-field text-3xl font-semibold tabular-nums text-field-fg">
            {intel.average_days_to_decision !== null
              ? Math.round(intel.average_days_to_decision)
              : "—"}
          </p>
        </div>
        <div>
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Outcomes recorded</p>
          <p className="mt-1 font-field text-3xl font-semibold tabular-nums text-field-fg">
            {intel.total_outcomes_recorded}
          </p>
        </div>
      </div>

      {bands.length > 0 && (
        <div className="mt-7 border-t border-field-rule pt-5">
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Approval rate by turnover band</p>
          <dl className="mt-3 space-y-2">
            {bands.map(([band, rate]) => (
              <div key={band} className="flex items-center gap-3">
                <dt className="w-28 shrink-0 font-field text-[11px] text-field-fg-muted">
                  {TURNOVER_BAND_LABELS[band] ?? band}
                </dt>
                <dd className="flex-1">
                  <div className="h-1.5 w-full border border-field-rule">
                    <div
                      className="h-full bg-field-fg"
                      style={{ width: `${Math.round(rate * 100)}%` }}
                    />
                  </div>
                </dd>
                <dd className="w-12 shrink-0 text-right font-field text-xs tabular-nums text-field-fg">
                  {Math.round(rate * 100)}%
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {intel.common_rejection_reasons.length > 0 && (
        <div className="mt-7 border-t border-field-rule pt-5">
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Most common rejection reasons</p>
          <ol className="mt-3 space-y-2">
            {intel.common_rejection_reasons.map((r) => (
              <li key={r.reason} className="flex items-start gap-2 text-sm">
                <span aria-hidden="true" className="mt-0.5 text-field-alert">
                  ✗
                </span>
                <span className="flex-1 text-field-fg">{r.reason}</span>
                <span className="shrink-0 font-field text-xs tabular-nums text-field-fg-muted">{r.count}×</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <p className="mt-6 text-xs leading-5 text-field-fg-subtle">{intel.data_note}</p>
    </section>
  );
}
