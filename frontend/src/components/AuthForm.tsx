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
    <aside className="terminal-panel overflow-hidden" aria-label="Access Bharat OS">
      <div className="border-b border-terminal-faint p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <p className="font-field text-[10px] font-semibold uppercase tracking-[0.16em] terminal-glow">
            {"// fastest path — live workspace"}
          </p>
          <span className="border border-terminal-faint px-2.5 py-1 font-field text-[9px] uppercase tracking-wider terminal-muted">~3 min</span>
        </div>
        <h2 className="mt-3 font-field text-xl font-semibold uppercase terminal-glow-strong">Open ZEN Club&apos;s dossier</h2>
        <p className="mt-2 text-sm leading-6 terminal-muted">
          Creates an isolated account, profile, and document vault through the same APIs as every applicant.
        </p>
        <button
          type="button"
          onClick={launchDemo}
          disabled={waiting}
          aria-busy={demoBusy}
          className="terminal-button terminal-button-primary mt-5 w-full justify-between"
        >
          <span>{demoBusy ? "BUILDING THE FUNDING WORKSPACE…" : "LAUNCH LIVE JUDGE DEMO"}</span>
          <span aria-hidden="true">→</span>
        </button>
      </div>

      <div className="p-5 sm:p-6">
        <div className="flex items-center gap-3" aria-hidden="true">
          <span className="h-px flex-1 bg-terminal-faint" />
          <span className="font-field text-[10px] uppercase tracking-[0.14em] terminal-faint">or use your profile</span>
          <span className="h-px flex-1 bg-terminal-faint" />
        </div>

        <div className="mt-5 flex items-end justify-between gap-4">
          <div>
            <h2 className="font-field text-xl font-semibold uppercase terminal-glow">
              {mode === "register" ? "Create your account" : "Sign in"}
            </h2>
            <p className="mt-1 text-sm terminal-muted">
              {mode === "register" ? "One profile, checked consistently." : "Return to your workspace."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setMode(mode === "register" ? "login" : "register");
              setError(null);
            }}
            className="min-h-11 shrink-0 font-field text-xs font-semibold uppercase terminal-glow hover:text-terminal-bloom"
          >
            {mode === "register" ? "Sign in" : "Register"}
          </button>
        </div>

        <form onSubmit={submit} className="mt-5 space-y-4" aria-busy={busy}>
          <div>
            <label htmlFor="email" className="font-field text-xs uppercase tracking-[0.06em] terminal-muted">Email</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="terminal-field mt-2"
            />
          </div>

          <div>
            <label htmlFor="password" className="font-field text-xs uppercase tracking-[0.06em] terminal-muted">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={mode === "register" ? 12 : undefined}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-describedby={mode === "register" ? "password-hint" : undefined}
              className="terminal-field mt-2"
            />
            {mode === "register" && (
              <p id="password-hint" className="mt-2 text-xs leading-5 terminal-faint">At least 12 characters. A memorable phrase is stronger than a short complex string.</p>
            )}
          </div>

          {mode === "register" && (
            <fieldset className="border-t border-terminal-shadow pt-4">
              <legend className="text-sm font-semibold text-terminal-fg">Optional data purposes</legend>
              <p className="mt-1 text-xs leading-5 terminal-muted">
                Matching is required for the service. Everything below is independently optional and reversible.
              </p>
              <div className="mt-3 space-y-2">
                {OPTIONAL_CONSENTS.map((consent) => (
                  <label key={consent.purpose} className="flex min-h-11 cursor-pointer items-start gap-3 border border-terminal-shadow px-3 py-2.5 text-sm transition-colors duration-150 hover:border-terminal-faint">
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
                      className="mt-0.5 h-4 w-4 shrink-0 accent-terminal-fg"
                    />
                    <span>
                      <span className="block font-semibold text-terminal-fg">{consent.label}</span>
                      <span className="mt-0.5 block text-xs leading-5 terminal-faint">{consent.detail}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          <div aria-live="polite" aria-atomic="true">
            {error && <p role="alert" className="border border-terminal-alert-border bg-red-950/40 px-3 py-2 text-sm text-terminal-alert">{error}</p>}
          </div>

          <button type="submit" disabled={waiting} className="terminal-button w-full" aria-busy={busy}>
            {busy ? "WORKING…" : mode === "register" ? "CREATE ACCOUNT" : "SIGN IN"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(mode === "register" ? "login" : "register");
            setError(null);
          }}
          className="mt-2 min-h-11 font-field text-sm font-semibold uppercase terminal-glow hover:text-terminal-bloom"
        >
          {mode === "register" ? "I already have an account" : "Create an account instead"}
        </button>
      </div>
    </aside>
  );
}
