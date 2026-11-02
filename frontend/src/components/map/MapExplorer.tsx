"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import * as maplibregl from "maplibre-gl";
type MLMap = maplibregl.Map; type GeoJSONSource = maplibregl.GeoJSONSource;
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import { CountUp } from "@/components/CountUp";
import {
  getJSON, shortTime, RISK_COLORS, RISK_BADGE, NO_DATA, FACTOR_LABELS,
  type Risk, type AirQuality, type RiskMap, type Region,
} from "@/lib/api";
import { BASEMAP, INDIA_BOUNDS, bbox } from "./geo";

const ease = [0.16, 1, 0.3, 1] as const;
const COLOR_EXPR = ["match", ["coalesce", ["get", "risk_class"], "none"],
  "Low", RISK_COLORS.Low, "Moderate", RISK_COLORS.Moderate, "High", RISK_COLORS.High, "Extreme", RISK_COLORS.Extreme, NO_DATA,
] as unknown as maplibregl.ExpressionSpecification;
const PANEL_W = 416, PANEL_GAP = 24;
const BAR_FRACS = [0.86, 0.66, 0.52];

type Town = { name: string; state: string; district: string; lat: number; lon: number; display_name?: string };
type Place = { name: string; lat: number; lon: number } | null;
/** "…, Bhusawal, Jalgaon, Maharashtra, 425307, India" -> "Jalgaon" (the part just before the state) */
function townDistrict(t: Town) {
  const parts = (t.display_name || "").split(",").map((x) => x.trim());
  const i = parts.lastIndexOf(t.state);
  return i > 0 ? parts[i - 1] : t.district;
}

type Hover = { x: number; y: number; name: string; cls: string | null } | null;

export default function MapExplorer({ initialId, bare = false }: { initialId?: number; bare?: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const [ready, setReady] = useState(false);
  const [points, setPoints] = useState<RiskMap | null>(null);
  const [place, setPlace] = useState<Place>(null);
  const [hover, setHover] = useState<Hover>(null);
  const [sel, setSel] = useState<number | null>(initialId ?? null);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [aq, setAq] = useState<AirQuality | null>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [noGL, setNoGL] = useState(false);

  // map
  useEffect(() => {
    if (!box.current) return;
    let map: MLMap;
    try {
      map = new maplibregl.Map({
      container: box.current, style: BASEMAP, bounds: INDIA_BOUNDS,
      fitBoundsOptions: { padding: { top: 120, bottom: 40, left: 40, right: 40 } },
      attributionControl: false, dragRotate: false, pitchWithRotate: false,
    });
    } catch {
      setNoGL(true); // no WebGL in this browser
      return;
    }
    map.touchZoomRotate.disableRotation();
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");
    mapRef.current = map;
    if (bare) (window as unknown as { __map: MLMap }).__map = map; // screenshot tooling
    map.on("load", () => {
      map.addSource("districts", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("boundary", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "boundary-fill", type: "fill", source: "boundary", paint: { "fill-color": ["get", "color"], "fill-opacity": 0.16 } });
      map.addLayer({ id: "boundary-glow", type: "line", source: "boundary", paint: { "line-color": ["get", "color"], "line-width": 10, "line-blur": 9, "line-opacity": 0.7 } });
      map.addSource("place", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "boundary-line", type: "line", source: "boundary", paint: { "line-color": ["get", "stroke"], "line-width": 2.5 }, layout: { "line-join": "round" } });
      map.addLayer({ id: "dots-glow", type: "circle", source: "districts", paint: {
        "circle-color": COLOR_EXPR, "circle-blur": 1, "circle-opacity": 0.55,
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 9, 6, 16, 9, 26],
      } });
      map.addLayer({ id: "dots", type: "circle", source: "districts", paint: {
        "circle-color": COLOR_EXPR,
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3.5, 6, 6, 9, 9],
        "circle-stroke-color": "#0B0D12", "circle-stroke-width": 1,
        "circle-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.35, 1],
      } });
      map.addLayer({ id: "place-halo", type: "circle", source: "place", paint: { "circle-color": "#F97316", "circle-radius": 18, "circle-blur": 0.8, "circle-opacity": 0.6 } });
      map.addLayer({ id: "place-pin", type: "circle", source: "place", paint: { "circle-color": "#FFFFFF", "circle-radius": 7, "circle-stroke-color": "#F97316", "circle-stroke-width": 3 } });
      map.addLayer({ id: "place-label", type: "symbol", source: "place",
        layout: { "text-field": ["get", "name"], "text-font": ["Montserrat SemiBold", "Open Sans Bold", "Noto Sans Regular"], "text-size": 14, "text-offset": [0, 1.5], "text-anchor": "top" },
        paint: { "text-color": "#FFFFFF", "text-halo-color": "#0B0D12", "text-halo-width": 2 } });
      map.on("mousemove", "dots", (e) => {
        const f = e.features?.[0]; if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        setHover({ x: e.point.x, y: e.point.y, name: String(f.properties.district_name), cls: (f.properties.risk_class as string) || null });
      });
      map.on("mouseleave", "dots", () => { map.getCanvas().style.cursor = ""; setHover(null); });
      map.on("click", "dots", (e) => { const f = e.features?.[0]; if (f) { setPlace(null); setSel(Number(f.properties.region_id)); } });
      setReady(true);
    });
    return () => { map.remove(); mapRef.current = null; };
  }, [bare]);

  // data
  useEffect(() => { getJSON<RiskMap>("/risk/map").then(setPoints).catch(() => {}); }, []);
  useEffect(() => {
    if (!ready || !points) return;
    (mapRef.current!.getSource("districts") as GeoJSONSource).setData(points as unknown as GeoJSON.FeatureCollection);
  }, [ready, points]);

  // town pin
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("place") as GeoJSONSource).setData(place
      ? { type: "Feature", geometry: { type: "Point", coordinates: [place.lon, place.lat] }, properties: { name: place.name } }
      : { type: "FeatureCollection", features: [] });
  }, [place, ready]);

  // selection
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const url = new URL(window.location.href);
    if (sel == null) {
      url.searchParams.delete("d"); window.history.replaceState(null, "", url);
      (map.getSource("boundary") as GeoJSONSource).setData({ type: "FeatureCollection", features: [] });
      setRisk(null); setAq(null);
      map.fitBounds(INDIA_BOUNDS, { padding: { top: 120, bottom: 40, left: 40, right: 40 }, duration: 1800, essential: true });
      return;
    }
    url.searchParams.set("d", String(sel)); window.history.replaceState(null, "", url);
    let alive = true;
    setRisk(null); setAq(null);
    getJSON<Risk>(`/risk/${sel}`).then((r) => alive && setRisk(r)).catch(() => {});
    getJSON<AirQuality>(`/air-quality/${sel}`).then((a) => alive && setAq(a)).catch(() => {});
    getJSON<Region>(`/regions/${sel}`).then((reg) => {
      if (!alive) return;
      const cls = points?.features.find((f) => f.properties.region_id === sel)?.properties.risk_class;
      const color = (cls && RISK_COLORS[cls]) || NO_DATA;
      (map.getSource("boundary") as GeoJSONSource).setData({ type: "Feature", geometry: reg.geom, properties: { color, stroke: cls === "Moderate" ? "#FBBF24" : color } });
      map.fitBounds(bbox(reg.geom), {
        padding: { top: 140, bottom: 80, left: 120, right: PANEL_W + PANEL_GAP + 120 }, duration: 2400, curve: 1.6, essential: true, maxZoom: 9,
      });
    }).catch(() => {});
    return () => { alive = false; };
  }, [sel, ready, points]);

  const matches = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!points || s.length < 2) return [];
    return points.features.filter((f) => f.properties.district_name.toLowerCase().includes(s)).slice(0, 6);
  }, [q, points]);

  // Towns / cities: backend geocoder, debounced; town -> parent district via /regions/by-coordinates
  const [towns, setTowns] = useState<Town[]>([]);
  const [searching, setSearching] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [searchErr, setSearchErr] = useState<string | null>(null);
  useEffect(() => {
    const s = q.trim();
    setSearchErr(null);
    if (s.length < 2) { setTowns([]); setSearching(false); return; }
    let alive = true; setSearching(true);
    const t = setTimeout(() => {
      getJSON<Town[]>(`/geo/cities?q=${encodeURIComponent(s)}`)
        .then((r) => { if (alive) setTowns((r || []).slice(0, 5)); })
        .catch(() => { if (alive) setTowns([]); })
        .finally(() => { if (alive) setSearching(false); });
    }, 350);
    return () => { alive = false; clearTimeout(t); };
  }, [q]);

  const pick = useCallback((id: number, pl: Place = null) => { setPlace(pl); setSel(id); setQ(""); setOpen(false); setSearchErr(null); }, []);
  const pickTown = useCallback((t: Town) => {
    setResolving(true); setSearchErr(null);
    getJSON<{ id: number }>(`/regions/by-coordinates?lat=${t.lat}&lon=${t.lon}`)
      .then((r) => { if (r?.id) pick(r.id, { name: t.name, lat: t.lat, lon: t.lon }); else setSearchErr("This place is outside our districts."); })
      .catch(() => setSearchErr("This place is outside our districts."))
      .finally(() => setResolving(false));
  }, [pick]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div className="absolute inset-0"><div ref={box} style={{ width: "100%", height: "100%" }} /></div>
      {noGL && (
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[16px] border border-line bg-surface px-6 py-4 text-center text-[15px] text-muted">
          This browser can&apos;t show the map (WebGL is off). Try Chrome, Edge or Firefox.
        </div>
      )}
      {!bare && (
        <>
          {/* Search / Back */}
          <AnimatePresence mode="wait">
            {sel == null ? (
              <motion.div key="search" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                className="absolute" style={{ left: 32, top: 104, width: 400 }}>
                <label className="relative flex h-[56px] items-center rounded-[16px] border border-line bg-surface focus-within:border-ember/60">
                  <input value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} placeholder="Search district or town" aria-label="Search district or town"
                    onKeyDown={(e) => { if (e.key !== "Enter") return; if (matches[0]) pick(matches[0].properties.region_id); else if (towns[0]) pickTown(towns[0]); }}
                    className="h-full w-full bg-transparent pl-[20px] pr-[56px] text-[18px] text-white outline-none placeholder:text-muted" />
                  <Icon name="search" size={22} color="#9AA3B2" className="absolute" style={{ left: 360, top: 16 }} />
                </label>
                {open && q.trim().length >= 2 && (
                  <ul className="mt-2 max-h-[420px] overflow-y-auto rounded-[16px] border border-line bg-surface">
                    {matches.map((m) => (
                      <li key={m.properties.region_id}>
                        <button onClick={() => pick(m.properties.region_id)} className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-white/5">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: (m.properties.risk_class && RISK_COLORS[m.properties.risk_class]) || NO_DATA }} />
                          <span className="text-[15px]">{m.properties.district_name}</span>
                          <span className="text-[13px] text-muted">{m.properties.state_name}</span>
                        </button>
                      </li>
                    ))}
                    {towns.map((t, i) => (
                      <li key={`t${i}`}>
                        <button onClick={() => pickTown(t)} disabled={resolving} className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-white/5 disabled:opacity-60">
                          <Icon name="pin" size={14} color="#9AA3B2" />
                          <span className="text-[15px]">{t.name}</span>
                          <span className="truncate text-[13px] text-muted">{townDistrict(t)} district, {t.state}</span>
                        </button>
                      </li>
                    ))}
                    {(searching || resolving) && <li className="px-5 py-3 text-[14px] text-muted">{resolving ? "Finding the district…" : "Searching towns…"}</li>}
                    {searchErr && <li className="px-5 py-3 text-[14px] text-muted">{searchErr}</li>}
                    {!searching && !resolving && !searchErr && matches.length === 0 && towns.length === 0 && (
                      <li className="px-5 py-3 text-[14px] text-muted">No district or town found for “{q.trim()}”. Try another spelling.</li>
                    )}
                  </ul>
                )}
              </motion.div>
            ) : (
              <motion.button key="back" onClick={() => { setPlace(null); setSel(null); }} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
                className="absolute flex h-[40px] items-center gap-[8px] rounded-[20px] border border-line bg-surface/90 pl-[14px] pr-[18px] text-[15px] backdrop-blur-md hover:border-ember/60"
                style={{ left: 32, top: 104 }}>
                <Icon name="arrow-left" size={16} />Back to India
              </motion.button>
            )}
          </AnimatePresence>

          {/* Legend */}
          <AnimatePresence>
            {sel == null && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}
                className="absolute rounded-[16px] border border-line bg-surface" style={{ left: 32, bottom: 72, width: 168, padding: 20 }}>
                <p className="text-[15px] font-semibold leading-[20px]">Risk today</p>
                {["Low", "Moderate", "High", "Extreme"].map((c) => (
                  <p key={c} className="mt-[8px] flex items-center gap-[10px] text-[15px] leading-[20px]">
                    <span className="h-[10px] w-[10px] rounded-full" style={{ background: RISK_COLORS[c], boxShadow: `0 0 8px ${RISK_COLORS[c]}` }} />{c}
                  </p>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Zoom */}
          <div className="absolute flex flex-col overflow-hidden rounded-[12px] border border-line bg-surface"
            style={{ right: sel == null ? 32 : PANEL_W + PANEL_GAP + 24, bottom: 32, transition: "right .5s" }}>
            <button aria-label="Zoom in" onClick={() => mapRef.current?.zoomIn()} className="h-[40px] w-[40px] text-[20px] hover:bg-white/5">+</button>
            <span className="h-px bg-line" />
            <button aria-label="Zoom out" onClick={() => mapRef.current?.zoomOut()} className="h-[40px] w-[40px] text-[20px] hover:bg-white/5">−</button>
          </div>

          {/* Tooltip */}
          {hover && (
            <div className="pointer-events-none absolute whitespace-nowrap rounded-[10px] border border-line bg-surface px-[12px] py-[7px] text-[13px] font-semibold shadow-lg"
              style={{ left: hover.x + 14, top: hover.y - 18 }}>
              {hover.name} · <span style={{ color: (hover.cls && RISK_COLORS[hover.cls]) || NO_DATA }}>{hover.cls ?? "No forecast"}</span>
            </div>
          )}

          {/* Panel */}
          <AnimatePresence>
            {sel != null && <Panel key={sel} risk={risk} aq={aq} place={place} />}
          </AnimatePresence>

          {!points && (
            <div className="absolute left-1/2 top-[120px] -translate-x-1/2 rounded-full border border-line bg-surface px-4 py-2 text-[13px] text-muted">
              Loading today&apos;s forecast… (server may take ~30s to wake)
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Panel({ risk, aq, place }: { risk: Risk | null; aq: AirQuality | null; place: Place }) {
  const cls = risk?.risk_class;
  const col = (cls && RISK_COLORS[cls]) || NO_DATA;
  const aqCol = (aq?.aqi_category && RISK_COLORS[aq.aqi_category]) || "#F59E0B";
  const fires30 = risk?.top_factors.find((f) => f.feature === "fires_prev_30d")?.value ?? null;
  return (
    <motion.aside initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0, transition: { duration: 0.7, ease, delay: 0.5 } }} exit={{ opacity: 0, x: 40, transition: { duration: 0.3 } }}
      className="absolute overflow-y-auto rounded-[16px] border border-line bg-surface"
      style={{ right: PANEL_GAP, top: 96, bottom: PANEL_GAP, width: PANEL_W, padding: 32 }}>
      {!risk ? (
        <div className="space-y-4">
          <div className="h-[96px] w-[260px] animate-pulse rounded-lg bg-white/5" />
          <div className="h-[32px] w-[180px] animate-pulse rounded-full bg-white/5" />
          <div className="h-[96px] w-[200px] animate-pulse rounded-lg bg-white/5" />
        </div>
      ) : (
        <>
          {place ? (
            <>
              <h2 className="text-[40px] font-bold leading-[48px]">{place.name}</h2>
              <p className="mt-[6px] text-[16px] leading-[22px] text-muted">in {risk.district_name} district, {risk.state_name}</p>
              <p className="mt-[4px] text-[13px] leading-[18px] text-muted">Forecast is for the whole district.</p>
            </>
          ) : (
            <h2 className="text-[40px] font-bold leading-[48px]">{risk.district_name},<br />{risk.state_name}</h2>
          )}
          <span className="mt-[16px] inline-flex h-[32px] items-center rounded-[16px] px-[14px] text-[13px] font-semibold"
            style={{ color: col, background: `${col}24`, border: `1px solid ${col}E6` }}>{RISK_BADGE[cls!] ?? "No forecast yet"}</span>
          <div className="mt-[16px] flex items-center">
            <span className="text-[88px] font-bold leading-[96px]" style={{ color: col }}><CountUp to={Math.round(risk.probability * 100)} suffix="%" /></span>
            <span className="ml-[16px] text-[18px] font-semibold leading-[24px]">chance of<br />wildfire today</span>
          </div>
          <div className="mt-[20px] grid grid-cols-2 gap-[16px]">
            {[
              { l: "Air quality", i: "wind" as const, v: aq?.aqi ?? null, s: aq?.aqi_category ?? "–", c: aqCol, sc: aqCol },
              { l: "Fires nearby", i: "flame" as const, v: fires30, s: "in 30 days", c: "#FFFFFF", sc: "#9AA3B2" },
            ].map((t) => (
              <div key={t.l} className="relative h-[120px] rounded-[16px] border border-line bg-bg/60">
                <span className="absolute left-[16px] top-[16px] text-[13px] leading-[normal] text-muted">{t.l}</span>
                <Icon name={t.i} size={18} color="#9AA3B2" className="absolute left-[134px] top-[16px]" />
                <span className="absolute left-[16px] top-[38px] text-[36px] font-bold leading-[44px]" style={{ color: t.c }}><CountUp to={t.v} /></span>
                <span className={`absolute left-[16px] top-[82px] text-[13px] leading-[normal] ${t.sc === "#9AA3B2" ? "" : "font-semibold"}`} style={{ color: t.sc }}>{t.s}</span>
              </div>
            ))}
          </div>
          <h3 className="mt-[28px] text-[24px] font-semibold leading-[32px]">Why today?</h3>
          <div className="mt-[12px] space-y-[14px]">
            {risk.top_factors.slice(0, 3).map((f, j) => (
              <div key={f.feature}>
                <p className="text-[15px] font-semibold leading-[20px]">{FACTOR_LABELS[f.feature] ?? f.label}</p>
                <div className="mt-[8px] h-[8px] rounded-full bg-line">
                  <motion.div className="h-full rounded-full" initial={{ width: 0 }} animate={{ width: `${BAR_FRACS[j] * 100}%` }}
                    transition={{ duration: 1.1, ease, delay: 0.9 + j * 0.12 }}
                    style={{ background: "linear-gradient(90deg, #C2410C, #F97316)", boxShadow: "0 0 12px #F9731699" }} />
                </div>
              </div>
            ))}
          </div>
          <a href={`#district-${risk.region_id}`} className="mt-[28px] flex h-[52px] items-center justify-center rounded-[14px] bg-ember text-[16px] font-semibold text-white shadow-[0_0_24px_#F9731655] transition hover:brightness-110">
            Open full details
          </a>
          <p className="mt-[16px] text-[12px] leading-[16px] text-muted" title={risk.disclaimer_short}>Updated {shortTime(risk.as_of.ist)} · Not an official warning.</p>
        </>
      )}
    </motion.aside>
  );
}
