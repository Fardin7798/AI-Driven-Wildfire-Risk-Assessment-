"use client";

import { Suspense, useMemo, useState } from "react";
import { PageShell, Card, Skeleton, Waking, ErrorNote, useApi } from "@/components/ui";
import { RISK_COLORS, NO_DATA, fmt, dayLabel, todayIST, shortTime, type AirQuality } from "@/lib/api";

type Fc = { horizon: number; target_date: string; pm25_si_pred: number; category: string };
type DistFc = { region_id: number; status: string; origin_date: string | null; extrapolated: boolean; forecasts: Fc[] };
type AllFc = { model_version: string | null; counts: Record<string, number>; districts: DistFc[] };

const CATS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"];

export default function AirQualityPage() {
  return (
    <Suspense fallback={null}>
      <AirQualityView />
    </Suspense>
  );
}

function AirQualityView() {
  const now = useApi<AirQuality[]>("/air-quality/latest?limit=1000");
  const fc = useApi<AllFc>("/air-quality/forecast");
  const [q, setQ] = useState("");
  const today = todayIST();

  const fcById = useMemo(() => {
    const m = new Map<number, Fc | undefined>();
    for (const d of fc.data?.districts ?? []) {
      m.set(d.region_id, [...d.forecasts].filter((f) => f.target_date > today).sort((a, b) => a.target_date.localeCompare(b.target_date))[0]);
    }
    return m;
  }, [fc.data, today]);

  const rows = useMemo(() => [...(now.data ?? [])].sort((a, b) => (b.aqi ?? -1) - (a.aqi ?? -1)), [now.data]);
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of rows) if (r.aqi_category) c[r.aqi_category] = (c[r.aqi_category] ?? 0) + 1;
    return c;
  }, [rows]);
  const s = q.trim().toLowerCase();
  const shown = s.length >= 2
    ? rows.filter((r) => r.district_name.toLowerCase().includes(s) || r.state_name.toLowerCase().includes(s))
    : rows.slice(0, 15);
  const noData = now.data ? 676 - rows.filter((r) => r.aqi != null).length : 0;
  const tomorrowDate = [...fcById.values()].find(Boolean)?.target_date;

  return (
    <PageShell active="Air Quality" eyebrow="Air quality" title="How clean is the air?"
      sub="Air quality index (AQI) for every district, from the last 24 hours, plus our model's PM2.5 forecast for the coming day.">
      {now.loading && <Waking />}
      {now.error && <ErrorNote what="air quality" />}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-6">
        {CATS.map((c, j) => (
          <Card key={c} i={j} className="!p-5">
            <p className="text-[13px] font-semibold" style={{ color: RISK_COLORS[c] }}>{c}</p>
            {now.data ? <p className="mt-2 text-[32px] font-bold leading-none">{fmt(counts[c] ?? 0)}</p> : <Skeleton h={32} className="mt-2 w-[60px]" />}
            <p className="mt-1 text-[12px] text-muted">districts</p>
          </Card>
        ))}
      </div>
      {now.data && noData > 0 && <p className="mt-3 text-[13px] text-muted">{noData} districts have no reading right now.</p>}

      <div className="mt-12 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-[28px] font-semibold">{s.length >= 2 ? "Search results" : "Worst air right now"}</h2>
          {rows[0] && <p className="mt-2 text-[14px] text-muted">Readings up to {shortTime(rows[0].observed_at_utc)}.</p>}
        </div>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search district or state" aria-label="Search district or state"
          className="h-[48px] w-full rounded-[24px] border border-line bg-surface px-5 text-[16px] text-white outline-none placeholder:text-muted md:w-[320px]" />
      </div>

      {!now.data ? (!now.error && <Skeleton h={360} className="mt-6" />) : shown.length === 0 ? (
        <p className="mt-6 text-muted">No district matches “{q}”.</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-[16px] border border-line">
          <table className="w-full min-w-[600px] text-left text-[14px]">
            <thead className="bg-surface text-muted">
              <tr>
                <th className="px-5 py-3 font-normal">District</th>
                <th className="px-5 py-3 font-normal">AQI now</th>
                <th className="px-5 py-3 font-normal">PM2.5</th>
                <th className="px-5 py-3 font-normal">{tomorrowDate ? `Forecast ${dayLabel(tomorrowDate)}` : "Forecast"}</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => {
                const c = (r.aqi_category && RISK_COLORS[r.aqi_category]) || NO_DATA;
                const f = fcById.get(r.region_id);
                const fcCol = f ? RISK_COLORS[f.category] ?? NO_DATA : NO_DATA;
                return (
                  <tr key={r.region_id} className="border-t border-line hover:bg-white/[0.03]">
                    <td className="px-5 py-3">{r.district_name}<span className="block text-[12px] text-muted">{r.state_name}</span></td>
                    <td className="px-5 py-3"><span className="text-[18px] font-bold" style={{ color: c }}>{r.aqi ?? "–"}</span> <span className="text-[13px]" style={{ color: c }}>{r.aqi_category ?? ""}</span></td>
                    <td className="px-5 py-3 tabular-nums text-muted">{fmt(r.pm25)} µg/m³</td>
                    <td className="px-5 py-3">{f ? <span style={{ color: fcCol }}>{Math.round(f.pm25_si_pred)} {f.category}</span> : <span className="text-muted">–</span>}</td>
                    <td className="px-5 py-3 text-right"><a href={`/district/${r.region_id}`} className="text-ember hover:underline">Open</a></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-6 text-[12px] leading-[18px] text-muted">
        AQI now: satellite-model estimate (Copernicus CAMS) turned into India&apos;s AQI with the CPCB formula; not a ground station reading.
        Forecast: our model&apos;s PM2.5 index{fc.data?.districts?.[0]?.origin_date ? `, made on ${dayLabel(fc.data.districts[0].origin_date)}` : ""}; it can read low on very polluted days.
        For official numbers see CPCB.
      </p>
    </PageShell>
  );
}
