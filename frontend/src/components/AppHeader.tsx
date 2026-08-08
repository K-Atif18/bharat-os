"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useState } from "react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/calibration", label: "Calibration" },
  { href: "/onboarding", label: "Profile" },
  { href: "/settings", label: "Privacy & data" },
];

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none">
      {open ? (
        <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      ) : (
        <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
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
            ? `flex min-h-11 items-center border-l-2 px-4 text-sm font-semibold ${active ? "border-brand bg-brand-subtle text-brand" : "border-transparent text-ink-muted hover:bg-surface-sunken hover:text-ink"}`
            : `inline-flex min-h-11 items-center border-b-2 px-1 text-sm font-semibold transition-[border-color,color] duration-150 ${active ? "border-brand text-brand" : "border-transparent text-ink-muted hover:border-surface-strong hover:text-ink"}`
        }
      >
        {item.label}
      </Link>
    );
  });
}

export function AppHeader() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileNavId = useId();
  const onLanding = pathname === "/";

  useEffect(() => setMobileOpen(false), [pathname]);

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-surface/95 shadow-[0_1px_0_rgb(23_34_51/0.03)] backdrop-blur-sm">
      <div className="page-shell flex min-h-[72px] items-center justify-between gap-4">
        <Link href="/" className="group flex min-h-11 items-center gap-3" aria-label="Bharat OS home">
          <span className="relative grid h-10 w-10 place-items-center overflow-hidden rounded-lg bg-civic-navy font-display text-lg font-semibold text-white shadow-sm transition-transform duration-150 group-hover:-translate-y-0.5">
            B
            <span aria-hidden="true" className="absolute inset-x-0 bottom-0 grid h-1 grid-cols-2">
              <span className="bg-civic-saffron" />
              <span className="bg-civic-green" />
            </span>
          </span>
          <span>
            <span className="block font-display text-lg font-semibold leading-tight tracking-[-0.02em] text-ink">Bharat OS</span>
            <span className="block font-mono text-[9px] uppercase tracking-[0.14em] text-ink-subtle">Evidence to execution</span>
          </span>
        </Link>

        {!onLanding && (
          <>
            <nav aria-label="Primary navigation" className="hidden items-center gap-6 sm:flex">
              <NavLinks pathname={pathname} />
            </nav>
            <button
              type="button"
              className="button-secondary h-11 w-11 px-0 sm:hidden"
              aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileOpen}
              aria-controls={mobileNavId}
              onClick={() => setMobileOpen((open) => !open)}
            >
              <MenuIcon open={mobileOpen} />
            </button>
          </>
        )}

        {onLanding && (
          <span className="hidden rounded-full border border-met-border bg-met-bg px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-met-fg sm:inline-flex">
            Live working MVP
          </span>
        )}
      </div>

      {!onLanding && mobileOpen && (
        <nav id={mobileNavId} aria-label="Mobile navigation" className="border-t border-surface-border bg-surface px-4 py-3 sm:hidden">
          <div className="mx-auto grid max-w-[1180px] gap-1">
            <NavLinks pathname={pathname} mobile />
          </div>
        </nav>
      )}
    </header>
  );
}
