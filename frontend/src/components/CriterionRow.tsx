"use client";

import { useState } from "react";

import { formatConfidence } from "@/lib/format";

type HardCriterion = {
  criterion_id: string;
  description: string;
  state: "met" | "unmet" | "cannot_verify";
  reason: string;
  missing_fields: string[];
  source_url: string;
  source_quote: string | null;
  last_verified_at: string;
  verified_by_human: boolean;
  days_since_verified: number;
  is_stale: boolean;
};

type SoftCriterion = {
  criterion_id: string;
  description: string;
  verdict: "likely_met" | "likely_unmet" | "uncertain";
  confidence: number;
  reasoning: string;
  evidence_that_would_strengthen: string[];
  requires_human_review: boolean;
  audit_prompt: string | null;
  audit_provider: string;
  audit_model: string;
  audit_prompt_version: string;
  was_cached: boolean;
  source_url: string;
  source_quote: string | null;
  last_verified_at: string;
  verified_by_human: boolean;
  days_since_verified: number;
  is_stale: boolean;
};

/**
 * Field-system status presentation for all six criterion states. Only
 * the two "not met" states spend the reserved alert accent — the other
 * four (met, cannot_verify, likely_met, uncertain) render as neutral
 * field-status chips, differentiated by their text label alone. This is
 * the real test of the redesign's "one accent" discipline: six distinct
 * states, one color spent on exactly the two that block the applicant.
 */
const ALERT_STATES = new Set(["unmet", "likely_unmet"]);

const STATE_LABEL: Record<string, string> = {
  met: "MET",
  unmet: "NOT MET",
  cannot_verify: "CANNOT VERIFY",
  likely_met: "LIKELY MET",
  likely_unmet: "LIKELY NOT MET",
  uncertain: "UNCERTAIN",
};

function ProvenanceLine({
  sourceUrl,
  verifiedByHuman,
  daysSinceVerified,
  isStale,
}: {
  sourceUrl: string;
  verifiedByHuman: boolean;
  daysSinceVerified: number;
  isStale: boolean;
}) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 font-field text-[11px] text-field-fg-subtle">
      <a
        href={sourceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-field-fg-muted underline underline-offset-2 hover:text-field-fg"
      >
        OFFICIAL SOURCE
      </a>
      <span>·</span>
      <span>
        {verifiedByHuman ? "HUMAN-VERIFIED" : "MACHINE-EXTRACTED, PENDING REVIEW"}
      </span>
      <span>·</span>
      <span className={isStale ? "font-semibold text-field-alert" : ""}>
        {isStale
          ? `LAST CHECKED ${daysSinceVerified}D AGO — CONFIRM BEFORE RELYING ON THIS`
          : `CHECKED ${daysSinceVerified}D AGO`}
      </span>
    </div>
  );
}

export function HardCriterionRow({ criterion }: { criterion: HardCriterion }) {
  const isAlert = ALERT_STATES.has(criterion.state);
  return (
    <div className={`field-panel p-4 ${isAlert ? "field-panel-active" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-field-fg">{criterion.description}</p>
        <span className={isAlert ? "field-status field-status-alert" : "field-status"}>
          {STATE_LABEL[criterion.state]}
        </span>
      </div>
      <p className="mt-1 text-sm text-field-fg-muted">{criterion.reason}</p>
      {criterion.missing_fields.length > 0 && (
        <p className="mt-1 font-field text-xs text-field-alert">
          ADD: {criterion.missing_fields.join(", ")}
        </p>
      )}
      <ProvenanceLine
        sourceUrl={criterion.source_url}
        verifiedByHuman={criterion.verified_by_human}
        daysSinceVerified={criterion.days_since_verified}
        isStale={criterion.is_stale}
      />
    </div>
  );
}

/**
 * A judgement-based criterion, with the full audit trail behind a disclosure.
 *
 * The trail is not a debugging aid bolted on afterwards — it is the direct answer
 * to "how do I know this isn't hallucinating". Expanding it shows exactly what
 * was asked, which model answered, and whether the answer came from cache.
 */
export function SoftCriterionRow({ criterion }: { criterion: SoftCriterion }) {
  const [expanded, setExpanded] = useState(false);
  const isAlert = ALERT_STATES.has(criterion.verdict);

  return (
    <div className={`field-panel p-4 ${isAlert ? "field-panel-active" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-field-fg">{criterion.description}</p>
          <p className="mt-0.5 font-field text-[11px] text-field-fg-subtle">ASSESSED BY AI, NOT A FIXED RULE</p>
        </div>
        <span className={isAlert ? "field-status field-status-alert" : "field-status"}>
          {STATE_LABEL[criterion.verdict]} · {formatConfidence(criterion.confidence)}
        </span>
      </div>

      <p className="mt-1 text-sm text-field-fg-muted">{criterion.reasoning}</p>

      {criterion.requires_human_review && (
        <p className="mt-1 font-field text-xs font-semibold text-field-alert">
          CONFIDENCE TOO LOW TO RELY ON — THIS NEEDS A HUMAN TO REVIEW.
        </p>
      )}

      {criterion.evidence_that_would_strengthen.length > 0 && (
        <div className="mt-2 text-xs text-field-fg-muted">
          <span className="text-field-fg-subtle">Would strengthen this: </span>
          {criterion.evidence_that_would_strengthen.join("; ")}
        </div>
      )}

      <ProvenanceLine
        sourceUrl={criterion.source_url}
        verifiedByHuman={criterion.verified_by_human}
        daysSinceVerified={criterion.days_since_verified}
        isStale={criterion.is_stale}
      />

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="mt-2 font-field text-xs font-semibold uppercase text-field-fg-muted hover:text-field-fg"
      >
        {expanded ? "HIDE" : "SHOW"} EXACTLY WHY THE AI REACHED THIS JUDGEMENT
      </button>

      {expanded && (
        <div className="mt-2 space-y-1 border border-field-rule bg-field-bg p-3 font-field text-xs text-field-fg-muted">
          <p>
            <span className="text-field-fg-subtle">MODEL: </span>
            {criterion.audit_provider}/{criterion.audit_model}
          </p>
          <p>
            <span className="text-field-fg-subtle">PROMPT VERSION: </span>
            {criterion.audit_prompt_version}
          </p>
          <p>
            <span className="text-field-fg-subtle">SOURCE: </span>
            {criterion.was_cached ? "CACHED FROM AN EARLIER IDENTICAL QUESTION" : "FRESH CALL"}
          </p>
          {criterion.audit_prompt && (
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap border border-field-rule bg-black p-2 text-field-fg-subtle">
              {criterion.audit_prompt}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
