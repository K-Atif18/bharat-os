import type { MatchOutcome } from "@/lib/api";
import { formatConfidence } from "@/lib/format";

/**
 * Field-system status presentation. Every outcome except "ruled_out"
 * uses the neutral field-status chip — the reserved alert accent is
 * spent only on the one state that actually blocks the applicant,
 * matching the rule established for the rest of this redesign: color is
 * a reinforcement of a text label, never a substitute for one.
 */
const PRESENTATION: Record<MatchOutcome, { label: string; alert: boolean }> = {
  eligible: { label: "ALL CHECKABLE REQUIREMENTS MET", alert: false },
  needs_more_data: { label: "NEEDS MORE INFORMATION", alert: false },
  ruled_out: { label: "REQUIREMENT NOT MET", alert: true },
  judgement_only: { label: "REQUIRES HUMAN JUDGEMENT", alert: false },
};

export function OutcomeBadge({ outcome }: { outcome: MatchOutcome }) {
  const { label, alert } = PRESENTATION[outcome];
  return (
    <span className={alert ? "field-status field-status-alert" : "field-status"}>{label}</span>
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
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 font-field text-xs">
        <span className="text-field-fg">
          <span className="tabular-nums">{formatConfidence(confidence)}</span> CONFIRMED
        </span>
        <span className="text-field-fg-muted">{requirementText}</span>
      </div>
      <div
        className="mt-2 h-1.5 w-full overflow-hidden border border-field-rule"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={`${percentage} percent confirmed; ${requirementText}`}
        aria-label="Confirmed requirements"
      >
        <div className="h-full bg-field-fg transition-[width] duration-300" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}
