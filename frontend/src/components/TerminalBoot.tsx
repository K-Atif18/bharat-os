"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Types out a sequence of lines, terminal-boot style, then calls onDone.
 * Every line here is a real, checkable product fact — never an invented
 * metric — matching the same discipline the rest of this product applies
 * to sourced claims.
 */
export interface BootLine {
  text: string;
  /** Rendered right-aligned once the line finishes, e.g. "OK". */
  status?: string;
}

const CHAR_INTERVAL_MS = 14;
const LINE_PAUSE_MS = 220;

export function TerminalBoot({
  lines,
  onDone,
  skipTyping = false,
}: {
  lines: BootLine[];
  onDone?: () => void;
  /** Renders every line immediately, no per-character typing delay. */
  skipTyping?: boolean;
}) {
  const [lineIndex, setLineIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [finished, setFinished] = useState(false);
  const reducedMotion = useRef(false);

  useEffect(() => {
    reducedMotion.current =
      (typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches) ||
      skipTyping;

    if (reducedMotion.current) {
      setLineIndex(lines.length);
      setFinished(true);
      onDone?.();
    }
    // onDone and skipTyping are intentionally not dependencies — this
    // should only run once, when the boot sequence starts or completes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (reducedMotion.current || finished) return;
    if (lineIndex >= lines.length) {
      setFinished(true);
      onDone?.();
      return;
    }

    const current = lines[lineIndex];
    if (!current) {
      setFinished(true);
      onDone?.();
      return;
    }

    if (charIndex < current.text.length) {
      const timer = setTimeout(() => setCharIndex((c) => c + 1), CHAR_INTERVAL_MS);
      return () => clearTimeout(timer);
    }

    const timer = setTimeout(() => {
      setLineIndex((i) => i + 1);
      setCharIndex(0);
    }, LINE_PAUSE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lineIndex, charIndex, finished]);

  const completedLines = reducedMotion.current ? lines : lines.slice(0, lineIndex);
  const typingLine = !reducedMotion.current && lineIndex < lines.length ? lines[lineIndex] : null;

  return (
    <div aria-live="polite">
      {completedLines.map((line, index) => (
        <p key={index} className="terminal-row">
          <span className="terminal-glow">&gt; {line.text}</span>
          {line.status && <span className="terminal-muted">{line.status}</span>}
        </p>
      ))}
      {typingLine && (
        <p className="terminal-row">
          <span className="terminal-glow">
            &gt; {typingLine.text.slice(0, charIndex)}
            <span className="terminal-cursor" aria-hidden="true" />
          </span>
        </p>
      )}
    </div>
  );
}
