import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getAppointmentsRange } from "../../api/endpoints";
import { Button, Card, Skeleton } from "../../components/ui";
import { useBusiness } from "../../hooks/useBusiness";
import { addDays, dateOf, dayLabel, minutesOfDay, nextDays, startOfWeek, todayIn } from "../../lib/dates";
import { formatTime } from "../../lib/format";

const PX_PER_MIN = 1.1;
const BLOCK_STYLES: Record<string, string> = {
  booked: "bg-sky-100 text-sky-900 ring-sky-300",
  completed: "bg-emerald-100 text-emerald-900 ring-emerald-300",
  cancelled: "bg-slate-100 text-slate-500 ring-slate-200 line-through opacity-70",
  no_show: "bg-amber-100 text-amber-900 ring-amber-300",
};

export default function Week() {
  const business = useBusiness();
  if (!business.data) return <Skeleton className="h-96" />;
  return <WeekView tz={business.data.timezone} />;
}

function WeekView({ tz }: { tz: string }) {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(todayIn(tz)));
  const days = nextDays(weekStart, 7);
  const weekEnd = days[6];
  const appts = useQuery({
    queryKey: ["appointments", "range", weekStart, weekEnd],
    queryFn: () => getAppointmentsRange(weekStart, weekEnd),
  });

  const data = appts.data ?? [];
  const starts = data.map((a) => minutesOfDay(a.start_time, tz));
  const ends = data.map((a) => minutesOfDay(a.end_time, tz) || 24 * 60);
  const dayStart = Math.min(9 * 60, ...starts.map((m) => Math.floor(m / 60) * 60));
  const dayEnd = Math.max(20 * 60, ...ends.map((m) => Math.ceil(m / 60) * 60));
  const hours = Array.from({ length: (dayEnd - dayStart) / 60 }, (_, i) => dayStart / 60 + i);
  const height = (dayEnd - dayStart) * PX_PER_MIN;
  const a = dayLabel(weekStart);
  const b = dayLabel(weekEnd);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">
          {a.day} {a.month} – {b.day} {b.month}
        </h1>
        <div className="flex gap-2">
          <Button variant="secondary" aria-label="Previous week" onClick={() => setWeekStart(addDays(weekStart, -7))}>
            ←
          </Button>
          <Button variant="secondary" onClick={() => setWeekStart(startOfWeek(todayIn(tz)))}>
            This week
          </Button>
          <Button variant="secondary" aria-label="Next week" onClick={() => setWeekStart(addDays(weekStart, 7))}>
            →
          </Button>
        </div>
      </div>

      <Card className="overflow-x-auto p-0">
        <div className="min-w-[760px]">
          <div className="grid grid-cols-[3.5rem_repeat(7,1fr)] border-b border-slate-200 text-center text-xs font-semibold text-slate-600">
            <div />
            {days.map((d) => {
              const l = dayLabel(d);
              const isToday = d === todayIn(tz);
              return (
                <div key={d} className={`py-2 ${isToday ? "text-brand-700" : ""}`}>
                  {l.weekday} <span className="text-base">{l.day}</span>
                </div>
              );
            })}
          </div>
          <div className="grid grid-cols-[3.5rem_repeat(7,1fr)]" style={{ height }}>
            <div className="relative">
              {hours.map((h) => (
                <div
                  key={h}
                  className="absolute right-2 -translate-y-1/2 text-[11px] text-slate-400"
                  style={{ top: (h * 60 - dayStart) * PX_PER_MIN }}
                >
                  {h % 12 || 12}
                  {h < 12 ? "am" : "pm"}
                </div>
              ))}
            </div>
            {days.map((d) => (
              <div key={d} className="relative border-l border-slate-100">
                {hours.map((h) => (
                  <div
                    key={h}
                    className="absolute inset-x-0 border-t border-slate-100"
                    style={{ top: (h * 60 - dayStart) * PX_PER_MIN }}
                  />
                ))}
                {appts.isPending && <Skeleton className="absolute inset-x-1 top-10 h-16" />}
                {data
                  .filter((x) => dateOf(x.start_time, tz) === d)
                  .map((x) => {
                    const s = minutesOfDay(x.start_time, tz);
                    const e = minutesOfDay(x.end_time, tz) || 24 * 60;
                    return (
                      <div
                        key={x.id}
                        title={`${formatTime(x.start_time, tz)} ${x.customer_name} — ${x.service_name} (${x.status})`}
                        className={`absolute inset-x-1 overflow-hidden rounded-lg px-1.5 py-1 text-[11px] leading-tight ring-1 ${BLOCK_STYLES[x.status]}`}
                        style={{ top: (s - dayStart) * PX_PER_MIN, height: Math.max((e - s) * PX_PER_MIN - 2, 18) }}
                      >
                        <div className="font-semibold">{formatTime(x.start_time, tz)}</div>
                        <div className="truncate">{x.customer_name}</div>
                        <div className="truncate opacity-75">{x.service_name}</div>
                      </div>
                    );
                  })}
              </div>
            ))}
          </div>
        </div>
      </Card>
      <div className="flex flex-wrap gap-3 text-xs text-slate-600">
        {Object.entries(BLOCK_STYLES).map(([k, cls]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className={`h-3 w-3 rounded ring-1 ${cls}`} /> {k === "no_show" ? "No-show" : k[0].toUpperCase() + k.slice(1)}
          </span>
        ))}
      </div>
    </div>
  );
}
