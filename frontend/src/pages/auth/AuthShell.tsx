import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <Link to="/" className="mb-8 flex items-center gap-2 font-bold text-brand-800">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white">✓</span>
          SlotEase
        </Link>
        <h1 className="text-2xl font-bold">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}
