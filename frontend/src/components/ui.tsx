import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { forwardRef } from "react";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-lg bg-slate-200 ${className}`} />;
}

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-700 text-white hover:bg-brand-800 disabled:bg-slate-300 disabled:text-slate-500",
  secondary: "bg-white text-slate-800 ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-50",
  ghost: "text-slate-700 hover:bg-slate-100 disabled:opacity-50",
  danger: "bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
    />
  );
}

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
  prefix?: ReactNode;
};

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, hint, prefix, id, className = "", ...props },
  ref,
) {
  const inputId = id ?? props.name;
  const errId = `${inputId}-error`;
  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <div
        className={`flex items-center rounded-xl bg-white ring-1 focus-within:ring-2 ${
          error ? "ring-red-400 focus-within:ring-red-500" : "ring-slate-300 focus-within:ring-brand-600"
        }`}
      >
        {prefix && <span className="pl-3 text-slate-500">{prefix}</span>}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errId : undefined}
          className="min-h-12 w-full rounded-xl bg-transparent px-3 text-base outline-none placeholder:text-slate-400"
          {...props}
        />
      </div>
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && (
        <p id={errId} className="mt-1 text-sm text-red-600" aria-live="polite">
          {error}
        </p>
      )}
    </div>
  );
});

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200 ${className}`}>{children}</div>;
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-40 flex items-end justify-center bg-slate-900/40 p-0 sm:items-center sm:p-4"
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <div className="w-full max-w-md rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-lg p-2 hover:bg-slate-100">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const STATUS_STYLES: Record<string, string> = {
  booked: "bg-sky-100 text-sky-800 ring-sky-200",
  completed: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  cancelled: "bg-slate-100 text-slate-500 ring-slate-200 line-through",
  no_show: "bg-amber-100 text-amber-800 ring-amber-200",
};

export function StatusBadge({ status }: { status: string }) {
  const label = status === "no_show" ? "No-show" : status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${STATUS_STYLES[status]}`}>
      {label}
    </span>
  );
}
