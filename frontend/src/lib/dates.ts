/** Calendar-date helpers on plain "YYYY-MM-DD" strings (no timezone drift). */

export function todayIn(tz: string, now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

function toUTC(ymd: string): Date {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12));
}

function fromUTC(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function addDays(ymd: string, n: number): string {
  const d = toUTC(ymd);
  d.setUTCDate(d.getUTCDate() + n);
  return fromUTC(d);
}

/** 0 = Monday … 6 = Sunday (matches the backend's weekday numbering). */
export function weekdayIndex(ymd: string): number {
  return (toUTC(ymd).getUTCDay() + 6) % 7;
}

export function startOfWeek(ymd: string): string {
  return addDays(ymd, -weekdayIndex(ymd));
}

export function nextDays(fromYmd: string, count: number): string[] {
  return Array.from({ length: count }, (_, i) => addDays(fromYmd, i));
}

export function dayLabel(ymd: string): { weekday: string; day: number; month: string } {
  const d = toUTC(ymd);
  return {
    weekday: d.toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" }),
    day: d.getUTCDate(),
    month: d.toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" }),
  };
}

export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/** Minutes since local midnight for an ISO timestamp, in the business timezone. */
export function minutesOfDay(iso: string, tz: string): number {
  const p = new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
    .formatToParts(new Date(iso))
    .reduce<Record<string, string>>((acc, x) => ({ ...acc, [x.type]: x.value }), {});
  return Number(p.hour) * 60 + Number(p.minute);
}

/** Calendar date of an ISO timestamp in the business timezone. */
export function dateOf(iso: string, tz: string): string {
  return todayIn(tz, new Date(iso));
}
