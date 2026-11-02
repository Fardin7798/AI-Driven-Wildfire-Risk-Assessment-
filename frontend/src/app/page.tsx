"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useScroll, useTransform, type Variants } from "framer-motion";
import { Nav } from "@/components/Nav";
import { Icon, type IconName } from "@/components/Icon";
import { CountUp } from "@/components/CountUp";
import { NASHIK } from "@/lib/nashik-outline";
import {
  getJSON, shortTime, fmt, RISK_COLORS, RISK_BADGE, NO_DATA, FACTOR_LABELS,
  type Risk, type AirQuality, type FireStats,
} from "@/lib/api";

const REGION_ID = 369; // Nashik (default district until search / location is wired)
const ease = [0.16, 1, 0.3, 1] as const;
const up: Variants = { hidden: { opacity: 0, y: 24 }, show: (i: number = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.8, ease, delay: i * 0.12 } }) };
const radial = (hex: string, a: number) => `radial-gradient(closest-side, ${hex}${Math.round(a * 255).toString(16).padStart(2, "0")}, ${hex}00)`;

function useStageZoom() {
  useEffect(() => {
    const set = () => document.documentElement.style.setProperty("--z", String(Math.min(window.innerWidth / 1440, 1.6)));
    set(); window.addEventListener("resize", set);
    return () => window.removeEventListener("resize", set);
  }, []);
}

export default function Home() {
  useStageZoom();
  const [risk, setRisk] = useState<Risk | null>(null);
  const [aq, setAq] = useState<AirQuality | null>(null);
  const [fires, setFires] = useState<FireStats | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    getJSON<Risk>(`/risk/${REGION_ID}`).then(setRisk).catch(() => setErr(true));
    getJSON<AirQuality>(`/air-quality/${REGION_ID}`).then(setAq).catch(() => setErr(true));
    getJSON<FireStats>(`/fires/stats?days=7`).then(setFires).catch(() => setErr(true));
  }, []);

  return (
    <main style={{ zoom: "var(--z, 1)" } as React.CSSProperties}>
      <Nav active="" />
      <Hero />
      <FiresThisWeek fires={fires} />
      <YourDistrict risk={risk} aq={aq} />
      <WhyToday risk={risk} />
      {err && (
        <div className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-full border border-line bg-surface px-4 py-2 text-[13px] text-muted">
          Some live data could not load. Retrying when you refresh.
        </div>
      )}
    </main>
  );
}

/* ---------------- 01 Hero ---------------- */
function Hero() {
  const [homeQ, setHomeQ] = useState("");
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  // Scroll story: the globe pushes in towards India and fades as the next section arrives.
  const scale = useTransform(scrollYProgress, [0, 1], [1, 2.1]);
  const x = useTransform(scrollYProgress, [0, 1], [0, 260]);
  const y = useTransform(scrollYProgress, [0, 1], [0, 120]);
  const opacity = useTransform(scrollYProgress, [0.55, 1], [1, 0]);
  const textY = useTransform(scrollYProgress, [0, 1], [0, -120]);

  return (
    <section ref={ref} className="relative overflow-hidden">
      <div className="relative mx-auto h-[900px] w-[1440px]">
        <motion.div className="absolute" style={{ left: 0, top: 82, width: 820, height: 820, scale, x, y, opacity, transformOrigin: "52% 50%" }}>
          <div className="absolute" style={{ left: 120, top: 178, width: 640, height: 520, background: radial("#F97316", 0.1), borderRadius: "50%" }} />
          <motion.img src="/img/globe.png" alt="Earth at night with India glowing" width={820} height={820}
            className="absolute inset-0 select-none" draggable={false}
            initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1.4, ease }} />
        </motion.div>

        <motion.div style={{ y: textY }}>
          <motion.h1 variants={up} initial="hidden" animate="show" custom={0}
            className="absolute text-[72px] font-bold leading-[80px]" style={{ left: 840, top: 250 }}>
            Know your<br />wildfire risk.
          </motion.h1>
          <motion.p variants={up} initial="hidden" animate="show" custom={1}
            className="absolute text-[18px] leading-[28px]" style={{ left: 840, top: 438, color: "rgba(255,255,255,0.82)" }}>
            AI forecast for every district in India,<br />updated daily.
          </motion.p>
          <motion.form variants={up} initial="hidden" animate="show" custom={2}
            action="/map" method="get" role="search"
            onSubmit={(e) => { e.preventDefault(); const v = homeQ.trim(); window.location.href = v.length >= 2 ? `/map?q=${encodeURIComponent(v)}` : "/map"; }}
            className="absolute flex items-center rounded-[16px] border border-line bg-surface transition-colors focus-within:border-ember/60"
            style={{ left: 840, top: 528, width: 540, height: 56 }}>
            <input name="q" value={homeQ} onChange={(e) => setHomeQ(e.target.value)}
              placeholder="Search district or town" aria-label="Search district or town" autoComplete="off"
              className="h-full w-full bg-transparent pl-[20px] pr-[60px] text-[18px] text-white outline-none placeholder:text-muted" />
            <button type="submit" aria-label="Search" className="absolute flex items-center justify-center rounded-[12px] hover:bg-white/10"
              style={{ left: 488, top: 6, width: 44, height: 44 }}>
              <Icon name="search" size={22} color="#9AA3B2" />
            </button>
          </motion.form>
          <motion.a href="#fires" variants={up} initial="hidden" animate="show" custom={3}
            className="absolute flex items-center" style={{ left: 840, top: 792, height: 40 }}>
            <span className="absolute rounded-full border border-line bg-surface" style={{ left: 0, top: 4, width: 32, height: 32 }} />
            <motion.span className="absolute" style={{ left: 8, top: 12 }} animate={{ y: [0, 4, 0] }} transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}>
              <Icon name="arrow-down" size={16} />
            </motion.span>
            <span className="absolute whitespace-nowrap text-[15px] leading-[normal]" style={{ left: 44, top: 10, color: "rgba(255,255,255,0.85)" }}>Scroll to explore</span>
          </motion.a>
        </motion.div>
      </div>
    </section>
  );
}

/* ---------------- 02 Fires this week ---------------- */
function FiresThisWeek({ fires }: { fires: FireStats | null }) {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "start start"] });
  const imgScale = useTransform(scrollYProgress, [0, 1], [1.35, 1]);
  const top3 = fires ? Object.entries(fires.by_state).sort((a, b) => b[1] - a[1]).slice(0, 3) : [];

  return (
    <section id="fires" ref={ref} className="relative overflow-hidden">
      <div className="relative mx-auto h-[900px] w-[1440px]">
        <motion.img src="/img/india-night.png" alt="Satellite fire detections over India" className="absolute max-w-none select-none"
          draggable={false} style={{ left: 60, top: 40, width: 1600, height: 893, scale: imgScale, transformOrigin: "40% 40%" }} />
        <div className="absolute" style={{ left: 0, top: 0, width: 1000, height: 900, background: "linear-gradient(90deg, #0B0D12 0%, #0B0D12E0 30%, #0B0D1266 65%, #0B0D1200 100%)" }} />
        <div className="absolute" style={{ left: 0, top: 560, width: 1440, height: 340, background: "linear-gradient(180deg, #0B0D1200 0%, #0B0D12E6 100%)" }} />
        <div className="absolute" style={{ left: 0, top: 72, width: 1440, height: 120, background: "linear-gradient(180deg, #0B0D12D9 0%, #0B0D1200 100%)" }} />

        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.5 }}>
          <motion.div variants={up} custom={0} className="absolute text-[120px] font-bold leading-[128px]" style={{ left: 68, top: 572 }}>
            <CountUp to={fires?.total_detections ?? null} duration={2} />
          </motion.div>
          <motion.p variants={up} custom={1} className="absolute whitespace-nowrap text-[24px] leading-[normal]" style={{ left: 72, top: 708, color: "rgba(255,255,255,0.9)" }}>
            fires spotted by satellites this week
          </motion.p>
          <motion.div key={top3.length} initial="hidden" animate="show" className="absolute flex gap-[12px]" style={{ left: 72, top: 772 }}>
            {top3.map(([state, n], i) => (
              <motion.span key={state} variants={up} custom={2 + i}
                className="flex h-[40px] items-center whitespace-nowrap rounded-[20px] border border-line bg-surface pl-[16px] pr-[24px] text-[15px] text-muted">
                {state}&nbsp;<b className="font-semibold text-white">{fmt(n)}</b>
              </motion.span>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

/* ---------------- 03 Your district ---------------- */
function YourDistrict({ risk, aq }: { risk: Risk | null; aq: AirQuality | null }) {
  const MX = 90, MY = 72 + (828 - NASHIK.height) / 2;
  const px = MX + NASHIK.city[0], py = MY + NASHIK.city[1];
  const cls = risk?.risk_class;
  const col = cls ? RISK_COLORS[cls] ?? NO_DATA : NO_DATA;
  const aqCol = aq?.aqi_category ? RISK_COLORS[aq.aqi_category] ?? "#F59E0B" : "#F59E0B";
  const fires30 = risk?.top_factors.find((f) => f.feature === "fires_prev_30d")?.value ?? null;
  const pct = risk ? Math.round(risk.probability * 100) : null;
  const pin = "M12 21 C12 21 19 14.5 19 9.5 A7 7 0 0 0 5 9.5 C5 14.5 12 21 12 21 Z";

  return (
    <section className="relative overflow-hidden">
      <motion.div className="relative mx-auto h-[900px] w-[1440px]" initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.45 }}>
        <motion.div variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { duration: 1.2 } } }} className="absolute"
          style={{ left: MX - 120, top: MY - 140, width: NASHIK.width + 240, height: NASHIK.height + 280, background: radial("#F59E0B", 0.2), borderRadius: "50%" }} />
        <svg className="absolute overflow-visible" style={{ left: MX, top: MY }} width={NASHIK.width} height={NASHIK.height}>
          <defs><filter id="blur18" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="9" /></filter></defs>
          <motion.path d={NASHIK.path} fill="none" stroke="#F59E0B" strokeWidth={10} opacity={0.7} filter="url(#blur18)"
            variants={{ hidden: { pathLength: 0 }, show: { pathLength: 1, transition: { duration: 2.2, ease } } }} />
          <motion.path d={NASHIK.path} stroke="#FBBF24" strokeWidth={2.5} strokeLinejoin="round"
            style={{ filter: "drop-shadow(0 0 7px #F59E0BAA)" }}
            variants={{ hidden: { pathLength: 0, fill: "rgba(245,158,11,0)" }, show: { pathLength: 1, fill: "rgba(245,158,11,0.16)", transition: { pathLength: { duration: 2.2, ease }, fill: { duration: 1, delay: 1.4 } } } }} />
        </svg>
        <motion.div className="absolute" style={{ left: px - 22, top: py - 9, width: 44, height: 18, background: radial("#F59E0B", 0.55), borderRadius: "50%" }}
          animate={{ scale: [1, 1.5, 1], opacity: [0.9, 0.4, 0.9] }} transition={{ duration: 2, repeat: Infinity }} />
        <motion.svg className="absolute" style={{ left: px - 19.2, top: py - 33.6, filter: "drop-shadow(0 2px 3px #00000066)" }} width={38.4} height={38.4} viewBox="0 0 24 24"
          variants={{ hidden: { y: -40, opacity: 0 }, show: { y: 0, opacity: 1, transition: { type: "spring", bounce: 0.5, delay: 1.6 } } }}>
          <path d={pin} fill="#F59E0B" stroke="#F59E0B" strokeWidth={1.5 / 1.6} strokeLinejoin="round" />
          <circle cx={12} cy={9.5} r={4.5 / 1.6} fill="#0B0D12" />
        </motion.svg>
        <motion.span variants={up} custom={14} className="absolute text-[15px] font-semibold leading-[normal]" style={{ left: px + 26, top: py - 44, color: "#FDE68A" }}>
          {risk?.district_name ?? "Nashik"}
        </motion.span>

        <motion.h2 variants={up} custom={0} className="absolute text-[72px] font-bold leading-[80px]" style={{ left: 820, top: 160 }}>
          {risk ? <>{risk.district_name},<br />{risk.state_name}</> : <>&nbsp;<br />&nbsp;</>}
        </motion.h2>
        <motion.span variants={up} custom={1} className="absolute flex h-[36px] items-center whitespace-nowrap rounded-[18px] px-[16px] text-[15px] font-semibold"
          style={{ left: 820, top: 352, color: col, background: `${col}24`, border: `1px solid ${col}E6` }}>
          {cls ? RISK_BADGE[cls] ?? cls : "No forecast yet"}
        </motion.span>
        <motion.div variants={up} custom={2} className="absolute flex items-start" style={{ left: 816, top: 412 }}>
          <span className="text-[120px] font-bold leading-[128px]" style={{ color: col }}><CountUp to={pct} suffix="%" /></span>
          <span className="ml-[24px] mt-[36px] text-[24px] font-semibold leading-[32px]">chance of<br />wildfire today</span>
        </motion.div>
        <Tile i={3} x={820} label="Air quality" icon="wind" value={aq?.aqi ?? null} sub={aq?.aqi_category ?? "–"} vcol={aqCol} subcol={aqCol} />
        <Tile i={4} x={820 + 272 + 16} label="Fires nearby" icon="flame" value={fires30} sub="in 30 days" vcol="#FFFFFF" subcol="#9AA3B2" />
        <motion.p variants={up} custom={5} className="absolute text-[13px] leading-[normal] text-muted" style={{ left: 820, top: 772 }}>
          {risk ? `Updated ${shortTime(risk.as_of.ist)}` : "Loading today's forecast…"}
        </motion.p>
      </motion.div>
    </section>
  );
}

function Tile({ i, x, label, icon, value, sub, vcol, subcol }: { i: number; x: number; label: string; icon: IconName; value: number | null; sub: string; vcol: string; subcol: string }) {
  return (
    <motion.div variants={up} custom={i} whileHover={{ y: -4 }}
      className="absolute rounded-[16px] border border-line bg-surface" style={{ left: x, top: 584, width: 272, height: 156 }}>
      <span className="absolute flex items-center gap-[8px] text-[15px] leading-[normal] text-muted" style={{ left: 24, top: 24 }}>{label}{label === "Air quality" && (
        <span title="AQI model is still in training; values are provisional" className="rounded-full border border-amber/60 px-[7px] py-[1px] text-[11px] font-semibold uppercase tracking-wide text-amber">Beta</span>
      )}</span>
      <Icon name={icon} size={22} color="#9AA3B2" className="absolute" style={{ left: 224, top: 22 }} />
      <span className="absolute text-[44px] font-bold leading-[52px]" style={{ left: 24, top: 52, color: vcol }}><CountUp to={value} /></span>
      <span className={`absolute text-[15px] leading-[normal] ${subcol === "#9AA3B2" ? "" : "font-semibold"}`} style={{ left: 24, top: 110, color: subcol }}>{sub}</span>
    </motion.div>
  );
}

/* ---------------- 04 Why today + Stay safe ---------------- */
const BAR_FRACS = [0.86, 0.66, 0.52]; // rank-based lengths, as in the approved design
const SAFETY: { title: string; icon: IconName; stage: string }[] = [
  { title: "Before a fire", icon: "shield-house", stage: "before" },
  { title: "During a fire", icon: "flame", stage: "during" },
  { title: "After a fire", icon: "wind", stage: "after" },
];

function WhyToday({ risk }: { risk: Risk | null }) {
  const factors = risk?.top_factors.slice(0, 3) ?? [];
  return (
    <section className="relative overflow-hidden">
      <motion.div className="relative mx-auto h-[900px] w-[1440px]" initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.35 }}>
        <motion.h2 variants={up} custom={0} className="absolute text-[48px] font-bold leading-[56px]" style={{ left: 72, top: 128 }}>Why today?</motion.h2>
        <motion.p variants={up} custom={1} className="absolute text-[18px] leading-[normal] text-muted" style={{ left: 72, top: 192 }}>
          What is pushing the forecast for {risk?.district_name ?? "your district"}
        </motion.p>
        {factors.map((f, j) => (
          <div key={f.feature} className="absolute rounded-[24px] border border-line bg-surface" style={{ left: 72, top: 248 + j * 64, width: 1296, height: 48 }}>
            <motion.div className="absolute left-0 top-0 h-full rounded-[24px]"
              style={{ background: "linear-gradient(90deg, #C2410CF2 0%, #F97316BF 100%)", border: "1.5px solid #FB923C", boxShadow: "0 0 24px #F9731699, 0 0 6px #F9731655" }}
              variants={{ hidden: { width: 0 }, show: { width: Math.round(1296 * BAR_FRACS[j]), transition: { duration: 1.2, ease, delay: 0.3 + j * 0.15 } } }} />
            <motion.span variants={up} custom={2 + j} className="absolute whitespace-nowrap text-[16px] font-semibold leading-[normal]" style={{ left: 24, top: 14 }}>
              {FACTOR_LABELS[f.feature] ?? f.label}
            </motion.span>
          </div>
        ))}
        <motion.h3 variants={up} custom={4} className="absolute text-[24px] font-semibold leading-[normal]" style={{ left: 72, top: 470 }}>Stay safe</motion.h3>
        {SAFETY.map((c, j) => (
          <motion.a key={c.stage} href={`/stay-safe?stage=${c.stage}`} variants={up} custom={5 + j} whileHover={{ y: -6, borderColor: "#F9731666" }}
            className="absolute rounded-[16px] border border-line bg-surface" style={{ left: 72 + j * 440, top: 518, width: 416, height: 232 }}>
            <span className="absolute rounded-full" style={{ left: 168, top: 34, width: 80, height: 80, background: radial("#F97316", 0.22) }} />
            <Icon name={c.icon} size={44} color="#F97316" strokeWidth={2} className="absolute" style={{ left: 186, top: 52 }} />
            <span className="absolute text-center text-[24px] font-semibold leading-[normal]" style={{ left: 24, top: 140, width: 368 }}>{c.title}</span>
            <span className="absolute text-center text-[15px] leading-[normal] text-muted" style={{ left: 24, top: 182, width: 368 }}>Read guide</span>
          </motion.a>
        ))}
        <div className="absolute bg-line" style={{ left: 72, top: 808, width: 1296, height: 1 }} />
        <p className="absolute text-center text-[13px] leading-[normal] text-muted" style={{ left: 72, top: 836, width: 1296 }}>
          {risk ? `Updated ${shortTime(risk.as_of.ist)} · ` : ""}Academic decision-support tool, not an official warning. Consult IMD, CPCB, NDMA and local authorities.
        </p>
      </motion.div>
    </section>
  );
}
