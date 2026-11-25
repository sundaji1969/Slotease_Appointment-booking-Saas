import { useState } from "react";

import { useToast } from "./Toast";
import { Button, Card } from "./ui";

export function ShareCard({ slug, businessName }: { slug: string; businessName: string }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const url = `${window.location.origin}/${slug}`;
  const waText = `Book your next appointment at ${businessName} in 30 seconds: ${url}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast("Couldn't copy — select the link and copy it manually", "error");
    }
  }

  return (
    <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Your booking link</p>
        <a href={`/${slug}`} target="_blank" rel="noreferrer" className="block truncate font-medium text-brand-700">
          {url.replace(/^https?:\/\//, "")}
        </a>
      </div>
      <div className="flex shrink-0 gap-2">
        <Button variant="secondary" onClick={copy}>
          {copied ? "Copied ✓" : "Copy link"}
        </Button>
        <a
          href={`https://wa.me/?text=${encodeURIComponent(waText)}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center rounded-xl bg-[#25D366] px-4 py-2.5 text-sm font-semibold text-white hover:brightness-95"
        >
          Share on WhatsApp
        </a>
      </div>
    </Card>
  );
}
