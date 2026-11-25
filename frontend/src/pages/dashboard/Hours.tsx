import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiError } from "../../api/client";
import { getHours, putHours } from "../../api/endpoints";
import type { WorkingHour } from "../../api/types";
import { useToast } from "../../components/Toast";
import { Button, Card, Skeleton } from "../../components/ui";
import { WEEKDAYS } from "../../lib/dates";
import { addBreak, fromWeek, toWeek, validateWeek, type Week } from "../../lib/hours";

export default function Hours() {
  const hours = useQuery({ queryKey: ["hours"], queryFn: getHours });
  if (hours.isPending) return <Skeleton className="h-96" />;
  if (hours.isError) return <p className="text-red-600">{apiError(hours.error).message}</p>;
  return <HoursForm initial={hours.data} />;
}

export function HoursForm({ initial }: { initial: WorkingHour[] }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [week, setWeek] = useState<Week>(() => toWeek(initial));
  const [errors, setErrors] = useState<Record<number, string>>({});

  const save = useMutation({
    mutationFn: () => putHours(fromWeek(week)),
    onSuccess: (rows) => {
      qc.setQueryData(["hours"], rows);
      toast("Working hours saved", "success");
    },
    onError: (e) => toast(apiError(e).message, "error"),
  });

  function update(i: number, fn: (d: Week[number]) => Week[number]) {
    setWeek((w) => w.map((d, k) => (k === i ? fn(d) : d)));
  }

  function onSave() {
    const errs = validateWeek(week);
    setErrors(errs);
    if (Object.keys(errs).length === 0) save.mutate();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Working hours</h1>
        <Button onClick={onSave} disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save hours"}
        </Button>
      </div>
      <Card className="divide-y divide-slate-100 p-0">
        {week.map((d, i) => (
          <div key={WEEKDAYS[i]} className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start">
            <div className="flex w-40 shrink-0 items-center justify-between sm:block">
              <p className="font-semibold">{WEEKDAYS[i]}</p>
              <label className="flex items-center gap-2 text-sm text-slate-600 sm:mt-1">
                <input
                  type="checkbox"
                  className="h-5 w-5 accent-brand-700"
                  checked={d.closed}
                  aria-label={`${WEEKDAYS[i]} closed`}
                  onChange={(e) =>
                    update(i, (x) => ({
                      closed: e.target.checked,
                      windows: !e.target.checked && x.windows.length === 0 ? [{ open: "10:00", close: "18:00" }] : x.windows,
                    }))
                  }
                />
                Closed
              </label>
            </div>
            {!d.closed && (
              <div className="flex-1 space-y-2">
                {d.windows.map((w, k) => (
                  <div key={k} className="flex items-center gap-2">
                    <input
                      type="time"
                      aria-label={`${WEEKDAYS[i]} window ${k + 1} opens`}
                      value={w.open}
                      onChange={(e) =>
                        update(i, (x) => ({ ...x, windows: x.windows.map((y, j) => (j === k ? { ...y, open: e.target.value } : y)) }))
                      }
                      className="min-h-11 rounded-xl bg-white px-3 ring-1 ring-slate-300"
                    />
                    <span className="text-slate-400">to</span>
                    <input
                      type="time"
                      aria-label={`${WEEKDAYS[i]} window ${k + 1} closes`}
                      value={w.close}
                      onChange={(e) =>
                        update(i, (x) => ({ ...x, windows: x.windows.map((y, j) => (j === k ? { ...y, close: e.target.value } : y)) }))
                      }
                      className="min-h-11 rounded-xl bg-white px-3 ring-1 ring-slate-300"
                    />
                    {d.windows.length > 1 && (
                      <button
                        type="button"
                        aria-label="Remove window"
                        onClick={() => update(i, (x) => ({ ...x, windows: x.windows.filter((_, j) => j !== k) }))}
                        className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
                <button type="button" onClick={() => update(i, addBreak)} className="text-sm font-medium text-brand-700">
                  + Add break
                </button>
                {errors[i] && (
                  <p role="alert" className="text-sm text-red-600">
                    {errors[i]}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </Card>
    </div>
  );
}
