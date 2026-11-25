import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="min-h-dvh bg-gradient-to-b from-brand-50 to-white">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-4 py-5">
        <span className="flex items-center gap-2 font-bold text-brand-800">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white">✓</span>
          SlotEase
        </span>
        <Link to="/login" className="text-sm font-semibold text-slate-700">
          Sign in
        </Link>
      </header>
      <main className="mx-auto max-w-5xl px-4 pb-20 pt-10 sm:pt-20">
        <h1 className="max-w-2xl text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          Stop taking bookings on the phone.
        </h1>
        <p className="mt-4 max-w-xl text-lg text-slate-600">
          Give your clinic, salon or physio centre a booking page customers can use in 30 seconds. No double
          bookings — ever. Track no-shows and revenue from one dashboard.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/register"
            className="inline-flex min-h-12 items-center rounded-xl bg-brand-700 px-6 font-semibold text-white hover:bg-brand-800"
          >
            Create your booking page
          </Link>
          <Link
            to="/glow-salon"
            className="inline-flex min-h-12 items-center rounded-xl bg-white px-6 font-semibold text-slate-800 ring-1 ring-slate-300"
          >
            See a demo page
          </Link>
        </div>
        <p className="mt-4 text-sm text-slate-500">₹499 / month per business.</p>
        <ul className="mt-16 grid gap-4 sm:grid-cols-3">
          {[
            ["Book in 30 seconds", "Mobile-first page at slotease.app/your-name. Pick a service, a time, done."],
            ["Zero double bookings", "The database itself refuses overlapping appointments, even at the same instant."],
            ["Know your numbers", "Today's schedule, weekly calendar, no-show rate and revenue estimate."],
          ].map(([t, d]) => (
            <li key={t} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <p className="font-semibold">{t}</p>
              <p className="mt-1 text-sm text-slate-600">{d}</p>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
