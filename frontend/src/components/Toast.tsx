import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

type Tone = "error" | "success" | "info";
type ToastItem = { id: number; message: string; tone: Tone };

const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const show = useCallback((message: string, tone: Tone = "info") => {
    const id = nextId.current++;
    setItems((xs) => [...xs, { id, message, tone }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 5000);
  }, []);

  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="assertive"
        className="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-3"
      >
        {items.map((t) => (
          <div
            key={t.id}
            role={t.tone === "error" ? "alert" : "status"}
            className={`pointer-events-auto w-full max-w-sm rounded-xl px-4 py-3 text-sm font-medium shadow-lg ring-1 ${
              t.tone === "error"
                ? "bg-red-600 text-white ring-red-700"
                : t.tone === "success"
                  ? "bg-brand-700 text-white ring-brand-800"
                  : "bg-slate-900 text-white ring-slate-800"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
