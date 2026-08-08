/**
 * Formatting helpers shared across the interface.
 *
 * Indian numbering is used throughout because "₹1.2 crore" is what a user
 * recognises; "₹12,000,000" makes them count digits.
 */

/** Format rupees using lakh and crore, which is how the amounts are published. */
export function formatRupees(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "Not specified";
  if (amount === 0) return "No direct monetary benefit";
  // parseFloat drops trailing zeros, so 1.5 crore does not render as "1.50 crore".
  if (amount >= 10_000_000) {
    return `₹${parseFloat((amount / 10_000_000).toFixed(2))} crore`;
  }
  if (amount >= 100_000) {
    return `₹${parseFloat((amount / 100_000).toFixed(1))} lakh`;
  }
  return `₹${amount.toLocaleString("en-IN")}`;
}

/**
 * Render a confidence value as a percentage.
 *
 * Deliberately never paired with the word "eligible". The number describes how
 * many requirements have been confirmed, not a probability of approval.
 */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/** Turn a profile field name into something a person would recognise. */
export function humaniseField(field: string): string {
  const labels: Record<string, string> = {
    annual_turnover_inr: "annual turnover",
    employee_count: "employee count",
    entity_age_years: "incorporation date",
    is_woman_led: "whether the business is woman-led",
    social_category: "social category",
    registrations: "registrations held",
    state: "state",
    district: "district",
    sector: "sector",
    stage: "stage",
  };
  return labels[field] ?? field.replace(/_/g, " ");
}

/** Days-since-verified rendered as a staleness note, or null if fresh. */
export function stalenessNote(days: number, thresholdDays = 90): string | null {
  if (days < thresholdDays) return null;
  if (days > 365) return `Last verified over a year ago`;
  return `Last verified ${days} days ago`;
}

export function formatDeadline(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  const days = Math.ceil((date.getTime() - Date.now()) / 86_400_000);
  const formatted = date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  if (days < 0) return `Closed ${formatted}`;
  if (days === 0) return `Closes today`;
  if (days === 1) return `Closes tomorrow (${formatted})`;
  return `${days} days left (${formatted})`;
}
