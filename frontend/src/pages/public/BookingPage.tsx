import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { apiError } from "../../api/client";
import { createBooking, getPublicBusiness, getPublicServices, getSlots } from "../../api/endpoints";
import type { BookingResponse, PublicBusiness, PublicService } from "../../api/types";
import { AssistantPanel } from "../../components/AssistantPanel";
import { useToast } from "../../components/Toast";
import { Button, Field, Skeleton } from "../../components/ui";
import { dayLabel, nextDays, todayIn } from "../../lib/dates";
import { formatBookingDate, formatINR, formatTime, whatsappLink } from "../../lib/format";

const detailsSchema = z.object({
  name: z.string().trim().min(2, "Please enter your name (at least 2 characters)").max(60, "Name is too long"),
  phone: z
    .string()
    .trim()
    .regex(/^[6-9]\d{9}$/, "Enter a valid 10-digit mobile number"),
});
type Details = z.infer<typeof detailsSchema>;

export default function BookingPage() {
  const { slug = "" } = useParams();
  const business = useQuery({
    queryKey: ["public", slug],
    queryFn: () => getPublicBusiness(slug),
    retry: (count, err) => apiError(err).status !== 404 && count < 2,
  });

  if (business.isPending) return <PageShell><BookingSkeleton /></PageShell>;
  if (business.isError) {
    const notFound = apiError(business.error).status === 404;
    return (
      <PageShell>
        <div className="py-16 text-center">
          <p className="text-5xl" aria-hidden>🔍</p>
          <h1 className="mt-4 text-xl font-semibold">{notFound ? "Business not found" : "Something went wrong"}</h1>
          <p className="mt-2 text-slate-600">
            {notFound ? "Check the link you were sent — it may have a typo." : apiError(business.error).message}
          </p>
        </div>
      </PageShell>
    );
  }
  return <BookingFlow slug={slug} business={business.data} />;
}

function PageShell({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <div className="mx-auto min-h-dvh w-full max-w-lg bg-white sm:my-6 sm:min-h-0 sm:rounded-3xl sm:shadow-sm sm:ring-1 sm:ring-slate-200">
      {title && (
        <header className="border-b border-slate-100 px-4 pb-4 pt-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-brand-700">Book an appointment</p>
          <h1 className="mt-1 text-2xl font-bold">{title}</h1>
        </header>
      )}
      <main className="px-4 pb-32">{children}</main>
    </div>
  );
}

function BookingSkeleton() {
  return (
    <div className="space-y-4 pt-6" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="h-20" />
      <Skeleton className="h-20" />
      <Skeleton className="h-16" />
    </div>
  );
}

function SectionTitle({ step, children }: { step: number; children: React.ReactNode }) {
  return (
    <h2 className="mb-3 mt-6 flex items-center gap-2 text-base font-semibold text-slate-900">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800">
        {step}
      </span>
      {children}
    </h2>
  );
}

function BookingFlow({ slug, business }: { slug: string; business: PublicBusiness }) {
  const tz = business.timezone;
  const toast = useToast();
  const qc = useQueryClient();
  const [service, setService] = useState<PublicService | null>(null);
  const [date, setDate] = useState(() => todayIn(tz));
  const [slot, setSlot] = useState<string | null>(null);
  const [booking, setBooking] = useState<BookingResponse | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const services = useQuery({ queryKey: ["public", slug, "services"], queryFn: () => getPublicServices(slug) });
  const slotsKey = ["public", slug, "slots", service?.id, date];
  const slots = useQuery({
    queryKey: slotsKey,
    queryFn: () => getSlots(slug, service!.id, date),
    enabled: !!service,
  });

  const form = useForm<Details>({ resolver: zodResolver(detailsSchema), defaultValues: { name: "", phone: "" } });

  const mutation = useMutation({
    mutationFn: (d: Details) =>
      createBooking(slug, { service_id: service!.id, start_time: slot!, name: d.name, phone: d.phone }),
    onSuccess: (data) => {
      setBooking(data);
      qc.invalidateQueries({ queryKey: ["public", slug, "slots"] });
    },
    onError: (err) => {
      const e = apiError(err);
      if (e.status === 409) {
        toast(e.message || "This slot was just booked. Please pick another time.", "error");
        setSlot(null);
        qc.invalidateQueries({ queryKey: ["public", slug, "slots"] });
      } else {
        setFormError(e.message);
      }
    },
  });

  function onSubmit(d: Details) {
    setFormError(null);
    if (!service || !slot) {
      setFormError("Pick a service and a time first.");
      return;
    }
    mutation.mutate(d);
  }

  if (booking) {
    return (
      <PageShell>
        <Success
          booking={booking}
          business={business}
          onAgain={() => {
            setBooking(null);
            setSlot(null);
            setService(null);
          }}
        />
      </PageShell>
    );
  }

  const days = nextDays(todayIn(tz), 14);

  return (
    <PageShell title={business.name}>
      {business.assistant_enabled && (
        <AssistantPanel
          slug={slug}
          tz={tz}
          onPick={(serviceId, day, iso) => {
            const svc = services.data?.find((s) => s.id === serviceId);
            if (!svc) return;
            setService(svc);
            setDate(day);
            setSlot(iso);
            const name = document.getElementById("name");
            name?.scrollIntoView({ behavior: "smooth", block: "center" });
            name?.focus({ preventScroll: true });
          }}
        />
      )}

      {/* 1. Service */}
      <SectionTitle step={1}>Choose a service</SectionTitle>
      {services.isPending ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : services.isError ? (
        <p className="text-red-600">Couldn't load services. Pull to refresh.</p>
      ) : services.data.length === 0 ? (
        <p className="text-slate-600">This business hasn't added any services yet.</p>
      ) : (
        <div className="grid gap-2" role="radiogroup" aria-label="Services">
          {services.data.map((s) => {
            const selected = service?.id === s.id;
            return (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => {
                  setService(s);
                  setSlot(null);
                }}
                className={`flex min-h-16 items-center justify-between rounded-2xl px-4 py-3 text-left ring-1 transition ${
                  selected ? "bg-brand-50 ring-2 ring-brand-600" : "bg-white ring-slate-200 hover:ring-slate-300"
                }`}
              >
                <span>
                  <span className="block font-semibold">{s.name}</span>
                  <span className="text-sm text-slate-500">{s.duration_min} min</span>
                </span>
                <span className="font-semibold text-slate-900">{formatINR(s.price)}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* 2. Date */}
      <SectionTitle step={2}>Pick a day</SectionTitle>
      <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1" role="radiogroup" aria-label="Dates">
        {days.map((d, i) => {
          const l = dayLabel(d);
          const selected = d === date;
          return (
            <button
              key={d}
              type="button"
              role="radio"
              aria-checked={selected}
              aria-label={`${l.weekday} ${l.day} ${l.month}`}
              onClick={() => {
                setDate(d);
                setSlot(null);
              }}
              className={`flex min-h-16 w-16 shrink-0 flex-col items-center justify-center rounded-2xl ring-1 ${
                selected ? "bg-brand-700 text-white ring-brand-700" : "bg-white ring-slate-200"
              }`}
            >
              <span className={`text-xs ${selected ? "text-brand-100" : "text-slate-500"}`}>
                {i === 0 ? "Today" : l.weekday}
              </span>
              <span className="text-lg font-bold leading-tight">{l.day}</span>
              <span className={`text-xs ${selected ? "text-brand-100" : "text-slate-500"}`}>{l.month}</span>
            </button>
          );
        })}
      </div>

      {/* 3. Time */}
      <SectionTitle step={3}>Pick a time</SectionTitle>
      {!service ? (
        <p className="text-sm text-slate-500">Choose a service to see available times.</p>
      ) : slots.isPending || slots.isFetching ? (
        <div className="grid grid-cols-3 gap-2" aria-busy="true" aria-label="Loading times">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : slots.isError ? (
        <p className="text-sm text-red-600" role="alert">
          {apiError(slots.error).message}
        </p>
      ) : slots.data.slots.length === 0 ? (
        <p className="rounded-xl bg-slate-50 p-4 text-center text-sm text-slate-600">
          No free slots — try another day
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Times">
          {slots.data.slots.map((iso) => {
            const selected = slot === iso;
            return (
              <button
                key={iso}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setSlot(iso)}
                className={`min-h-12 rounded-xl text-sm font-semibold ring-1 ${
                  selected ? "bg-brand-700 text-white ring-brand-700" : "bg-white text-slate-800 ring-slate-200"
                }`}
              >
                {formatTime(iso, tz)}
              </button>
            );
          })}
        </div>
      )}

      {/* 4. Details */}
      <SectionTitle step={4}>Your details</SectionTitle>
      <form id="booking-form" noValidate onSubmit={form.handleSubmit(onSubmit)} className="space-y-3">
        <Field
          label="Name"
          autoComplete="name"
          placeholder="Your full name"
          error={form.formState.errors.name?.message}
          {...form.register("name")}
        />
        <Field
          label="Mobile number"
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          placeholder="98765 43210"
          maxLength={10}
          prefix="+91"
          error={form.formState.errors.phone?.message}
          {...form.register("phone")}
        />
        {formError && (
          <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {formError}
          </p>
        )}
      </form>

      {/* Sticky confirm */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto max-w-lg">
          {service && slot && (
            <p className="mb-2 truncate text-center text-sm text-slate-600">
              {service.name} · {formatBookingDate(slot, tz)} · {formatINR(service.price)}
            </p>
          )}
          <Button
            type="submit"
            form="booking-form"
            className="min-h-12 w-full text-base"
            disabled={!service || !slot || mutation.isPending}
          >
            {mutation.isPending ? "Booking…" : "Confirm booking"}
          </Button>
        </div>
      </div>
    </PageShell>
  );
}

function Success({
  booking,
  business,
  onAgain,
}: {
  booking: BookingResponse;
  business: PublicBusiness;
  onAgain: () => void;
}) {
  const when = formatBookingDate(booking.start_time, business.timezone);
  const waText = `Hi ${business.name}, I just booked ${booking.service} on ${when}. Ref ${booking.booking_id}.`;
  return (
    <div className="py-10 text-center" aria-live="polite">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 text-3xl text-brand-700">
        ✓
      </div>
      <h1 className="mt-4 text-2xl font-bold">You're booked!</h1>
      <p className="mt-1 text-slate-600">{business.name}</p>
      <dl className="mx-auto mt-6 max-w-xs space-y-3 rounded-2xl bg-slate-50 p-4 text-left">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Booking ref</dt>
          <dd className="font-mono font-semibold">{booking.booking_id}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">When</dt>
          <dd className="font-semibold">{when}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Service</dt>
          <dd className="font-semibold">{booking.service}</dd>
        </div>
      </dl>
      <div className="mx-auto mt-6 flex max-w-xs flex-col gap-2">
        {business.phone && (
          <a
            href={whatsappLink(business.phone, waText)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-12 items-center justify-center rounded-xl bg-[#25D366] px-4 font-semibold text-white"
          >
            Add to WhatsApp
          </a>
        )}
        <Button variant="secondary" className="min-h-12" onClick={onAgain}>
          Book another
        </Button>
      </div>
      <p className="mt-8 text-xs text-slate-400">
        Powered by <Link to="/" className="underline">SlotEase</Link>
      </p>
    </div>
  );
}
