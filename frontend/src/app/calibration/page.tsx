"use client";

/*
THESIS: Calibration is the system reporting on its own honesty — a
reliability diagram read as instrument output, not a marketing chart —
where the reserved accent is spent only on the one direction the page's
own copy calls out as actually harmful: overconfidence.
OWN-WORLD: Field system — black ground, monospace type, hairline rules,
tabular readouts. The reliability diagram is the one place on this page
three genuinely distinct directional meanings (overconfident/
underconfident/well-calibrated) are real content, not decoration — so
they're differentiated by fill density (solid/hatched/outline) with color
reserved for the direction that matters, rather than forcing a false
single-accent reading onto a three-way semantic.
STORY: A visitor reads the headline ECE and direction as tabular data,
then the reliability diagram band by band, then an explainer for why
this measurement exists at all.
FORM: Rollout of the already-committed field-system direction (seed key
ca281bee, index 3) — this page extends that established world.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md.
*/

import { useEffect, useState } from "react";

import { FieldLoadingState, FieldSectionHeading } from "@/components/Ui";
import { FieldNav } from "@/components/FieldNav";
import { ApiError, getCalibration, type Calibration } from "@/lib/api";

export default function CalibrationPage() {
  const [data, setData] = useState<Calibration | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCalibration()
      .then(setData)
      .catch((caught) => {
        setError(caught instanceof ApiError ? caught.detail : "Could not load calibration data.");
      });
  }, []);

  if (error) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <div role="alert" className="field-panel field-panel-active mx-auto max-w-3xl p-6">
            <p className="text-field-fg">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="field-shell">
        <FieldNav />
        <div className="field-page">
          <FieldLoadingState label="Computing calibration" />
        </div>
      </div>
    );
  }

  return (
    <div className="field-shell">
      <FieldNav />
      <main className="field-page space-y-8">
        <FieldSectionHeading
          index="01"
          title="CONFIDENCE CALIBRATION"
          description="When Bharat OS states a confidence percentage, this measures whether that percentage tracks what actually happened — not just how it sounds."
        />

        {data.warning && (
          <div role="status" className="border border-field-alert-border bg-field-alert-bg p-3">
            <span className="font-field text-xs font-semibold uppercase text-field-alert">⚠ {data.warning}</span>
          </div>
        )}

        {data.sample_size === 0 ? (
          <div className="field-panel p-8 text-center">
            <p className="font-field text-lg font-semibold uppercase text-field-fg">No calibration data available yet</p>
            <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-field-fg-muted">
              This measurement runs against recorded outcomes or, absent those, labelled
              synthetic fixtures. Neither exists yet in this environment.
            </p>
          </div>
        ) : (
          <>
            <HeadlineStats data={data} />
            <ReliabilityDiagram buckets={data.buckets} />
            <Explainer />
          </>
        )}
      </main>
    </div>
  );
}

function HeadlineStats({ data }: { data: Calibration }) {
  const ece = data.expected_calibration_error;
  const direction = data.overall_direction;
  const isOverconfident = direction === "overconfident";

  return (
    <div className="field-panel p-6 sm:p-7">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div>
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Expected calibration error</p>
          <p className="mt-2 font-field text-4xl font-semibold tabular-nums text-field-fg sm:text-5xl">
            {ece !== null ? `${(ece * 100).toFixed(1)}%` : "—"}
          </p>
          <p className="mt-2 text-xs leading-5 text-field-fg-subtle">
            Average gap between stated confidence and observed outcome, weighted by how
            many cases fall in each band. Lower is better.
          </p>
        </div>

        <div>
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Overall tendency</p>
          <p className={`mt-2 font-field text-2xl font-semibold uppercase sm:text-3xl ${isOverconfident ? "text-field-alert" : "text-field-fg"}`}>
            {direction ?? "—"}
          </p>
          <p className="mt-2 text-xs leading-5 text-field-fg-subtle">
            Overconfidence is the direction that actually harms users — it sends people
            into applications they are less likely to win.
          </p>
        </div>

        <div>
          <p className="font-field text-[11px] uppercase tracking-[0.08em] text-field-fg-muted">Sample size</p>
          <p className="mt-2 font-field text-2xl font-semibold tabular-nums text-field-fg sm:text-3xl">
            {data.sample_size}
          </p>
          <p className="mt-2 text-xs leading-5 text-field-fg-subtle">
            {data.has_real_outcomes
              ? "Recorded application outcomes."
              : "Synthetic fixture cases — see the notice above."}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Three genuinely distinct directional meanings — differentiated by fill
 * pattern (solid / hatched / outline-only) rather than hue, so the
 * reserved alert color stays spent on exactly one thing (overconfident,
 * the direction the page's own copy calls out as actually harmful) while
 * the other two directions stay legible without introducing more color.
 */
const BUCKET_FILL: Record<string, string> = {
  overconfident: "bg-field-alert",
  underconfident: "bg-field-fg bg-[repeating-linear-gradient(45deg,transparent,transparent_2px,theme(colors.field.bg)_2px,theme(colors.field.bg)_4px)]",
  "well calibrated": "bg-field-fg",
  "no data": "bg-field-rule",
};

function ReliabilityDiagram({ buckets }: { buckets: Calibration["buckets"] }) {
  return (
    <div className="field-panel p-6 sm:p-7">
      <FieldSectionHeading
        index="02"
        title="STATED CONFIDENCE VS. WHAT ACTUALLY HAPPENED"
        description="Each pair of bars is one confidence band. The outline bar is what we predicted on average within that band; the filled bar is what actually happened. A perfectly calibrated system has matching bar heights in every band."
      />

      <div className="mt-8 flex items-end gap-3 border-b border-field-rule pb-1 sm:gap-6">
        {buckets.map((bucket) => (
          <BucketBars key={`${bucket.lower}-${bucket.upper}`} bucket={bucket} fillClass={BUCKET_FILL[bucket.direction] ?? "bg-field-rule"} />
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 font-field text-xs uppercase text-field-fg-muted">
        <LegendSwatch className="border border-field-rule-strong" label="STATED CONFIDENCE" />
        <LegendSwatch className="bg-field-fg" label="WELL CALIBRATED" />
        <LegendSwatch className={BUCKET_FILL.underconfident!} label="UNDERCONFIDENT" />
        <LegendSwatch className="bg-field-alert" label="OVERCONFIDENT" />
      </div>
    </div>
  );
}

function BucketBars({
  bucket,
  fillClass,
}: {
  bucket: Calibration["buckets"][number];
  fillClass: string;
}) {
  const CHART_HEIGHT_PX = 176; // 11rem, matches h-44 below
  const predictedHeight = Math.max(bucket.mean_predicted * CHART_HEIGHT_PX, bucket.count > 0 ? 2 : 0);
  const observedHeight = Math.max(bucket.observed_rate * CHART_HEIGHT_PX, bucket.count > 0 ? 2 : 0);

  return (
    <div className="flex flex-1 flex-col items-center gap-2">
      <div className="flex h-44 w-full items-end justify-center gap-1" aria-hidden="true">
        <div
          className="w-full max-w-[1.1rem] border border-field-rule-strong"
          style={{ height: `${predictedHeight}px` }}
          title={`Stated: ${(bucket.mean_predicted * 100).toFixed(0)}%`}
        />
        <div
          className={`w-full max-w-[1.1rem] ${fillClass}`}
          style={{ height: `${observedHeight}px` }}
          title={`Observed: ${(bucket.observed_rate * 100).toFixed(0)}%`}
        />
      </div>
      <p className="font-field text-[11px] tabular-nums text-field-fg-muted">
        {Math.round(bucket.lower * 100)}–{Math.round(bucket.upper * 100)}%
      </p>
      <p className="font-field text-[10px] text-field-fg-subtle">n={bucket.count}</p>
    </div>
  );
}

function LegendSwatch({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span aria-hidden="true" className={`inline-block h-2.5 w-2.5 ${className}`} />
      {label}
    </span>
  );
}

function Explainer() {
  return (
    <details className="field-panel p-6 sm:p-7">
      <summary className="cursor-pointer font-field text-sm font-semibold uppercase text-field-fg">WHAT IS CALIBRATION, AND WHY DOES IT MATTER?</summary>
      <div className="mt-4 space-y-3 text-sm leading-6 text-field-fg-muted">
        <p>
          A confidence score is a claim about the world: &ldquo;of the applications we rate
          70% confident, roughly 70% should actually succeed.&rdquo; If that claim is false,
          the number is worse than useless — a user calibrates their own effort against it.
        </p>
        <p>
          <span className="font-semibold text-field-fg">Expected Calibration Error</span> is the
          average gap between what we stated and what actually happened, weighted by how many
          cases fall into each confidence band. A single average can hide a bad bucket, which
          is why the diagram above shows every band individually rather than only the headline
          number.
        </p>
        <p>
          Overconfidence and underconfidence are not symmetric risks here.
          Overconfidence sends someone into a 40–200 hour application they are unlikely to
          win. Underconfidence at worst discourages someone from an application they would
          have won — a real cost, but a smaller one. That asymmetry is why overconfidence is
          the direction this measurement is built to catch.
        </p>
      </div>
    </details>
  );
}
