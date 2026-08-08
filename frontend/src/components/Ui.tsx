import type { ReactNode } from "react";

export function PageIntro({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-5 border-b border-surface-strong pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="page-title mt-2">{title}</h1>
        {description && <div className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted sm:text-base">{description}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  trailing,
  id,
}: {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  trailing?: ReactNode;
  id?: string;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 id={id} className="section-title mt-1">{title}</h2>
        {description && <div className="mt-2 text-sm leading-6 text-ink-muted">{description}</div>}
      </div>
      {trailing && <div className="shrink-0">{trailing}</div>}
    </div>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div role="status" aria-live="polite" className="panel mx-auto max-w-3xl p-6 sm:p-8">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="space-y-4">
        <div className="loading-line h-3 w-28" />
        <div className="loading-line h-9 w-3/4" />
        <div className="loading-line h-4 w-full" />
        <div className="loading-line h-4 w-5/6" />
      </div>
    </div>
  );
}

export function StatusDot({ tone }: { tone: "met" | "unmet" | "unverified" | "info" }) {
  const colors = {
    met: "bg-met-fg",
    unmet: "bg-unmet-fg",
    unverified: "bg-unverified-fg",
    info: "bg-info-fg",
  };
  return <span aria-hidden="true" className={`inline-block h-2 w-2 shrink-0 rounded-full ${colors[tone]}`} />;
}

/* --- Field-system equivalents ------------------------------------------
 * Same components, restyled for the black/white instrument-panel world.
 * Kept separate from the civic-paper versions above rather than adding a
 * variant prop — the two worlds' pages never render the same component
 * instance, so a prop would only add an unused branch to every call site.
 */

export function FieldSectionHeading({
  index,
  title,
  description,
  trailing,
  id,
}: {
  index?: string;
  title: string;
  description?: ReactNode;
  trailing?: ReactNode;
  id?: string;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        <div className="field-section-label border-none pb-0">
          {index && <span className="field-index">{index}</span>}
          <span id={id}>{title}</span>
        </div>
        {description && <div className="mt-2 text-sm leading-6 text-field-fg-muted">{description}</div>}
      </div>
      {trailing && <div className="shrink-0">{trailing}</div>}
    </div>
  );
}

export function FieldLoadingState({ label }: { label: string }) {
  return (
    <div role="status" aria-live="polite" className="field-panel mx-auto max-w-3xl p-6 sm:p-8">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="space-y-4">
        <div className="h-3 w-28 animate-pulse bg-field-rule" />
        <div className="h-9 w-3/4 animate-pulse bg-field-rule" />
        <div className="h-4 w-full animate-pulse bg-field-rule" />
        <div className="h-4 w-5/6 animate-pulse bg-field-rule" />
      </div>
    </div>
  );
}

export function FieldPageIntro({
  index,
  title,
  description,
  actions,
}: {
  index?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-5 border-b border-field-rule pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        <div className="field-section-label border-none pb-0">
          {index && <span className="field-index">{index}</span>}
          <span>{title}</span>
        </div>
        {description && <div className="mt-3 max-w-2xl text-sm leading-6 text-field-fg-muted sm:text-base">{description}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
