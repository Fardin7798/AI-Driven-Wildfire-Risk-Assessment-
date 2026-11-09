"use client";

import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import { Nav } from "@/components/Nav";
import { Icon, type IconName } from "@/components/Icon";
import { CountUp } from "@/components/CountUp";
import { NASHIK } from "@/lib/nashik-outline";
import {
  factorFracs, dayLabel, forecastWhen, fmt, RISK_COLORS, RISK_BADGE, NO_DATA, FACTOR_LABELS,
  type Risk, type AirQuality, type FireStats,
} from "@/lib/api";

const ease = [0.16, 1, 0.3, 1] as const;
const up: Variants = { hidden: { opacity: 0, y: 20 }, show: (i: number = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.7, ease, delay: i * 0.1 } }) };
const inView = { initial: "hidden", whileInView: "show", viewport: { once: true, amount: 0.3 } } as const;

const SAFETY: { title: string; icon: IconName; stage: string }[] = [
  { title: "Before a fire", icon: "shield-house", stage: "before" },
  { title: "During a fire", icon: "flame", stage: "during" },
  { title: "After a fire", icon: "wind", stage: "after" },
];

/** Phone layout of the Home scroll story (below 768 px). Same data and story, stacked. */
export function HomeMobile({ risk, aq, fires }: { risk: Risk | null; aq: AirQuality | null; fires: FireStats | null }) {
  const [q, setQ] = useState("");
  const cls = risk?.risk_class;
  const col = cls ? RISK_COLORS[cls] ?? NO_DATA : NO_DATA;
  const aqCol = aq?.aqi_category ? RISK_COLORS[aq.aqi_category] ?? "#F59E0B" : "#F59E0B";
  const fires30 = risk?.top_factors.find((f) => f.feature === "fires_prev_30d")?.value ?? null;
  const pct = risk ? Math.round(risk.probability * 100) : null;
  const top3 = fires ? Object.entries(fires.by_state).sort((a, b) => b[1] - a[1]).slice(0, 3) : [];
  const factors = risk?.top_factors.slice(0, 3) ?? [];
  const fracs = factorFracs(factors);

  return (
    <div className="overflow-x-hidden md:hidden">
      <Nav active="" />

      {/* 01 Hero */}
      <section className="relative overflow-hidden px-[20px] pb-[48px] pt-[96px]">
        <motion.img src="/img/globe.png" alt="Earth at night with India glowing" draggable={false}
          className="pointer-events-none mx-auto block w-[86vw] max-w-[420px] select-none"
          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1, rotate: [0, 2, 0] }}
          transition={{ opacity: { duration: 1.2 }, scale: { duration: 1.4, ease }, rotate: { duration: 12, repeat: Infinity, ease: "easeInOut" } }} />
        <motion.h1 variants={up} initial="hidden" animate="show" custom={1} className="mt-[8px] text-[44px] font-bold leading-[50px]">
          Know your<br />wildfire risk.
        </motion.h1>
        <motion.p variants={up} initial="hidden" animate="show" custom={2} className="mt-[12px] text-[16px] leading-[24px] text-white/80">
          AI forecast for every district in India, updated daily.
        </motion.p>
        <motion.form variants={up} initial="hidden" animate="show" custom={3} role="search" action="/map" method="get"
          onSubmit={(e) => { e.preventDefault(); const v = q.trim(); window.location.href = v.length >= 2 ? `/map?q=${encodeURIComponent(v)}` : "/map"; }}
          className="relative mt-[20px] flex h-[54px] items-center rounded-[16px] border border-line bg-surface focus-within:border-ember/60">
          <input name="q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search district or town" aria-label="Search district or town" autoComplete="off"
            className="h-full w-full bg-transparent pl-[18px] pr-[56px] text-[16px] text-white outline-none placeholder:text-muted" />
          <button type="submit" aria-label="Search" className="absolute right-[6px] top-[5px] flex h-[44px] w-[44px] items-center justify-center rounded-[12px] hover:bg-white/10">
            <Icon name="search" size={20} color="#9AA3B2" />
          </button>
        </motion.form>
      </section>

      {/* 02 Fires this week */}
      <section className="relative overflow-hidden">
        <motion.img src="/img/india-night.png" alt="Satellite fire detections over India" draggable={false}
          className="block h-[300px] w-full select-none object-cover" style={{ objectPosition: "35% 40%" }}
          initial={{ scale: 1.25 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ duration: 1.6, ease }} />
        <div className="absolute inset-x-0 top-0 h-[80px]" style={{ background: "linear-gradient(180deg, #0B0D12 0%, #0B0D1200 100%)" }} />
        <div className="absolute inset-x-0 top-[180px] h-[120px]" style={{ background: "linear-gradient(180deg, #0B0D1200 0%, #0B0D12 100%)" }} />
        <motion.div {...inView} className="relative -mt-[56px] px-[20px] pb-[48px]">
          <motion.div variants={up} custom={0} className="text-[64px] font-bold leading-[68px]">
            <CountUp to={fires?.total_detections ?? null} duration={2} />
          </motion.div>
          <motion.p variants={up} custom={1} className="mt-[4px] text-[18px] leading-[24px] text-white/90">fires spotted by satellites this week</motion.p>
          <motion.div variants={up} custom={2} className="mt-[16px] flex flex-wrap gap-[8px]">
            {top3.map(([state, n]) => (
              <span key={state} className="flex h-[36px] items-center whitespace-nowrap rounded-[18px] border border-line bg-surface px-[14px] text-[14px] text-muted">
                {state}&nbsp;<b className="font-semibold text-white">{fmt(n)}</b>
              </span>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* 03 Your district */}
      <motion.section {...inView} className="relative overflow-hidden px-[20px] pb-[48px] pt-[8px]">
        <div className="relative mx-auto" style={{ width: "min(78vw, 320px)", aspectRatio: `${NASHIK.width} / ${NASHIK.height}` }}>
          <div className="absolute -inset-[30%] rounded-full" style={{ background: "radial-gradient(closest-side, #F59E0B33, #F59E0B00)" }} />
          <svg className="absolute inset-0 h-full w-full overflow-visible" viewBox={`0 0 ${NASHIK.width} ${NASHIK.height}`}>
            <motion.path d={NASHIK.path} stroke="#FBBF24" strokeWidth={3} strokeLinejoin="round" style={{ filter: "drop-shadow(0 0 7px #F59E0BAA)" }}
              variants={{ hidden: { pathLength: 0, fill: "rgba(245,158,11,0)" }, show: { pathLength: 1, fill: "rgba(245,158,11,0.16)", transition: { pathLength: { duration: 2, ease }, fill: { duration: 1, delay: 1.2 } } } }} />
            <motion.circle cx={NASHIK.city[0]} cy={NASHIK.city[1]} r={9} fill="#F59E0B"
              variants={{ hidden: { opacity: 0, scale: 0 }, show: { opacity: 1, scale: 1, transition: { type: "spring", bounce: 0.5, delay: 1.4 } } }} />
          </svg>
        </div>
        <motion.h2 variants={up} custom={1} className="mt-[24px] text-[36px] font-bold leading-[42px]">
          {risk ? <>{risk.district_name},<br />{risk.state_name}</> : <>&nbsp;<br />&nbsp;</>}
        </motion.h2>
        <motion.span variants={up} custom={2} className="mt-[14px] inline-flex h-[34px] items-center rounded-[17px] px-[14px] text-[14px] font-semibold"
          style={{ color: col, background: `${col}24`, border: `1px solid ${col}E6` }}>
          {cls ? RISK_BADGE[cls] ?? cls : "No forecast yet"}
        </motion.span>
        <motion.div variants={up} custom={3} className="mt-[8px] flex items-center">
          <span className="text-[80px] font-bold leading-[88px]" style={{ color: col }}><CountUp to={pct} suffix="%" /></span>
          <span className="ml-[14px] text-[18px] font-semibold leading-[24px]">chance of<br />wildfire {risk ? forecastWhen(risk.date) : "today"}</span>
        </motion.div>
        <motion.div variants={up} custom={4} className="mt-[16px] grid grid-cols-2 gap-[12px]">
          {[
            { l: "Air quality", i: "wind" as IconName, v: aq?.aqi ?? null, s: aq?.aqi_category ?? "–", c: aqCol, sc: aqCol },
            { l: "Fires nearby", i: "flame" as IconName, v: fires30, s: "in 30 days", c: "#FFFFFF", sc: "#9AA3B2" },
          ].map((t) => (
            <div key={t.l} className="relative rounded-[16px] border border-line bg-surface p-[16px]">
              <span className="flex items-center gap-[6px] text-[13px] text-muted">{t.l}{t.l === "Air quality" && (
                <span title="Satellite-model estimate (Copernicus CAMS, CPCB formula, last 24 h), not a ground station reading" className="rounded-full border border-amber/60 px-[6px] py-[1px] text-[10px] font-semibold uppercase tracking-wide text-amber">Estimate</span>
              )}</span>
              <Icon name={t.i} size={18} color="#9AA3B2" className="absolute right-[14px] top-[16px]" />
              <span className="mt-[6px] block text-[36px] font-bold leading-[44px]" style={{ color: t.c }}><CountUp to={t.v} /></span>
              <span className={`block text-[13px] ${t.sc === "#9AA3B2" ? "" : "font-semibold"}`} style={{ color: t.sc }}>{t.s}</span>
            </div>
          ))}
        </motion.div>
        {risk && (
          <motion.a variants={up} custom={5} href={`/district/${risk.region_id}`}
            className="mt-[16px] flex h-[50px] items-center justify-center rounded-[14px] border border-line bg-surface text-[15px] font-semibold hover:border-ember/60">
            Open full details
          </motion.a>
        )}
      </motion.section>

      {/* 04 Why today + Stay safe */}
      <motion.section {...inView} className="px-[20px] pb-[40px]">
        <motion.h2 variants={up} custom={0} className="text-[32px] font-bold leading-[38px]">Why today?</motion.h2>
        <motion.p variants={up} custom={1} className="mt-[6px] text-[15px] text-muted">What is pushing the forecast for {risk?.district_name ?? "your district"}</motion.p>
        <div className="mt-[16px] space-y-[16px]">
          {factors.map((f, j) => (
            <motion.div key={f.feature} variants={up} custom={2 + j}>
              <p className="text-[15px] font-semibold">{FACTOR_LABELS[f.feature] ?? f.label}</p>
              <div className="mt-[8px] h-[10px] rounded-full bg-line">
                <motion.div className="h-full rounded-full" style={{ background: "linear-gradient(90deg, #C2410C, #F97316)", boxShadow: "0 0 12px #F9731699" }}
                  variants={{ hidden: { width: 0 }, show: { width: `${fracs[j] * 100}%`, transition: { duration: 1.1, ease, delay: 0.4 + j * 0.12 } } }} />
              </div>
            </motion.div>
          ))}
        </div>

        <motion.h3 variants={up} custom={5} className="mt-[36px] text-[22px] font-semibold">Stay safe</motion.h3>
        <div className="mt-[12px] space-y-[12px]">
          {SAFETY.map((c, j) => (
            <motion.a key={c.stage} href={`/stay-safe?stage=${c.stage}`} variants={up} custom={6 + j}
              className="flex h-[76px] items-center gap-[16px] rounded-[16px] border border-line bg-surface px-[18px] active:border-ember/60">
              <span className="flex h-[44px] w-[44px] items-center justify-center rounded-full" style={{ background: "radial-gradient(closest-side, #F9731638, #F9731600)" }}>
                <Icon name={c.icon} size={26} color="#F97316" strokeWidth={2} />
              </span>
              <span className="flex-1 text-[17px] font-semibold">{c.title}</span>
              <span className="text-[14px] text-muted">Read guide</span>
            </motion.a>
          ))}
        </div>

        <div className="mt-[36px] h-px bg-line" />
        <p className="mt-[16px] text-center text-[12px] leading-[18px] text-muted">
          {risk ? `Forecast for ${dayLabel(risk.date)} · ` : ""}Academic decision-support tool, not an official warning. Consult IMD, CPCB, NDMA and local authorities.
        </p>
      </motion.section>
    </div>
  );
}
