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

const STATE_STYLE: Record<string, string> = {
  met: "border-met-border bg-met-bg",
  unmet: "border-unmet-border bg-unmet-bg",
  cannot_verify: "border-unverified-border bg-unverified-bg",
  likely_met: "border-met-border bg-met-bg",
  likely_unmet: "border-unmet-border bg-unmet-bg",
  uncertain: "border-unverified-border bg-unverified-bg",
};

const STATE_LABEL: Record<string, string> = {
  met: "Met",
  unmet: "Not met",
  cannot_verify: "Cannot verify",
  likely_met: "Likely met",
  likely_unmet: "Likely not met",
  uncertain: "Uncertain",
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
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-subtle">
      <a
        href={sourceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-brand hover:underline"
      >
        Official source
      </a>
      <span>·</span>
      <span>
        {verifiedByHuman ? "Human-verified" : "Machine-extracted, pending human review"}
      </span>
      <span>·</span>
      <span className={isStale ? "font-medium text-unverified-fg" : ""}>
        {isStale
          ? `Last checked ${daysSinceVerified} days ago — confirm before relying on this`
          : `Checked ${daysSinceVerified} days ago`}
      </span>
    </div>
  );
}

export function HardCriterionRow({ criterion }: { criterion: HardCriterion }) {
  return (
    <div className={`border p-3 ${STATE_STYLE[criterion.state]}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium">{criterion.description}</p>
        <span className="shrink-0 border border-current/20 bg-white/60 px-2 py-0.5 text-xs font-semibold">
          {STATE_LABEL[criterion.state]}
        </span>
      </div>
      <p className="mt-1 text-sm text-ink-muted">{criterion.reason}</p>
      {criterion.missing_fields.length > 0 && (
        <p className="mt-1 text-xs text-unverified-fg">
          Add: {criterion.missing_fields.join(", ")}
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

  return (
    <div className={`border p-3 ${STATE_STYLE[criterion.verdict]}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{criterion.description}</p>
          <p className="mt-0.5 text-xs text-ink-subtle">Assessed by AI, not a fixed rule</p>
        </div>
        <span className="shrink-0 border border-current/20 bg-white/60 px-2 py-0.5 text-xs font-semibold">
          {STATE_LABEL[criterion.verdict]} · {formatConfidence(criterion.confidence)}
        </span>
      </div>

      <p className="mt-1 text-sm text-ink-muted">{criterion.reasoning}</p>

      {criterion.requires_human_review && (
        <p className="mt-1 text-xs font-medium text-unverified-fg">
          Confidence too low to rely on — this needs a human to review.
        </p>
      )}

      {criterion.evidence_that_would_strengthen.length > 0 && (
        <div className="mt-2 text-xs">
          <span className="text-ink-subtle">Would strengthen this: </span>
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
        className="mt-2 text-xs font-medium text-brand hover:underline"
      >
        {expanded ? "Hide" : "Show"} exactly why the AI reached this judgement
      </button>

      {expanded && (
        <div className="mt-2 space-y-1 rounded bg-white/70 p-3 font-mono text-xs">
          <p>
            <span className="text-ink-subtle">Model: </span>
            {criterion.audit_provider}/{criterion.audit_model}
          </p>
          <p>
            <span className="text-ink-subtle">Prompt version: </span>
            {criterion.audit_prompt_version}
          </p>
          <p>
            <span className="text-ink-subtle">Source: </span>
            {criterion.was_cached ? "cached from an earlier identical question" : "fresh call"}
          </p>
          {criterion.audit_prompt && (
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-ink/5 p-2">
              {criterion.audit_prompt}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
