import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiError } from "../../api/client";
import { getAppointmentsForDay, getToday, updateAppointmentStatus } from "../../api/endpoints";
import type { Appointment, AppointmentStatus } from "../../api/types";
import { ShareCard } from "../../components/ShareCard";
import { useToast } from "../../components/Toast";
import { Button, Card, Skeleton, StatusBadge } from "../../components/ui";
import { useBusiness } from "../../hooks/useBusiness";
import { addDays, dayLabel, todayIn } from "../../lib/dates";
import { formatINR, formatTime } from "../../lib/format";

export default function Today() {
  const business = useBusiness();
  if (!business.data) return <Skeleton className="h-40" />;
  return <TodayView tz={business.data.timezone} slug={business.data.slug} name={business.data.name} />;
}

function TodayView({ tz, slug, name }: { tz: string; slug: string; name: string }) {
  const today = todayIn(tz);
  const [date, setDate] = useState(today);
  const qc = useQueryClient();
  const toast = useToast();
  const apptKey = ["appointments", "day", date];

  const summary = useQuery({ queryKey: ["today", date], queryFn: () => getToday(date) });
  const appts = useQuery({ queryKey: apptKey, queryFn: () => getAppointmentsForDay(date) });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AppointmentStatus }) => updateAppointmentStatus(id, status),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: apptKey });
      const previous = qc.getQueryData<Appointment[]>(apptKey);
      qc.setQueryData<Appointment[]>(apptKey, (xs) => xs?.map((a) => (a.id === id ? { ...a, status } : a)));
      return { previous };
    },
    onError: (err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(apptKey, ctx.previous);
      toast(apiError(err).message, "error");
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["appointments"] });
      qc.invalidateQueries({ queryKey: ["today"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const l = dayLabel(date);
  const isToday = date === today;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight sm:text-2xl">
            <span>{name.toUpperCase()}</span>
            <span className="text-slate-400"> | </span>
            {isToday ? "Today, " : ""}
            {l.weekday} {l.day} {l.month}
          </h1>
          {summary.data ? (
            <p className="mt-1 text-slate-600" data-testid="day-summary">
              {summary.data.count} booking{summary.data.count === 1 ? "" : "s"} · {summary.data.no_shows} no-show
              {summary.data.no_shows === 1 ? "" : "s"} · Est. {formatINR(summary.data.revenue_estimate)}
            </p>
          ) : (
            <Skeleton className="mt-2 h-5 w-64" />
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" aria-label="Previous day" onClick={() => setDate(addDays(date, -1))}>
            ←
          </Button>
          <input
            type="date"
            aria-label="Choose date"
            value={date}
            onChange={(e) => e.target.value && setDate(e.target.value)}
            className="min-h-11 rounded-xl bg-white px-3 ring-1 ring-slate-300"
          />
          <Button variant="secondary" aria-label="Next day" onClick={() => setDate(addDays(date, 1))}>
            →
          </Button>
          {!isToday && (
            <Button variant="ghost" onClick={() => setDate(today)}>
              Today
            </Button>
          )}
        </div>
      </div>

      <ShareCard slug={slug} businessName={name} />

      <Card className="overflow-hidden p-0">
        {appts.isPending ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : appts.isError ? (
          <p className="p-4 text-red-600">{apiError(appts.error).message}</p>
        ) : appts.data.length === 0 ? (
          <p className="p-8 text-center text-slate-500">No bookings for this day yet. Share your link to get some!</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Service</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {appts.data.map((a) => (
                  <tr key={a.id} data-testid={`appt-${a.booking_id}`}>
                    <td className="whitespace-nowrap px-4 py-3 font-semibold">{formatTime(a.start_time, tz)}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium">{a.customer_name}</div>
                      <a href={a.whatsapp_url} target="_blank" rel="noreferrer" className="text-xs text-brand-700">
                        {a.customer_phone} · WhatsApp
                      </a>
                    </td>
                    <td className="px-4 py-3">
                      <div>{a.service_name}</div>
                      <div className="text-xs text-slate-500">{formatINR(a.price)}</div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="px-4 py-3">
                      {a.status === "booked" && (
                        <div className="flex flex-wrap justify-end gap-1.5">
                          <Button
                            className="px-3 py-1.5"
                            onClick={() => mutation.mutate({ id: a.id, status: "completed" })}
                          >
                            Complete
                          </Button>
                          <Button
                            variant="secondary"
                            className="px-3 py-1.5"
                            onClick={() => mutation.mutate({ id: a.id, status: "no_show" })}
                          >
                            No-show
                          </Button>
                          <Button
                            variant="danger"
                            className="px-3 py-1.5"
                            onClick={() => mutation.mutate({ id: a.id, status: "cancelled" })}
                          >
                            Cancel
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
