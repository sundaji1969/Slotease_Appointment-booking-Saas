const inrWhole = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const inrExact = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

export function formatINR(amount: number): string {
  return Number.isInteger(amount) ? inrWhole.format(amount) : inrExact.format(amount);
}

function parts(iso: string | Date, tz: string, opts: Intl.DateTimeFormatOptions): Record<string, string> {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  const out: Record<string, string> = {};
  for (const p of new Intl.DateTimeFormat("en-GB", { timeZone: tz, ...opts }).formatToParts(d)) {
    out[p.type] = p.value;
  }
  return out;
}

/** "5:30 PM" in the business timezone. */
export function formatTime(iso: string, tz: string): string {
  const p = parts(iso, tz, { hour: "numeric", minute: "2-digit", hour12: true });
  return `${Number(p.hour)}:${p.minute} ${(p.dayPeriod ?? "").toUpperCase()}`;
}

/** "Sat 10 Oct" in the business timezone. */
export function formatDay(iso: string, tz: string): string {
  const p = parts(iso, tz, { weekday: "short", day: "numeric", month: "short" });
  return `${p.weekday} ${p.day} ${p.month}`;
}

/** "Sat 10 Oct, 5:30 PM" — matches the backend confirmation text. */
export function formatBookingDate(iso: string, tz: string): string {
  return `${formatDay(iso, tz)}, ${formatTime(iso, tz)}`;
}

export function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(rate === 0 ? 0 : 1)}%`;
}

export function whatsappLink(phoneE164: string, text: string): string {
  return `https://wa.me/${phoneE164.replace(/\D/g, "")}?text=${encodeURIComponent(text)}`;
}
