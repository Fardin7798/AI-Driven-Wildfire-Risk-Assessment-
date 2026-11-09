"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { CountUp } from "@/components/CountUp";
import { PageShell, Card, Skeleton, Waking, ErrorNote, useApi, ease } from "@/components/ui";
import { fmt } from "@/lib/api";

type Stats = { period_days: number; total_detections: number; high_confidence_count: number; outside_districts: number; by_state: Record<string, number>; by_source: Record<string, number> };
type Fire = { id: number; source: string; acq_datetime_utc: string; lat: number; lon: number; frp: number | null; confidence: string; daynight: string; region_id: number | null; district_name: string | null; state_name: string | null };

const PERIODS = [1, 7, 30];
const when = (v: string) => {
  const d = new Date(v);
  if (isNaN(d.getTime())) return v.replace(/^\w{3} \d{4}-\d{2}-\d{2} /, "").replace(" (UTC+05:30)", "");
  return d.toLocaleString("en-US", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }) + " IST";
};
const conf = (c: string) => {
  const n = Number(c);
  if (c === "h" || n >= 80) return { t: "High", c: "#EF4444" };
  if (c === "n" || n >= 50) return { t: "Medium", c: "#F59E0B" };
  return { t: "Low", c: "#9AA3B2" };
};

export default function AlertsPage() {
  const [days, setDays] = useState(7);
  const stats = useApi<Stats>(`/fires/stats?days=${days}`);
  const recent = useApi<Fire[]>(`/fires/recent?hours=${days * 24}&limit=20`);
  const span = days === 1 ? "24 hours" : `${days} days`;
  const s = stats.data;
  const states = s ? Object.entries(s.by_state).sort((a, b) => b[1] - a[1]).slice(0, 10) : [];
  const top = states[0]?.[1] ?? 1;

  return (
    <PageShell active="Alerts" eyebrow="Fire alerts" title="Fires seen from space"
      sub="Hot spots spotted by NASA satellites over India. Not every hot spot is a forest fire; many are crop burning.">
      <div className="mb-8 flex gap-2">
        {PERIODS.map((p) => (
          <button key={p} onClick={() => setDays(p)}
            className={`h-[40px] rounded-[20px] border px-5 text-[15px] transition ${p === days ? "border-ember bg-ember/15 text-white" : "border-line text-muted hover:text-white"}`}>
            {p === 1 ? "24 hours" : `${p} days`}
          </button>
        ))}
      </div>
      {stats.loading && <Waking />}
      {stats.error && <ErrorNote what="fire numbers" />}

      <div className="grid gap-6 md:grid-cols-3">
        {[
          { l: "Fire detections", v: s?.total_detections, c: "#F97316" },
          { l: "High confidence", v: s?.high_confidence_count, c: "#EF4444" },
          { l: "Outside any district", v: s?.outside_districts, c: "#9AA3B2" },
        ].map((t, j) => (
          <Card key={t.l} i={j}>
            <p className="text-[15px] text-muted">{t.l}</p>
            {s ? <p className="mt-3 text-[48px] font-bold leading-none" style={{ color: t.c }}><CountUp key={`${days}-${t.l}`} to={t.v ?? null} /></p> : <Skeleton h={48} className="mt-3 w-[160px]" />}
          </Card>
        ))}
      </div>

      <Card className="mt-6" i={1}>
        <h2 className="text-[24px] font-semibold">Most fires by state</h2>
        {!s ? <Skeleton h={300} className="mt-6" /> : (
          <div className="mt-6 space-y-3">
            {states.map(([name, n], j) => (
              <div key={name} className="grid grid-cols-[160px_1fr_72px] items-center gap-4 text-[15px]">
                <span className="truncate">{name}</span>
                <div className="h-[10px] rounded-full bg-white/5">
                  <motion.div key={`${days}-${name}`} className="h-full rounded-full bg-ember" style={{ boxShadow: "0 0 10px #F9731688" }}
                    initial={{ width: 0 }} animate={{ width: `${(n / top) * 100}%` }} transition={{ duration: 0.9, ease, delay: j * 0.05 }} />
                </div>
                <span className="text-right tabular-nums text-muted">{fmt(n)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <h2 className="mt-14 text-[28px] font-semibold">Latest detections</h2>
      <p className="mt-2 text-[15px] text-muted">Newest 20 from the last {span}.</p>
      {recent.error ? <div className="mt-6"><ErrorNote what="latest fires" /></div> : !recent.data ? <Skeleton h={320} className="mt-6" /> : recent.data.length === 0 ? (
        <p className="mt-6 text-muted">No detections in the last {span}.</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-[16px] border border-line">
          <table className="w-full min-w-[640px] text-left text-[14px]">
            <thead className="bg-surface text-muted">
              <tr><th className="px-5 py-3 font-normal">Time</th><th className="px-5 py-3 font-normal">Place</th><th className="px-5 py-3 font-normal">Confidence</th><th className="px-5 py-3 font-normal">Strength</th><th className="px-5 py-3" /></tr>
            </thead>
            <tbody>
              {recent.data.map((f) => {
                const c = conf(f.confidence);
                return (
                  <tr key={f.id} className="border-t border-line hover:bg-white/[0.03]">
                    <td className="px-5 py-3">{when(f.acq_datetime_utc)}</td>
                    <td className="px-5 py-3">
                      {f.district_name ? <span>{f.district_name}, {f.state_name}</span> : <span className="text-muted">Outside any district</span>}
                      <span className="block tabular-nums text-[12px] text-muted">{f.lat.toFixed(2)}, {f.lon.toFixed(2)}</span>
                    </td>
                    <td className="px-5 py-3"><span style={{ color: c.c }}>{c.t}</span></td>
                    <td className="px-5 py-3 tabular-nums text-muted">{f.frp != null ? `${Math.round(f.frp)} MW` : "–"}</td>
                    <td className="px-5 py-3 text-right">{f.region_id != null && <a href={`/district/${f.region_id}`} className="text-ember hover:underline">Open</a>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </PageShell>
  );
}
