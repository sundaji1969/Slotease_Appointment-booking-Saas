import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { apiError } from "../api/client";
import { askAssistant } from "../api/endpoints";
import type { AssistantReply, AssistantTurn } from "../api/types";
import { formatDay, formatTime } from "../lib/format";

type Props = {
  slug: string;
  tz: string;
  onPick: (serviceId: string, date: string, slotIso: string) => void;
};

type Entry = AssistantTurn & { result?: AssistantReply };

/** "Just tell us what you need" — suggests REAL free slots; tapping one fills the booking form. */
export function AssistantPanel({ slug, tz, onPick }: Props) {
  const [text, setText] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);

  const ask = useMutation({
    mutationFn: ({ message, history }: { message: string; history: AssistantTurn[] }) =>
      askAssistant(slug, message, history),
    onSuccess: (result) => setEntries((xs) => [...xs, { role: "assistant", content: result.reply, result }]),
    onError: (err) => setEntries((xs) => [...xs, { role: "assistant", content: apiError(err).message }]),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    const message = text.trim();
    if (!message || ask.isPending) return;
    const history = entries.slice(-6).map(({ role, content }) => ({ role, content }));
    setEntries((xs) => [...xs, { role: "user", content: message }]);
    setText("");
    ask.mutate({ message, history });
  }

  return (
    <section aria-label="Booking assistant" className="mt-5 rounded-2xl bg-brand-50 p-4 ring-1 ring-brand-100">
      <p className="text-sm font-semibold text-brand-900">✨ Not sure? Just tell us what you need</p>
      {entries.length > 0 && (
        <div className="mt-3 space-y-2" aria-live="polite">
          {entries.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : ""}>
              <p
                className={`inline-block max-w-[90%] rounded-2xl px-3 py-2 text-sm ${
                  m.role === "user" ? "bg-brand-700 text-white" : "bg-white text-slate-800 ring-1 ring-slate-200"
                }`}
              >
                {m.content}
              </p>
              {m.result && m.result.service_id && m.result.date && m.result.slots.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {m.result.slots.map((iso) => (
                    <button
                      key={iso}
                      type="button"
                      onClick={() => onPick(m.result!.service_id!, m.result!.date!, iso)}
                      className="min-h-11 rounded-xl bg-white px-3 text-sm font-semibold text-brand-800 ring-1 ring-brand-200 hover:ring-brand-600"
                    >
                      {formatDay(iso, tz)} · {formatTime(iso, tz)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {ask.isPending && <p className="text-sm text-slate-500">Checking availability…</p>}
        </div>
      )}
      <form onSubmit={submit} className="mt-3 flex gap-2">
        <label htmlFor="assistant-input" className="sr-only">
          Describe what you'd like to book
        </label>
        <input
          id="assistant-input"
          value={text}
          maxLength={300}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. haircut Saturday evening"
          className="min-h-12 min-w-0 flex-1 rounded-xl bg-white px-3 text-base ring-1 ring-slate-300 outline-none focus:ring-2 focus:ring-brand-600"
        />
        <button
          type="submit"
          disabled={!text.trim() || ask.isPending}
          className="min-h-12 rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white disabled:bg-slate-300"
        >
          Ask
        </button>
      </form>
    </section>
  );
}
