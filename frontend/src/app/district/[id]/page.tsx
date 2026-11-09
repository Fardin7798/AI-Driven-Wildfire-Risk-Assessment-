"use client";

import { Suspense } from "react";

import { motion } from "framer-motion";
import { useParams } from "next/navigation";
import { Icon } from "@/components/Icon";
import { CountUp } from "@/components/CountUp";
import { PageShell, Card, Skeleton, Waking, ErrorNote, Badge, useApi, ease } from "@/components/ui";
import { RISK_COLORS, RISK_BADGE, NO_DATA, FACTOR_LABELS, factorFracs, shortTime, type Risk } from "@/lib/api";

type Hist = Risk & { date: string };
type Weather = { date: string; temp_max: number | null; temp_min: number | null; rh_mean: number | null; wind_max: number | null; precip_sum: number | null; is_forecast: boolean };

const day = (d: string) => new Date(`${d}T00:00:00+05:30`).toLocaleDateString("en-US", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });

export default function DistrictPage() {
  return (
    <Suspense fallback={null}>
      <DistrictView />
    </Suspense>
  );
}

function DistrictView() {
  const { id } = useParams<{ id: string }>();
  const risk = useApi<Risk>(id ? `/risk/${id}` : null);
  const hist = useApi<Hist[]>(id ? `/risk/${id}/history?days=14` : null);
  const wx = useApi<Weather[]>(id ? `/weather/${id}` : null);
  const r = risk.data;
  const col = (r?.risk_class && RISK_COLORS[r.risk_class]) || NO_DATA;

  return (
    <PageShell active="Map" eyebrow="District detail"
      title={r ? <>{r.district_name}, <span className="text-muted">{r.state_name}</span></> : risk.error ? "District" : <span className="text-muted">Loading…</span>}
      sub={r ? `Today's wildfire forecast, updated ${shortTime(r.as_of?.ist)}.` : undefined}>
      {risk.loading && <Waking />}
      {risk.error && <ErrorNote what="this district" />}

      {/* Hero */}
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="relative overflow-hidden">
          {!r ? <Skeleton h={220} /> : (
            <>
              <div className="pointer-events-none absolute -right-24 -top-24 h-[320px] w-[320px] rounded-full blur-3xl" style={{ background: `${col}22` }} />
              <Badge color={col}>{RISK_BADGE[r.risk_class] ?? "No forecast yet"}</Badge>
              <div className="mt-4 flex items-end gap-4">
                <span className="text-[76px] md:text-[112px] font-bold leading-[1]" style={{ color: col }}><CountUp to={Math.round(r.probability * 100)} suffix="%" /></span>
                <span className="pb-2 text-[16px] font-semibold leading-[22px] md:pb-3 md:text-[20px] md:leading-[26px]">chance of<br />wildfire today</span>
              </div>
              <a href={`/map?d=${id}`} className="mt-6 inline-flex items-center gap-2 text-[15px] text-muted hover:text-white">
                <Icon name="arrow-left" size={16} /> See it on the map
              </a>
            </>
          )}
        </Card>

        <Card i={1}>
          <h2 className="text-[24px] font-semibold">Why today?</h2>
          {!r ? <Skeleton h={160} className="mt-4" /> : (
            <div className="mt-5 space-y-5">
              {r.top_factors.slice(0, 3).map((f, j, arr) => (
                <div key={f.feature}>
                  <p className="text-[16px]">{FACTOR_LABELS[f.feature] ?? f.label}</p>
                  <div className="mt-2 h-[8px] w-full rounded-full bg-white/5">
                    <motion.div className="h-full rounded-full bg-ember" initial={{ width: 0 }} animate={{ width: `${factorFracs(arr)[j] * 100}%` }} transition={{ duration: 1.1, ease, delay: 0.2 + j * 0.12 }}
                      style={{ boxShadow: "0 0 10px #F9731688" }} />
                  </div>
                </div>
              ))}
              <p className="text-[13px] text-muted">Top reasons the model gave for today&apos;s forecast.</p>
            </div>
          )}
        </Card>
      </div>

      {/* History */}
      <Card className="mt-6" i={2}>
        <div className="flex items-baseline justify-between">
          <h2 className="whitespace-nowrap text-[24px] font-semibold">Recent days</h2>
          <span className="text-right text-[13px] text-muted">Chance of wildfire each day</span>
        </div>
        {hist.error ? <p className="mt-4 text-muted">History not available.</p> : !hist.data ? <Skeleton h={200} className="mt-6" /> : (
          <History rows={[...hist.data].sort((a, b) => a.date.localeCompare(b.date))} />
        )}
      </Card>

      {/* Weather */}
      <h2 className="mt-14 text-[28px] font-semibold">Weather</h2>
      {wx.error ? <p className="mt-4 text-muted">Weather not available.</p> : !wx.data ? <Skeleton h={160} className="mt-6" /> : (
        <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
          {wx.data.slice(-7).map((w, j) => (
            <Card key={w.date} i={j} className="!p-5">
              <p className="text-[13px] text-muted">{day(w.date)}{w.is_forecast && <span className="ml-1 text-ember">· forecast</span>}</p>
              <p className="mt-3 text-[28px] font-bold leading-none">{w.temp_max != null ? Math.round(w.temp_max) : "–"}°<span className="text-[16px] font-normal text-muted"> / {w.temp_min != null ? Math.round(w.temp_min) : "–"}°</span></p>
              <div className="mt-4 space-y-1 text-[13px] text-muted">
                <p>Humidity {w.rh_mean ?? "–"}%</p>
                <p>Wind {w.wind_max ?? "–"} km/h</p>
                <p>Rain {w.precip_sum ?? "–"} mm</p>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Air quality: pending model, left empty on purpose */}
      <Card className="mt-14" i={1}>
        <div className="flex items-center gap-3">
          <h2 className="text-[24px] font-semibold">Air quality</h2>
          <span className="rounded-full border border-amber/60 px-[8px] py-[2px] text-[11px] font-semibold uppercase tracking-wide text-amber">Coming soon</span>
        </div>
        <div className="mt-6 h-[120px] rounded-[12px] border border-dashed border-line" />
      </Card>

      <a href="/stay-safe" className="mt-10 flex h-[56px] items-center justify-center rounded-[14px] bg-ember text-[17px] font-semibold shadow-[0_0_24px_#F9731655] transition hover:brightness-110 md:w-[320px]">
        How to stay safe
      </a>
    </PageShell>
  );
}

function History({ rows }: { rows: Hist[] }) {
  const max = Math.max(0.25, ...rows.map((r) => r.probability));
  return (
    <div className="mt-8 flex h-[200px] items-end gap-3">
      {rows.map((r, j) => {
        const c = RISK_COLORS[r.risk_class] || NO_DATA;
        return (
          <div key={r.date} className="group relative flex h-full w-[48px] flex-col items-center justify-end">
            <span className="mb-1 text-[11px] text-muted">{Math.round(r.probability * 100)}%</span>
            <motion.div className="w-[32px] rounded-t-[6px]" style={{ background: c, boxShadow: `0 0 10px ${c}55` }}
              initial={{ height: 0 }} whileInView={{ height: `${(r.probability / max) * 82}%` }} viewport={{ once: true }} transition={{ duration: 0.8, ease, delay: j * 0.04 }} />
            <span className="mt-2 whitespace-nowrap text-[11px] text-muted">{new Date(`${r.date}T00:00:00+05:30`).toLocaleDateString("en-US", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" })}</span>
          </div>
        );
      })}
    </div>
  );
}
