"use client";

import { useMemo } from "react";

/**
 * Persistent falling-digit background for the terminal landing page.
 * Pure CSS animation (matrix-rain-fall in globals.css) — no canvas, no
 * per-frame JS — each column is a tall string of random digits animated
 * with a randomized duration/delay so columns don't sync up.
 * aria-hidden: purely decorative, never carries content.
 */
const CHARSET = "0123456789";

function randomColumn(length: number): string {
  let out = "";
  for (let i = 0; i < length; i += 1) {
    out += CHARSET[Math.floor(Math.random() * CHARSET.length)] + "\n";
  }
  return out;
}

export function MatrixRain({ columns = 32 }: { columns?: number }) {
  const cols = useMemo(
    () =>
      Array.from({ length: columns }, (_, i) => ({
        left: `${(i / columns) * 100}%`,
        duration: 7 + Math.random() * 10,
        delay: Math.random() * -14,
        text: randomColumn(40),
      })),
    [columns],
  );

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden opacity-[0.14]" aria-hidden="true">
      {cols.map((col, i) => (
        <span
          key={i}
          className="matrix-rain-column"
          style={{
            left: col.left,
            animationDuration: `${col.duration}s`,
            animationDelay: `${col.delay}s`,
          }}
        >
          {col.text}
        </span>
      ))}
    </div>
  );
}
