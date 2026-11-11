"use client";

import { Suspense } from "react";

import { motion } from "framer-motion";
import { useParams } from "next/navigation";
import { Icon } from "@/components/Icon";
import { CountUp } from "@/components/CountUp";
import { PageShell, Card, Skeleton, Waking, ErrorNote, Badge, useApi, ease } from "@/components/ui";
import { RISK_COLORS, RISK_BADGE, NO_DATA, FACTOR_LABELS, factorFracs, fmt, todayIST, dayLabel, forecastWhen, type Risk, type AirQuality } from "@/lib/api";

type Hist = Risk & { date: string };
type AqForecast = { status: string; origin_date: string | null; extrapolated: boolean; forecasts: { horizon: number; target_date: string; pm25_si_pred: number; category: string }[] };
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
  const aq = useApi<AirQuality>(id ? `/air-quality/${id}` : null);
  const aqf = useApi<AqForecast>(id ? `/air-quality/${id}/forecast` : null);
  const r = risk.data;
  const col = (r?.risk_class && RISK_COLORS[r.risk_class]) || NO_DATA;

  return (
    <PageShell active="Map" eyebrow="District detail"
      title={r ? <>{r.district_name}, <span className="text-muted">{r.state_name}</span></> : risk.error ? "District" : <span className="text-muted">Loading…</span>}
      sub={r ? `Wildfire forecast for ${dayLabel(r.date)}.` : undefined}>
      {risk.loading && <Waking />}
      {risk.notFound && <p className="rounded-[16px] border border-line bg-surface px-6 py-5 text-[15px] text-muted">No district with this number. <a href="/map" className="text-ember hover:underline">Find a district on the map</a>.</p>}
      {risk.error && !risk.notFound && <ErrorNote what="this district" />}

      {!risk.notFound && (<>
      {/* Hero */}
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="relative overflow-hidden">
          {!r ? <Skeleton h={220} /> : (
            <>
              <div className="pointer-events-none absolute -right-24 -top-24 h-[320px] w-[320px] rounded-full blur-3xl" style={{ background: `${col}22` }} />
              <Badge color={col}>{RISK_BADGE[r.risk_class] ?? "No forecast yet"}</Badge>
              <div className="mt-4 flex items-end gap-4">
                <span className="text-[76px] md:text-[112px] font-bold leading-[1]" style={{ color: col }}><CountUp to={Math.round(r.probability * 100)} suffix="%" /></span>
                <span className="pb-2 text-[16px] font-semibold leading-[22px] md:pb-3 md:text-[20px] md:leading-[26px]">chance of<br />wildfire {forecastWhen(r.date)}</span>
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
              <p className="text-[13px] text-muted">Top reasons the model gave for this forecast.</p>
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

      {/* Air quality: current CAMS estimate + model PM2.5 forecast */}
      <AirCard aq={aq.data} aqErr={aq.error} fc={aqf.data} fcErr={aqf.error} />
      </>)}

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

function AirCard({ aq, aqErr, fc, fcErr }: { aq: AirQuality | null; aqErr: boolean; fc: AqForecast | null; fcErr: boolean }) {
  const col = (aq?.aqi_category && RISK_COLORS[aq.aqi_category]) || NO_DATA;
  const today = todayIST();
  const next = (fc?.forecasts ?? []).filter((f) => f.target_date >= today).sort((a, b) => a.target_date.localeCompare(b.target_date));
  return (
    <Card className="mt-14" i={1}>
      <h2 className="text-[24px] font-semibold">Air quality</h2>
      <div className="mt-6 grid gap-8 md:grid-cols-[1fr_1.4fr]">
        <div>
          <p className="text-[13px] text-muted">Now (last 24 h average)</p>
          {aqErr ? <p className="mt-3 text-muted">Air quality not available.</p> : !aq ? <Skeleton h={90} className="mt-3" /> : (
            <>
              <p className="mt-2 text-[56px] font-bold leading-none" style={{ color: col }}>{aq.aqi ?? "–"}</p>
              <p className="mt-2 text-[16px] font-semibold" style={{ color: col }}>{aq.aqi_category ?? "No data"}</p>
              <p className="mt-3 text-[13px] text-muted">PM2.5 {fmt(aq.pm25)} · PM10 {fmt(aq.pm10)} µg/m³</p>
            </>
          )}
        </div>
        <div>
          <p className="text-[13px] text-muted">Next days (PM2.5 forecast)</p>
          {fcErr ? <p className="mt-3 text-muted">Forecast not available.</p> : !fc ? <Skeleton h={90} className="mt-3" /> : next.length === 0 ? (
            <p className="mt-3 text-muted">No forecast for today or later yet.</p>
          ) : (
            <div className="mt-3 grid grid-cols-3 gap-3">
              {next.map((f) => {
                const c = RISK_COLORS[f.category] ?? NO_DATA;
                return (
                  <div key={f.target_date} className="rounded-[12px] border border-line p-3">
                    <p className="text-[12px] text-muted">{dayLabel(f.target_date)}</p>
                    <p className="mt-1 text-[24px] font-bold" style={{ color: c }}>{Math.round(f.pm25_si_pred)}</p>
                    <p className="text-[12px] font-semibold" style={{ color: c }}>{f.category}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
      <p className="mt-6 text-[12px] leading-[18px] text-muted">
        Satellite-model estimate (Copernicus CAMS, CPCB formula), not a ground station reading. Forecast = our model&apos;s PM2.5 index{fc?.origin_date ? `, made on ${dayLabel(fc.origin_date)}` : ""}{fc?.extrapolated ? "; no CPCB station near this district, so less sure" : ""}. It can read low on very polluted days.
      </p>
    </Card>
  );
}
