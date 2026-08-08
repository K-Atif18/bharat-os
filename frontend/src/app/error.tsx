"use client";

export default function ErrorBoundary({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <section role="alert" className="panel mx-auto max-w-2xl overflow-hidden">
      <div className="border-l-4 border-unmet-fg p-6 sm:p-8">
        <p className="eyebrow text-unmet-fg">Bharat OS could not finish this step</p>
        <h1 className="page-title mt-3">Your work is still under your control</h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-ink-muted sm:text-base">
          A temporary application error interrupted this screen. No application was submitted.
          Try the step again; if it continues, return to the dashboard and verify that the API is running.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button type="button" onClick={reset} className="button-primary">Try again</button>
          <a href="/dashboard" className="button-secondary">Return to dashboard</a>
        </div>
      </div>
    </section>
  );
}
