/** Score bands from design §2.1. Viewers can't call /meta/filters, so the labels live here too. */
export type BandKey = "poor" | "fair" | "good" | "very_good" | "excellent";

export const SCORE_BANDS: { key: BandKey; label: string; min: number; max: number }[] = [
  { key: "poor", label: "Poor", min: 300, max: 579 },
  { key: "fair", label: "Fair", min: 580, max: 669 },
  { key: "good", label: "Good", min: 670, max: 739 },
  { key: "very_good", label: "Very good", min: 740, max: 799 },
  { key: "excellent", label: "Excellent", min: 800, max: 850 },
];

export function bandFor(score: number) {
  return SCORE_BANDS.find((b) => score >= b.min && score <= b.max) ?? SCORE_BANDS[0];
}

/** Text colour classes per band (semantic tokens). */
export const BAND_STYLE: Record<BandKey, string> = {
  poor: "bg-danger/10 text-danger",
  fair: "bg-warning/10 text-warning",
  good: "bg-info/10 text-info",
  very_good: "bg-success/10 text-success",
  excellent: "bg-success/15 text-success",
};
