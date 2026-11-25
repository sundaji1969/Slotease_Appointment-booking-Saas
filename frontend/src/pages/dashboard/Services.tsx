import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { apiError } from "../../api/client";
import { createService, getServices, updateService } from "../../api/endpoints";
import type { Service } from "../../api/types";
import { useToast } from "../../components/Toast";
import { Button, Card, Field, Modal, Skeleton } from "../../components/ui";
import { formatINR } from "../../lib/format";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(80),
  duration_min: z.coerce.number().int("Whole minutes only").min(5, "At least 5 minutes").max(480, "At most 8 hours"),
  price: z.coerce.number().min(0, "Price can't be negative").max(10_000_000),
});
type Values = z.infer<typeof schema>;

export default function Services() {
  const qc = useQueryClient();
  const toast = useToast();
  const services = useQuery({ queryKey: ["services"], queryFn: getServices });
  const [editing, setEditing] = useState<Service | "new" | null>(null);

  const toggle = useMutation({
    mutationFn: (s: Service) => updateService(s.id, { is_active: !s.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["services"] }),
    onError: (e) => toast(apiError(e).message, "error"),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Services</h1>
        <Button onClick={() => setEditing("new")}>+ Add service</Button>
      </div>
      <Card className="p-0">
        {services.isPending ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : services.isError ? (
          <p className="p-4 text-red-600">{apiError(services.error).message}</p>
        ) : services.data.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-slate-600">Add your first service so customers can book it.</p>
            <Button className="mt-3" onClick={() => setEditing("new")}>
              Add a service
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {services.data.map((s) => (
              <li key={s.id} className={`flex flex-wrap items-center gap-3 px-4 py-3 ${s.is_active ? "" : "opacity-60"}`}>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">
                    {s.name} {!s.is_active && <span className="text-xs font-normal text-slate-500">(inactive)</span>}
                  </p>
                  <p className="text-sm text-slate-500">
                    {s.duration_min} min · {formatINR(s.price)}
                  </p>
                </div>
                <Button variant="ghost" onClick={() => setEditing(s)}>
                  Edit
                </Button>
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-brand-700"
                    checked={s.is_active}
                    onChange={() => toggle.mutate(s)}
                  />
                  Active
                </label>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {editing && <ServiceModal service={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function ServiceModal({ service, onClose }: { service: Service | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.input<typeof schema>, unknown, Values>({
    resolver: zodResolver(schema),
    defaultValues: service
      ? { name: service.name, duration_min: service.duration_min, price: service.price }
      : { name: "", duration_min: 30, price: 0 },
  });
  const save = useMutation({
    mutationFn: (v: Values) => (service ? updateService(service.id, v) : createService(v)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["services"] });
      onClose();
    },
    onError: (e) => setError(apiError(e).message),
  });
  const errs = form.formState.errors;

  return (
    <Modal title={service ? "Edit service" : "Add service"} onClose={onClose}>
      <form noValidate onSubmit={form.handleSubmit((v) => save.mutate(v))} className="space-y-3">
        <Field label="Name" placeholder="Haircut" error={errs.name?.message} {...form.register("name")} />
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Duration (min)"
            type="number"
            inputMode="numeric"
            error={errs.duration_min?.message}
            {...form.register("duration_min")}
          />
          <Field
            label="Price (₹)"
            type="number"
            inputMode="decimal"
            step="0.01"
            error={errs.price?.message}
            {...form.register("price")}
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
