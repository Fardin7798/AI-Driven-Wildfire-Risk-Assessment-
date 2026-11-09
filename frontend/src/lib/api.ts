// Backend client and shared display helpers for the WildfireRisk frontend.
// Backend: FastAPI, base /api/v1. Override with NEXT_PUBLIC_API_BASE.

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "https://wildfire-platform-api.onrender.com/api/v1").replace(/\/$/, "");

export async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path.startsWith("/") ? path : `/${path}`}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return (await r.json()) as T;
}

/* ---------- Types (match backend responses) ---------- */

export type RiskClass = "Low" | "Moderate" | "High" | "Extreme";

export type Factor = {
  feature: string;
  label: string;
  value: number | null;
  unit: string | null;
  impact: number;
  method?: string;
};

export type AsOf = { utc: string; ist: string };

export type Risk = {
  region_id: number;
  district_name: string;
  state_name: string;
  date: string;
  probability: number;
  risk_class: RiskClass | string;
  model_version: string | null;
  fwi_value: number | null;
  top_factors: Factor[];
  as_of: AsOf;
  disclaimer_short: string;
};

export type AirQuality = {
  region_id: number;
  district_name: string;
  state_name: string;
  observed_at_utc: string;
  pm25: number | null;
  pm10: number | null;
  no2: number | null;
  so2: number | null;
  co: number | null;
  o3: number | null;
  nh3: number | null;
  aqi: number | null;
  aqi_category: string | null;
  provider: string;
  [k: string]: unknown;
};

export type FireStats = {
  period_days: number;
  total_detections: number;
  high_confidence_count: number;
  total_radiative_power_mw?: number;
  outside_districts: number;
  by_source: Record<string, number>;
  by_state: Record<string, number>;
  time_range_hours?: number;
};

export type RiskMapProps = {
  region_id: number;
  district_name: string;
  state_name: string;
  date: string;
  probability: number | null;
  risk_class: string | null;
  fwi_value: number | null;
  model_version: string | null;
  has_prediction: boolean;
};

export type RiskMap = GeoJSON.FeatureCollection<GeoJSON.Point, RiskMapProps>;

export type Region = {
  id: number;
  country_code: string;
  admin_level: number;
  state_name: string;
  district_name: string;
  gadm_id: string;
  centroid_lat: number;
  centroid_lon: number;
  area_km2: number | null;
  timezone: string;
  geom: GeoJSON.Polygon | GeoJSON.MultiPolygon;
};

/* ---------- Display helpers ---------- */

export const NO_DATA = "#4B5563";

/** Wildfire risk classes and CPCB AQI categories share one colour map. */
export const RISK_COLORS: Record<string, string> = {
  Low: "#22C55E",
  Moderate: "#F59E0B",
  High: "#F97316",
  Extreme: "#EF4444",
  Good: "#22C55E",
  Satisfactory: "#84CC16",
  Poor: "#F97316",
  "Very Poor": "#EF4444",
  Severe: "#B91C1C",
};

export const RISK_BADGE: Record<string, string> = {
  Low: "Low risk",
  Moderate: "Moderate risk",
  High: "High risk",
  Extreme: "Extreme risk",
};

/** Short, plain labels for model features; anything missing falls back to the backend label. */
export const FACTOR_LABELS: Record<string, string> = {
  climatological_fire_freq: "Fire history this month",
  rh_mean: "Humidity",
  fires_prev_7d: "Fires in last 7 days",
  temp_max: "Max temperature",
  temp_min: "Min temperature",
  wind_max: "Wind",
  precip_sum: "Rain",
  fwi: "Fire Weather Index",
  fwi_value: "Fire Weather Index",
};

/** Bar widths 0..1, scaled to the largest absolute SHAP impact. */
export function factorFracs(factors: { impact: number }[] | null | undefined): number[] {
  if (!factors?.length) return [];
  const max = Math.max(...factors.map((f) => Math.abs(f.impact ?? 0)));
  return factors.map((f) => (max > 0 ? Math.abs(f.impact ?? 0) / max : 0));
}

/** "Mon 2026-11-09 4:02 PM IST (UTC+05:30)" -> "9 Nov, 4:02 PM". Unknown formats are returned trimmed. */
export function shortTime(v: string | null | undefined): string {
  if (!v) return "–";
  const m = v.match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}:\d{2}\s*[AP]M)/i);
  if (m) {
    const mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(m[2]) - 1];
    return `${Number(m[3])} ${mon}, ${m[4].toUpperCase()}`;
  }
  const d = new Date(v);
  if (!isNaN(d.getTime()))
    return d.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" });
  return v.replace(" (UTC+05:30)", "");
}

/** Today's date in India as YYYY-MM-DD. */
export function todayIST(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

/** "2026-11-08" -> "Sun, 8 Nov". */
export function dayLabel(d: string): string {
  return new Date(`${d}T00:00:00+05:30`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
}

/** "today" when the forecast is for today in India, else "on Sun, 8 Nov" (so an old forecast never reads as today's). */
export function forecastWhen(d: string | null | undefined): string {
  if (!d) return "today";
  return d === todayIST() ? "today" : `on ${dayLabel(d)}`;
}

/** Indian digit grouping; null -> "–". */
export function fmt(n: number | null | undefined, digits = 0): string {
  if (n == null || Number.isNaN(n)) return "–";
  return n.toLocaleString("en-IN", { maximumFractionDigits: digits });
}
