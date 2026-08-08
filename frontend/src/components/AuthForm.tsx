"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, login, registerAccount } from "@/lib/api";
import { provisionJudgeDemo } from "@/lib/demo";

const OPTIONAL_CONSENTS = [
  {
    purpose: "document_storage" as const,
    label: "Reusable document vault",
    detail: "Store document metadata for checklists and deadline planning.",
  },
  {
    purpose: "notifications" as const,
    label: "Deadline reminders",
    detail: "Keep permission for future reminder delivery records.",
  },
  {
    purpose: "outcome_analytics" as const,
    label: "Help improve assessments",
    detail: "Retain de-identified outcomes so future assessments can improve.",
  },
];

export function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<"register" | "login">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [optional, setOptional] = useState<string[]>(["notifications"]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);

  async function launchDemo() {
    setError(null);
    setDemoBusy(true);
    try {
      await provisionJudgeDemo();
      router.push("/dashboard");
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.detail
          : "Could not prepare the demo workspace. Check that the API is running.",
      );
    } finally {
      setDemoBusy(false);
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "register") {
        await registerAccount({
          email,
          password,
          consents: ["scheme_matching", ...optional] as never,
        });
        router.push("/onboarding");
      } else {
        await login({ email, password });
        router.push("/dashboard");
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const waiting = busy || demoBusy;

  return (
    <aside className="panel reveal overflow-hidden" aria-label="Access Bharat OS">
      <div className="bg-civic-navy p-5 text-white sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-orange-200">Fastest path · live workspace</p>
          <span className="rounded-full border border-white/20 px-2.5 py-1 font-mono text-[9px] uppercase tracking-wider text-slate-200">~3 min</span>
        </div>
        <h2 className="mt-3 font-display text-2xl font-semibold">Open ZEN Club&apos;s dossier</h2>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          Creates an isolated account, profile, and document vault through the same APIs as every applicant.
        </p>
        <button
          type="button"
          onClick={launchDemo}
          disabled={waiting}
          aria-busy={demoBusy}
          className="mt-5 inline-flex min-h-12 w-full items-center justify-between rounded-lg bg-brand px-4 py-3 text-sm font-semibold text-white shadow-sm transition-[background-color,transform,box-shadow] duration-150 hover:bg-[#b3461c] hover:shadow-md active:scale-[0.99] disabled:cursor-wait disabled:opacity-60"
        >
          <span>{demoBusy ? "Building the funding workspace…" : "Launch live judge demo"}</span>
          <span aria-hidden="true">→</span>
        </button>
      </div>

      <div className="p-5 sm:p-6">
        <div className="flex items-center gap-3" aria-hidden="true">
          <span className="h-px flex-1 bg-surface-border" />
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">or use your profile</span>
          <span className="h-px flex-1 bg-surface-border" />
        </div>

        <div className="mt-5 flex items-end justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-semibold tracking-tight">
              {mode === "register" ? "Create your account" : "Sign in"}
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              {mode === "register" ? "One profile, checked consistently." : "Return to your workspace."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setMode(mode === "register" ? "login" : "register");
              setError(null);
            }}
            className="min-h-11 shrink-0 text-xs font-semibold text-brand underline decoration-brand/30 underline-offset-4 hover:text-brand-hover"
          >
            {mode === "register" ? "Sign in" : "Register"}
          </button>
        </div>

        <form onSubmit={submit} className="mt-5 space-y-4" aria-busy={busy}>
          <div>
            <label htmlFor="email" className="field-label">Email</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="field-control"
            />
          </div>

          <div>
            <label htmlFor="password" className="field-label">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={mode === "register" ? 12 : undefined}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-describedby={mode === "register" ? "password-hint" : undefined}
              className="field-control"
            />
            {mode === "register" && (
              <p id="password-hint" className="field-hint">At least 12 characters. A memorable phrase is stronger than a short complex string.</p>
            )}
          </div>

          {mode === "register" && (
            <fieldset className="border-t border-surface-border pt-4">
              <legend className="text-sm font-semibold text-ink">Optional data purposes</legend>
              <p className="mt-1 text-xs leading-5 text-ink-muted">
                Matching is required for the service. Everything below is independently optional and reversible.
              </p>
              <div className="mt-3 space-y-2">
                {OPTIONAL_CONSENTS.map((consent) => (
                  <label key={consent.purpose} className="choice-row">
                    <input
                      type="checkbox"
                      checked={optional.includes(consent.purpose)}
                      onChange={(event) =>
                        setOptional((current) =>
                          event.target.checked
                            ? [...current, consent.purpose]
                            : current.filter((purpose) => purpose !== consent.purpose),
                        )
                      }
                    />
                    <span>
                      <span className="block font-semibold text-ink">{consent.label}</span>
                      <span className="mt-0.5 block text-xs leading-5 text-ink-subtle">{consent.detail}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          <div aria-live="polite" aria-atomic="true">
            {error && <p role="alert" className="notice border-unmet-border bg-unmet-bg text-unmet-fg">{error}</p>}
          </div>

          <button type="submit" disabled={waiting} className="button-secondary w-full" aria-busy={busy}>
            {busy ? "Working…" : mode === "register" ? "Create account" : "Sign in"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "register" ? "login" : "register");
            setError(null);
          }}
          className="mt-2 min-h-11 text-sm font-semibold text-brand hover:text-brand-hover hover:underline"
        >
          {mode === "register" ? "I already have an account" : "Create an account instead"}
        </button>
      </div>
    </aside>
  );
}
