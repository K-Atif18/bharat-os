import Link from "next/link";

import { ConfidenceMeter, OutcomeBadge } from "@/components/OutcomeBadge";
import type { Match } from "@/lib/api";
import { formatDeadline, formatRupees, humaniseField, stalenessNote } from "@/lib/format";

const DIFFICULTY_LABEL: Record<string, string> = {
  low: "Straightforward",
  medium: "Moderate effort",
  high: "Demanding",
};

const RAIL_COLOR: Record<string, string> = {
  eligible: "border-l-met-fg",
  needs_more_data: "border-l-unverified-fg",
  ruled_out: "border-l-unmet-fg",
  judgement_only: "border-l-info-fg",
};

export function SchemeCard({ match }: { match: Match }) {
  const total = match.criteria_met + match.criteria_unmet + match.criteria_unverifiable;
  const deadline = formatDeadline(match.next_deadline);
  const staleness = stalenessNote(match.max_days_since_verified);

  return (
    <article className={`panel overflow-hidden border-l-4 ${RAIL_COLOR[match.outcome] ?? "border-l-surface-strong"}`}>
      <div className="p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 max-w-2xl">
            <p className="meta-line">{match.administering_ministry}</p>
            <h3 className="mt-1 font-display text-xl font-semibold leading-snug tracking-[-0.015em] sm:text-2xl">
              <Link href={`/schemes/${match.slug}`} className="decoration-brand/30 underline-offset-4 hover:text-brand hover:underline">
                {match.name}
              </Link>
            </h3>
          </div>
          <OutcomeBadge outcome={match.outcome} />
        </div>

        <p className="mt-3 max-w-3xl text-sm leading-6 text-ink-muted">{match.summary}</p>

        <div className="mt-5 max-w-2xl">
          <ConfidenceMeter confidence={match.confidence} met={match.criteria_met} total={total} />
        </div>

        <dl className="mt-5 grid grid-cols-2 border-y border-surface-border py-4 sm:grid-cols-4">
          <div className="pr-3 sm:pr-5">
            <dt className="meta-line">Benefit up to</dt>
            <dd className="data-value mt-1 text-sm font-semibold text-ink">{formatRupees(match.benefit_value_max)}</dd>
          </div>
          <div className="border-l border-surface-border px-3 sm:px-5">
            <dt className="meta-line">Application effort</dt>
            <dd className="mt-1 text-sm font-semibold text-ink">
              {DIFFICULTY_LABEL[match.application_difficulty] ?? match.application_difficulty}
              {match.estimated_effort_hours ? ` · ~${match.estimated_effort_hours}h` : ""}
            </dd>
          </div>
          <div className="mt-4 border-t border-surface-border pr-3 pt-4 sm:mt-0 sm:border-l sm:border-t-0 sm:px-5 sm:pt-0">
            <dt className="meta-line">Next deadline</dt>
            <dd className="data-value mt-1 text-sm font-semibold text-ink">{deadline ?? "Rolling"}</dd>
          </div>
          <div className="mt-4 border-l border-t border-surface-border pl-3 pt-4 sm:mt-0 sm:border-t-0 sm:px-5 sm:pt-0">
            <dt className="meta-line">Human judgement</dt>
            <dd className="mt-1 text-sm font-semibold text-ink">{match.soft_criteria_count === 0 ? "None" : `${match.soft_criteria_count} criteria`}</dd>
          </div>
        </dl>

        {match.missing_fields.length > 0 && (
          <div className="notice mt-4 border-unverified-border bg-unverified-bg text-unverified-fg">
            <p className="font-semibold">Profile evidence can settle more of this match</p>
            <p className="mt-1 text-xs leading-5">
              Add your {match.missing_fields.map(humaniseField).join(", ")} to settle {match.criteria_unverifiable === 1 ? "1 open requirement" : `${match.criteria_unverifiable} open requirements`}.
            </p>
          </div>
        )}

        {staleness && <p className="mt-3 text-xs leading-5 text-ink-subtle">{staleness} — confirm against the official source before applying.</p>}

        <div className="mt-5 flex justify-end">
          <Link href={`/schemes/${match.slug}`} className="button-quiet">
            Open eligibility, documents and draft <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>
    </article>
  );
}

export function RuledOutCard({ match }: { match: Match }) {
  return (
    <article className="border-l-2 border-unmet-fg bg-surface px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
        <h3 className="font-display text-lg font-semibold">
          <Link href={`/schemes/${match.slug}`} className="hover:text-brand hover:underline">
            {match.name}
          </Link>
        </h3>
        <span className="shrink-0 text-xs font-semibold text-unmet-fg">
          {match.criteria_unmet === 1 ? "1 requirement not met" : `${match.criteria_unmet} requirements not met`}
        </span>
      </div>
      <p className="mt-1 text-xs leading-5 text-ink-subtle">Open the scheme to see the exact requirement and whether it is something you can change.</p>
    </article>
  );
}
