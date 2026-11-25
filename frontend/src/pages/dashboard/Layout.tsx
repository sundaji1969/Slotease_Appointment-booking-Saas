import { useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Skeleton } from "../../components/ui";
import { useBusiness } from "../../hooks/useBusiness";
import { clearToken } from "../../lib/auth";

const NAV = [
  { to: "/dashboard", label: "Today", icon: "◉", end: true },
  { to: "/dashboard/week", label: "Week", icon: "▦" },
  { to: "/dashboard/services", label: "Services", icon: "✂" },
  { to: "/dashboard/hours", label: "Hours", icon: "◷" },
  { to: "/dashboard/stats", label: "Stats", icon: "▲" },
];

export default function DashboardLayout() {
  const business = useBusiness();
  const navigate = useNavigate();
  const qc = useQueryClient();

  function logout() {
    clearToken();
    qc.clear();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-dvh md:flex">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <div className="mb-6 flex items-center gap-2 font-bold text-brand-800">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white">✓</span>
          SlotEase
        </div>
        <nav className="flex flex-col gap-1" aria-label="Dashboard">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${
                  isActive ? "bg-brand-50 text-brand-800" : "text-slate-600 hover:bg-slate-50"
                }`
              }
            >
              <span aria-hidden className="w-4 text-center">
                {n.icon}
              </span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto border-t border-slate-100 pt-4">
          {business.data ? (
            <p className="truncate text-sm font-semibold">{business.data.name}</p>
          ) : (
            <Skeleton className="h-4 w-32" />
          )}
          <button type="button" onClick={logout} className="mt-1 text-sm text-slate-500 hover:text-slate-800">
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <span className="truncate font-bold text-brand-800">{business.data?.name ?? "SlotEase"}</span>
          <button type="button" onClick={logout} className="text-sm text-slate-500">
            Sign out
          </button>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 pb-24 md:p-8">
          <Outlet />
        </main>
      </div>

      <nav
        aria-label="Dashboard"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-slate-200 bg-white md:hidden"
      >
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) =>
              `flex min-h-14 flex-col items-center justify-center text-xs font-medium ${
                isActive ? "text-brand-700" : "text-slate-500"
              }`
            }
          >
            <span aria-hidden className="text-base">
              {n.icon}
            </span>
            {n.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
