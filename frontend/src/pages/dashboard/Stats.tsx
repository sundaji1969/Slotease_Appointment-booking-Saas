import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { apiError } from "../../api/client";
import { getStats } from "../../api/endpoints";
import { Card, Skeleton } from "../../components/ui";
import { useBusiness } from "../../hooks/useBusiness";
import { todayIn } from "../../lib/dates";
import { formatINR, formatPercent } from "../../lib/format";

export default function Stats() {
  const business = useBusiness();
  const tz = business.data?.timezone ?? "Asia/Kolkata";
  const [month, setMonth] = useState(() => todayIn(tz).slice(0, 7));
  const stats = useQuery({ queryKey: ["stats", month], queryFn: () => getStats(month) });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Stats</h1>
        <input
          type="month"
          aria-label="Month"
          value={month}
          onChange={(e) => e.target.value && setMonth(e.target.value)}
          className="min-h-11 rounded-xl bg-white px-3 ring-1 ring-slate-300"
        />
      </div>
      {stats.isPending ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : stats.isError ? (
        <p className="text-red-600">{apiError(stats.error).message}</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Bookings" value={String(stats.data.total)} sub={`${stats.data.completed} completed`} />
            <Stat
              label="No-show rate"
              value={formatPercent(stats.data.no_show_rate)}
              sub={`${stats.data.no_show} no-show${stats.data.no_show === 1 ? "" : "s"}`}
              tone={stats.data.no_show_rate > 0.15 ? "warn" : undefined}
            />
            <Stat label="Revenue estimate" value={formatINR(stats.data.revenue_estimate)} sub="completed × price" />
            <Stat label="Busiest day" value={stats.data.busiest_weekday ?? "—"} sub="by bookings" />
          </div>
          {stats.data.cancelled > 0 && (
            <p className="text-sm text-slate-500">{stats.data.cancelled} cancelled booking(s) not counted above.</p>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, sub, tone }: { label: string; value: string; sub: string; tone?: "warn" }) {
  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${tone === "warn" ? "text-amber-600" : "text-slate-900"}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-500">{sub}</p>
    </Card>
  );
}
