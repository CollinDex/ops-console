const TZ = "Africa/Lagos";

const dateFmt = new Intl.DateTimeFormat("en-NG", { timeZone: TZ, dateStyle: "medium" });
const dateTimeFmt = new Intl.DateTimeFormat("en-NG", {
  timeZone: TZ,
  dateStyle: "medium",
  timeStyle: "short",
});
const numberFmt = new Intl.NumberFormat("en-NG");
const relFmt = new Intl.RelativeTimeFormat("en", { numeric: "always" });

export function formatDate(value: string | Date): string {
  return dateFmt.format(new Date(value));
}

export function formatDateTime(value: string | Date): string {
  return dateTimeFmt.format(new Date(value));
}

export function formatNumber(value: number): string {
  return numberFmt.format(value);
}

/** "3 min ago", "2 days ago". Anything under a minute reads "just now". */
export function formatRelative(value: string | Date, now: Date = new Date()): string {
  const seconds = Math.round((new Date(value).getTime() - now.getTime()) / 1000);
  const abs = Math.abs(seconds);
  if (abs < 60) return "just now";
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (abs >= size) {
      const text = relFmt.format(Math.round(seconds / size), unit);
      return text.replace("minutes", "min").replace("minute", "min");
    }
  }
  return "just now";
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0];
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

const shortDateFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: "UTC",
  day: "numeric",
  month: "short",
});

/** "17 Aug" from a date-only string such as "2026-08-17" (no timezone shift). */
export function formatShortDate(dateOnly: string): string {
  return shortDateFmt.format(new Date(`${dateOnly}T00:00:00Z`));
}
