"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { AppHeader } from "@/components/AppHeader";

// Pages that own their full viewport — header, main and footer included —
// and must never be sandwiched inside the incumbent civic-paper shell
// below. Covers both redesigned visual worlds: the field-system Operate
// pages and the terminal-system landing page. usePathname is the least
// disruptive way to make this split without moving every existing route
// into a Next.js route group.
const OWN_SHELL_ROUTES = [
  /^\/schemes\/[^/]+\/workspace$/,
  /^\/schemes\/[^/]+$/,
  /^\/$/,
  /^\/dashboard$/,
  /^\/calibration$/,
  /^\/onboarding$/,
  /^\/settings$/,
  /^\/review-queue$/,
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const ownsShell = OWN_SHELL_ROUTES.some((pattern) => pattern.test(pathname ?? ""));

  if (ownsShell) {
    return <>{children}</>;
  }

  return (
    <>
      <a
        href="#main-content"
        className="fixed left-4 top-3 z-[100] -translate-y-20 rounded-lg bg-civic-navy px-4 py-2 text-sm font-semibold text-white shadow-lift transition-transform duration-150 focus:translate-y-0"
      >
        Skip to main content
      </a>
      <div className="flex min-h-screen flex-col">
        <AppHeader />

        <main id="main-content" tabIndex={-1} className="page-shell flex-1 py-8 outline-none sm:py-12">
          {children}
        </main>

        <footer className="mt-8 border-t border-surface-border bg-civic-navy text-ink-inverse">
          <div className="page-shell grid gap-5 py-7 sm:grid-cols-[1fr_auto] sm:items-end">
            <div className="max-w-3xl">
              <p className="font-display text-lg font-semibold">Evidence, not a guarantee.</p>
              <p className="mt-2 text-xs leading-5 text-slate-300 sm:text-sm">
                Bharat OS is advisory. Scheme terms change; confirm every criterion against its
                linked official source. Every application remains under human review and control.
              </p>
            </div>
            <nav aria-label="Footer navigation" className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-300">
              <Link href="/dashboard" className="min-h-11 content-center hover:text-white">Dashboard</Link>
              <Link href="/onboarding" className="min-h-11 content-center hover:text-white">Profile</Link>
              <Link href="/settings" className="min-h-11 content-center hover:text-white">Privacy &amp; data</Link>
            </nav>
          </div>
        </footer>
      </div>
    </>
  );
}
