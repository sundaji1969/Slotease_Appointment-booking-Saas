import type { WorkingHour } from "../api/types";

export type Window = { open: string; close: string };
export type DayHours = { closed: boolean; windows: Window[] };
export type Week = DayHours[]; // index 0 = Monday

const hhmm = (t: string) => t.slice(0, 5);

export function toWeek(rows: WorkingHour[]): Week {
  const week: Week = Array.from({ length: 7 }, () => ({ closed: true, windows: [] }));
  for (const r of [...rows].sort((a, b) => a.open_time.localeCompare(b.open_time))) {
    week[r.weekday].closed = false;
    week[r.weekday].windows.push({ open: hhmm(r.open_time), close: hhmm(r.close_time) });
  }
  return week;
}

export function fromWeek(week: Week): WorkingHour[] {
  return week.flatMap((d, weekday) =>
    d.closed ? [] : d.windows.map((w) => ({ weekday, open_time: w.open, close_time: w.close })),
  );
}

/** Returns an error message per weekday (index), or an empty object when valid. */
export function validateWeek(week: Week): Record<number, string> {
  const errors: Record<number, string> = {};
  week.forEach((d, i) => {
    if (d.closed) return;
    if (d.windows.length === 0) {
      errors[i] = "Add opening hours or mark the day closed";
      return;
    }
    for (const w of d.windows) {
      if (!w.open || !w.close) {
        errors[i] = "Fill in both times";
        return;
      }
      if (w.close <= w.open) {
        errors[i] = "Closing time must be after opening time";
        return;
      }
    }
    const sorted = [...d.windows].sort((a, b) => a.open.localeCompare(b.open));
    for (let k = 1; k < sorted.length; k++) {
      if (sorted[k].open < sorted[k - 1].close) {
        errors[i] = "Time windows overlap";
        return;
      }
    }
  });
  return errors;
}

/** Split the last window to create a 1-hour break in its middle (or add a new window). */
export function addBreak(day: DayHours): DayHours {
  const last = day.windows[day.windows.length - 1];
  if (!last) return { closed: false, windows: [{ open: "10:00", close: "18:00" }] };
  const toMin = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
  const toStr = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  const a = toMin(last.open);
  const b = toMin(last.close);
  if (b - a < 120) {
    return { ...day, windows: [...day.windows, { open: last.close, close: toStr(Math.min(b + 120, 23 * 60 + 59)) }] };
  }
  const mid = Math.round((a + b) / 2 / 30) * 30;
  return {
    ...day,
    windows: [...day.windows.slice(0, -1), { open: last.open, close: toStr(mid - 30) }, { open: toStr(mid + 30), close: last.close }],
  };
}
