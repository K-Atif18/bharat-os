import Link from "next/link";

import { ConfidenceMeter, OutcomeBadge } from "@/components/OutcomeBadge";
import type { Match } from "@/lib/api";
import { formatDeadline, formatRupees, humaniseField, stalenessNote } from "@/lib/format";

const DIFFICULTY_LABEL: Record<string, string> = {
  low: "STRAIGHTFORWARD",
  medium: "MODERATE EFFORT",
  high: "DEMANDING",
};

export function SchemeCard({ match }: { match: Match }) {
  const total = match.criteria_met + match.criteria_unmet + match.criteria_unverifiable;
  const deadline = formatDeadline(match.next_deadline);
  const staleness = stalenessNote(match.max_days_since_verified);
  const isAlert = match.outcome === "ruled_out";

  return (
    <article className={`field-panel ${isAlert ? "field-panel-active" : ""}`}>
      <div className="p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 max-w-2xl">
            <p className="font-field text-[11px] uppercase tracking-[0.1em] text-field-fg-muted">
              {match.administering_ministry}
            </p>
            <h3 className="mt-1 font-field text-lg font-semibold uppercase leading-snug sm:text-xl">
              <Link href={`/schemes/${match.slug}`} className="text-field-fg hover:text-field-fg-muted">
                {match.name}
              </Link>
            </h3>
          </div>
          <OutcomeBadge outcome={match.outcome} />
        </div>

        <p className="mt-3 max-w-3xl text-sm leading-6 text-field-fg-muted">{match.summary}</p>

        <div className="mt-5 max-w-2xl">
          <ConfidenceMeter confidence={match.confidence} met={match.criteria_met} total={total} />
        </div>

        <dl className="mt-5 grid grid-cols-2 border-y border-field-rule py-4 sm:grid-cols-4">
          <div className="pr-3 sm:pr-5">
            <dt className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Benefit up to</dt>
            <dd className="mt-1 font-field text-sm font-semibold tabular-nums text-field-fg">{formatRupees(match.benefit_value_max)}</dd>
          </div>
          <div className="border-l border-field-rule px-3 sm:px-5">
            <dt className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Application effort</dt>
            <dd className="mt-1 font-field text-sm font-semibold text-field-fg">
              {DIFFICULTY_LABEL[match.application_difficulty] ?? match.application_difficulty}
              {match.estimated_effort_hours ? ` · ~${match.estimated_effort_hours}H` : ""}
            </dd>
          </div>
          <div className="mt-4 border-t border-field-rule pr-3 pt-4 sm:mt-0 sm:border-l sm:border-t-0 sm:px-5 sm:pt-0">
            <dt className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Next deadline</dt>
            <dd className="mt-1 font-field text-sm font-semibold tabular-nums text-field-fg">{deadline ?? "Rolling"}</dd>
          </div>
          <div className="mt-4 border-l border-t border-field-rule pl-3 pt-4 sm:mt-0 sm:border-t-0 sm:px-5 sm:pt-0">
            <dt className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Human judgement</dt>
            <dd className="mt-1 font-field text-sm font-semibold text-field-fg">{match.soft_criteria_count === 0 ? "None" : `${match.soft_criteria_count} criteria`}</dd>
          </div>
        </dl>

        {match.missing_fields.length > 0 && (
          <div className="field-panel mt-4 p-3">
            <p className="font-field text-xs font-semibold uppercase text-field-fg">Profile evidence can settle more of this match</p>
            <p className="mt-1 text-xs leading-5 text-field-fg-muted">
              Add your {match.missing_fields.map(humaniseField).join(", ")} to settle {match.criteria_unverifiable === 1 ? "1 open requirement" : `${match.criteria_unverifiable} open requirements`}.
            </p>
          </div>
        )}

        {staleness && <p className="mt-3 text-xs leading-5 text-field-fg-subtle">{staleness} — confirm against the official source before applying.</p>}

        <div className="mt-5 flex justify-end">
          <Link href={`/schemes/${match.slug}`} className="field-button">
            OPEN ELIGIBILITY, DOCUMENTS AND DRAFT →
          </Link>
        </div>
      </div>
    </article>
  );
}

export function RuledOutCard({ match }: { match: Match }) {
  return (
    <article className="field-panel field-panel-active px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
        <h3 className="font-field text-base font-semibold uppercase">
          <Link href={`/schemes/${match.slug}`} className="text-field-fg hover:text-field-fg-muted">
            {match.name}
          </Link>
        </h3>
        <span className="shrink-0 font-field text-xs font-semibold uppercase text-field-alert">
          {match.criteria_unmet === 1 ? "1 requirement not met" : `${match.criteria_unmet} requirements not met`}
        </span>
      </div>
      <p className="mt-1 text-xs leading-5 text-field-fg-subtle">Open the scheme to see the exact requirement and whether it is something you can change.</p>
    </article>
  );
}
