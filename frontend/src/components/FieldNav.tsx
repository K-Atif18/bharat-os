"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useState } from "react";

/**
 * Shared top nav for every field-system (Operate-world) page — the black/
 * white instrument-panel redesign. Mirrors AppHeader's real nav items so
 * navigation stays consistent across both visual worlds; only the visual
 * language differs. Every field-system page renders this instead of the
 * civic-paper AppHeader (see AppShell's OWN_SHELL_ROUTES exclusion).
 */
const NAV_ITEMS = [
  { href: "/dashboard", label: "DASHBOARD" },
  { href: "/applications", label: "APPLICATIONS" },
  { href: "/deadlines", label: "DEADLINES" },
  { href: "/vault", label: "VAULT" },
  { href: "/calibration", label: "CALIBRATION" },
  { href: "/onboarding", label: "PROFILE" },
  { href: "/settings", label: "PRIVACY" },
];

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none">
      {open ? (
        <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      ) : (
        <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      )}
    </svg>
  );
}

function NavLinks({ pathname, mobile = false }: { pathname: string; mobile?: boolean }) {
  return NAV_ITEMS.map((item) => {
    const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={active ? "page" : undefined}
        className={
          mobile
            ? `field-nav-key flex min-h-11 items-center border-l-2 px-4 ${active ? "border-field-fg" : "border-transparent"}`
            : "field-nav-key"
        }
      >
        {item.label}
      </Link>
    );
  });
}

export function FieldNav({
  /** Breadcrumb-style label rendered on the right, e.g. a scheme name. */
  trail,
}: {
  trail?: string;
}) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileNavId = useId();

  useEffect(() => setMobileOpen(false), [pathname]);

  return (
    <>
      <nav className="field-nav" aria-label="Primary navigation">
        <Link href="/dashboard" className="font-field text-sm font-semibold uppercase tracking-[0.1em] text-field-fg">
          BHARAT_OS
        </Link>

        <div className="hidden items-center gap-6 sm:flex">
          <NavLinks pathname={pathname} />
        </div>

        {trail && (
          <span className="hidden font-field text-[11px] uppercase tracking-[0.14em] text-field-fg-muted sm:inline">
            {trail}
          </span>
        )}

        <button
          type="button"
          className="field-button h-11 w-11 px-0 sm:hidden"
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileOpen}
          aria-controls={mobileNavId}
          onClick={() => setMobileOpen((open) => !open)}
        >
          <MenuIcon open={mobileOpen} />
        </button>
      </nav>

      {mobileOpen && (
        <nav id={mobileNavId} aria-label="Mobile navigation" className="border-b border-field-rule bg-field-bg-raised sm:hidden">
          <div className="grid gap-1 py-2">
            <NavLinks pathname={pathname} mobile />
          </div>
        </nav>
      )}
    </>
  );
}
