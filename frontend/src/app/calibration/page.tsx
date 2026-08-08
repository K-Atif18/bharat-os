"use client";

import { useEffect, useState } from "react";

import { LoadingState, SectionHeading } from "@/components/Ui";
import { ApiError, getCalibration, type Calibration } from "@/lib/api";

/**
 * Confidence calibration — "when we say 80% confident, are we actually right
 * 80% of the time?"
 *
 * This page is the visible half of services/calibration.py's measurement
 * harness. The reliability diagram below is plain CSS bars, not a charting
 * library — five buckets is a small, fixed shape that does not need one, and
 * every value on the page comes directly from the API response rather than
 * being computed client-side, so there is exactly one place (the backend)
 * that can be wrong about the numbers.
 */
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
      <div role="alert" className="notice mx-auto max-w-3xl border-unmet-border bg-unmet-bg text-unmet-fg">
        {error}
      </div>
    );
  }

  if (!data) {
    return <LoadingState label="Computing calibration" />;
  }

  return (
    <div className="page-stack">
      <SectionHeading
        eyebrow="Model accuracy"
        title="Confidence calibration"
        description="When Bharat OS states a confidence percentage, this measures whether that percentage tracks what actually happened — not just how it sounds."
      />

      {data.warning && (
        <div role="status" className="notice border-unverified-border bg-unverified-bg text-unverified-fg">
          <span className="font-semibold">⚠ {data.warning}</span>
        </div>
      )}

      {data.sample_size === 0 ? (
        <div className="panel p-8 text-center">
          <p className="section-title">No calibration data available yet</p>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-ink-muted">
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
    </div>
  );
}

function HeadlineStats({ data }: { data: Calibration }) {
  const ece = data.expected_calibration_error;
  const direction = data.overall_direction;

  const directionTone =
    direction === "overconfident"
      ? "text-unmet-fg"
      : direction === "underconfident"
        ? "text-unverified-fg"
        : "text-met-fg";

  return (
    <div className="panel p-6 sm:p-7">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div>
          <p className="meta-line">Expected calibration error</p>
          <p className="data-value mt-2 text-4xl font-semibold text-civic-navy sm:text-5xl">
            {ece !== null ? `${(ece * 100).toFixed(1)}%` : "—"}
          </p>
          <p className="mt-2 text-xs leading-5 text-ink-subtle">
            Average gap between stated confidence and observed outcome, weighted by how
            many cases fall in each band. Lower is better.
          </p>
        </div>

        <div>
          <p className="meta-line">Overall tendency</p>
          <p className={`data-value mt-2 text-2xl font-semibold sm:text-3xl ${directionTone}`}>
            {direction ?? "—"}
          </p>
          <p className="mt-2 text-xs leading-5 text-ink-subtle">
            Overconfidence is the direction that actually harms users — it sends people
            into applications they are less likely to win.
          </p>
        </div>

        <div>
          <p className="meta-line">Sample size</p>
          <p className="data-value mt-2 text-2xl font-semibold text-ink sm:text-3xl">
            {data.sample_size}
          </p>
          <p className="mt-2 text-xs leading-5 text-ink-subtle">
            {data.has_real_outcomes
              ? "Recorded application outcomes."
              : "Synthetic fixture cases — see the notice above."}
          </p>
        </div>
      </div>
    </div>
  );
}

function ReliabilityDiagram({ buckets }: { buckets: Calibration["buckets"] }) {
  const directionColor: Record<string, string> = {
    overconfident: "bg-unmet-fg",
    underconfident: "bg-unverified-fg",
    "well calibrated": "bg-met-fg",
    "no data": "bg-surface-strong",
  };

  return (
    <div className="panel p-6 sm:p-7">
      <SectionHeading
        eyebrow="Reliability diagram"
        title="Stated confidence vs. what actually happened"
        description="Each pair of bars is one confidence band. The grey bar is what we predicted on average within that band; the coloured bar is what actually happened. A perfectly calibrated system has matching bar heights in every band."
      />

      <div className="mt-8 flex items-end gap-3 border-b border-surface-strong pb-1 sm:gap-6">
        {buckets.map((bucket) => (
          <BucketBars key={`${bucket.lower}-${bucket.upper}`} bucket={bucket} colorClass={directionColor[bucket.direction] ?? "bg-surface-strong"} />
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-ink-muted">
        <LegendSwatch className="bg-surface-strong" label="Stated confidence" />
        <LegendSwatch className="bg-met-fg" label="Well calibrated" />
        <LegendSwatch className="bg-unverified-fg" label="Underconfident" />
        <LegendSwatch className="bg-unmet-fg" label="Overconfident" />
      </div>
    </div>
  );
}

function BucketBars({
  bucket,
  colorClass,
}: {
  bucket: Calibration["buckets"][number];
  colorClass: string;
}) {
  const CHART_HEIGHT_PX = 176; // 11rem, matches h-44 below
  const predictedHeight = Math.max(bucket.mean_predicted * CHART_HEIGHT_PX, bucket.count > 0 ? 2 : 0);
  const observedHeight = Math.max(bucket.observed_rate * CHART_HEIGHT_PX, bucket.count > 0 ? 2 : 0);

  return (
    <div className="flex flex-1 flex-col items-center gap-2">
      <div className="flex h-44 w-full items-end justify-center gap-1" aria-hidden="true">
        <div
          className="w-full max-w-[1.1rem] rounded-t-sm bg-surface-strong"
          style={{ height: `${predictedHeight}px` }}
          title={`Stated: ${(bucket.mean_predicted * 100).toFixed(0)}%`}
        />
        <div
          className={`w-full max-w-[1.1rem] rounded-t-sm ${colorClass}`}
          style={{ height: `${observedHeight}px` }}
          title={`Observed: ${(bucket.observed_rate * 100).toFixed(0)}%`}
        />
      </div>
      <p className="meta-line text-center">
        {Math.round(bucket.lower * 100)}–{Math.round(bucket.upper * 100)}%
      </p>
      <p className="text-center text-[11px] text-ink-subtle">n={bucket.count}</p>
    </div>
  );
}

function LegendSwatch({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span aria-hidden="true" className={`inline-block h-2.5 w-2.5 rounded-sm ${className}`} />
      {label}
    </span>
  );
}

function Explainer() {
  return (
    <details className="panel p-6 sm:p-7">
      <summary className="cursor-pointer font-semibold text-ink">What is calibration, and why does it matter?</summary>
      <div className="mt-4 space-y-3 text-sm leading-6 text-ink-muted">
        <p>
          A confidence score is a claim about the world: &ldquo;of the applications we rate
          70% confident, roughly 70% should actually succeed.&rdquo; If that claim is false,
          the number is worse than useless — a user calibrates their own effort against it.
        </p>
        <p>
          <span className="font-semibold text-ink">Expected Calibration Error</span> is the
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
