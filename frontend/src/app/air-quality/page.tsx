"use client";

import { PageShell } from "@/components/ui";

// Air quality model is still in training (user, 2026-11-02). Page intentionally left empty.
export default function AirQualityPage() {
  return (
    <PageShell active="Air Quality" eyebrow="Air quality" title="Air quality"
      sub={<span className="inline-flex items-center gap-3">Coming soon <span className="rounded-full border border-amber/60 px-[8px] py-[2px] text-[11px] font-semibold uppercase tracking-wide text-amber">Beta</span></span>}>
      <div className="h-[420px] rounded-[16px] border border-dashed border-line" />
    </PageShell>
  );
}
