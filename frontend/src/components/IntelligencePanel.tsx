import { SectionHeading } from "@/components/Ui";
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
      <section className="panel p-6 sm:p-7">
        <SectionHeading eyebrow="Process intelligence" title="What actually happens" />
        <p className="mt-4 text-sm leading-6 text-ink-muted">
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
    <section className="panel p-6 sm:p-7">
      <SectionHeading
        eyebrow="Process intelligence"
        title="What actually happens"
        description="Aggregated from recorded application outcomes for this scheme — never a single applicant's result."
      />

      {!intel.has_real_outcomes && (
        <div role="status" className="notice mt-4 border-unverified-border bg-unverified-bg text-unverified-fg">
          <span className="font-semibold">⚠ Based on synthetic data, not real outcomes.</span>{" "}
          This demonstrates the measurement working, not this scheme&apos;s actual approval rate.
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-3">
        <div>
          <p className="meta-line">Approval rate</p>
          <p className="data-value mt-1 text-3xl font-semibold text-civic-navy">
            {intel.approval_rate !== null ? `${Math.round(intel.approval_rate * 100)}%` : "—"}
          </p>
        </div>
        <div>
          <p className="meta-line">Avg. days to decision</p>
          <p className="data-value mt-1 text-3xl font-semibold text-ink">
            {intel.average_days_to_decision !== null
              ? Math.round(intel.average_days_to_decision)
              : "—"}
          </p>
        </div>
        <div>
          <p className="meta-line">Outcomes recorded</p>
          <p className="data-value mt-1 text-3xl font-semibold text-ink">
            {intel.total_outcomes_recorded}
          </p>
        </div>
      </div>

      {bands.length > 0 && (
        <div className="mt-7 border-t border-surface-strong pt-5">
          <p className="meta-line">Approval rate by turnover band</p>
          <dl className="mt-3 space-y-2">
            {bands.map(([band, rate]) => (
              <div key={band} className="flex items-center gap-3">
                <dt className="w-28 shrink-0 text-xs text-ink-muted">
                  {TURNOVER_BAND_LABELS[band] ?? band}
                </dt>
                <dd className="flex-1">
                  <div className="h-2 w-full overflow-hidden rounded-full bg-surface-sunken">
                    <div
                      className="h-full rounded-full bg-brand"
                      style={{ width: `${Math.round(rate * 100)}%` }}
                    />
                  </div>
                </dd>
                <dd className="data-value w-12 shrink-0 text-right text-xs text-ink">
                  {Math.round(rate * 100)}%
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {intel.common_rejection_reasons.length > 0 && (
        <div className="mt-7 border-t border-surface-strong pt-5">
          <p className="meta-line">Most common rejection reasons</p>
          <ol className="mt-3 space-y-2">
            {intel.common_rejection_reasons.map((r) => (
              <li key={r.reason} className="flex items-start gap-2 text-sm">
                <span aria-hidden="true" className="mt-0.5 text-unmet-fg">
                  ✗
                </span>
                <span className="flex-1 text-ink">{r.reason}</span>
                <span className="meta-line shrink-0">{r.count}×</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <p className="mt-6 text-xs leading-5 text-ink-subtle">{intel.data_note}</p>
    </section>
  );
}
