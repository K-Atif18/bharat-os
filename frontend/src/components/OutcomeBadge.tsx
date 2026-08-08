import type { MatchOutcome } from "@/lib/api";
import { formatConfidence } from "@/lib/format";

const PRESENTATION: Record<MatchOutcome, { label: string; className: string; dot: string }> = {
  eligible: {
    label: "All checkable requirements met",
    className: "border-met-border bg-met-bg text-met-fg",
    dot: "bg-met-fg",
  },
  needs_more_data: {
    label: "Needs more information",
    className: "border-unverified-border bg-unverified-bg text-unverified-fg",
    dot: "bg-unverified-fg",
  },
  ruled_out: {
    label: "Requirement not met",
    className: "border-unmet-border bg-unmet-bg text-unmet-fg",
    dot: "bg-unmet-fg",
  },
  judgement_only: {
    label: "Requires human judgement",
    className: "border-info-border bg-info-bg text-info-fg",
    dot: "bg-info-fg",
  },
};

export function OutcomeBadge({ outcome }: { outcome: MatchOutcome }) {
  const { label, className, dot } = PRESENTATION[outcome];
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${className}`}>
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

export function ConfidenceMeter({
  confidence,
  met,
  total,
}: {
  confidence: number;
  met: number;
  total: number;
}) {
  const percentage = Math.round(confidence * 100);
  const requirementText = total === 0 ? "no automatic checks" : `${met} of ${total} requirements`;

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="text-sm font-semibold text-ink">
          <span className="data-value">{formatConfidence(confidence)}</span> confirmed
        </span>
        <span className="text-xs text-ink-subtle">{requirementText}</span>
      </div>
      <div
        className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={`${percentage} percent confirmed; ${requirementText}`}
        aria-label="Confirmed requirements"
      >
        <div className="h-full rounded-full bg-civic-green transition-[width] duration-300" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}
