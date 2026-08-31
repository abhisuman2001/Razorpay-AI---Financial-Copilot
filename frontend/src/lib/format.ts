export const formatINR = (value: number, compact = false) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: compact ? 0 : 0,
    notation: compact ? "compact" : "standard",
  }).format(value);

export const formatPaiseINR = (value: number, compact = false) => formatINR(value / 100, compact);

export const formatDate = (value: string) =>
  new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(
    new Date(`${value}T00:00:00`),
  );