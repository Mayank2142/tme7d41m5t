export const number = (value: number | null | undefined, digits = 0) =>
  value == null
    ? "—"
    : new Intl.NumberFormat("en-GB", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(value);
export const signed = (value: number | null | undefined, digits = 0) =>
  value == null ? "—" : `${value > 0 ? "+" : ""}${number(value, digits)}`;
export function dateLabel(value: string, year = false) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    ...(year ? { year: "numeric" } : {}),
    timeZone: "Europe/London",
  }).format(new Date(`${value}T12:00:00Z`));
}
export function timeLabel(value: string | null, withDate = false) {
  return value
    ? new Intl.DateTimeFormat("en-GB", {
        ...(withDate ? { day: "numeric", month: "short" } : {}),
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
        timeZone: "Europe/London",
      }).format(new Date(value))
    : "—";
}
export function ageLabel(seconds: number | null) {
  if (seconds === null) return "—";
  const minutes = Math.floor(seconds / 60);
  return minutes < 60 ? `${minutes}m` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
const REASONS: Record<string, string> = {
  NO_PRE_CUTOFF_PUBLICATION: "No publication by cutoff",
  NO_ACTUAL_PUBLICATION: "No reported actual",
  NULL_GENERATION: "Source value is null",
  NEGATIVE_WIND_GENERATION: "Invalid negative wind value",
  CONFLICTING_SOURCE_KEY: "Conflicting latest source records",
  UNEXPECTED_TARGET_RESOLUTION: "Unexpected source resolution",
  SETTLEMENT_METADATA_MISMATCH: "Settlement metadata mismatch",
  NO_VALID_PAIRS: "No valid comparison pairs",
};
export const reasonLabel = (reason: string | null) =>
  reason ? (REASONS[reason] ?? reason.replaceAll("_", " ").toLowerCase()) : "Valid";
