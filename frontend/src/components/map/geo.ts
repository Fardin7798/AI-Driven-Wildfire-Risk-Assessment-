import type { LngLatBoundsLike } from "maplibre-gl";

export const INDIA_BOUNDS: LngLatBoundsLike = [[68.1, 6.5], [97.4, 35.7]];
export const BASEMAP = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export function bbox(g: GeoJSON.Polygon | GeoJSON.MultiPolygon): [[number, number], [number, number]] {
  let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
  const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
  for (const poly of polys) for (const ring of poly) for (const [x, y] of ring) {
    if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y;
  }
  return [[x0, y0], [x1, y1]];
}

/** Approximate "town area": a circle polygon of radiusKm around a point (most Indian towns have no OSM boundary). */
export function circle(lon: number, lat: number, radiusKm = 2.5, steps = 64): GeoJSON.Polygon {
  const ring: [number, number][] = [];
  const dLat = radiusKm / 110.574, dLon = radiusKm / (111.32 * Math.cos((lat * Math.PI) / 180));
  for (let i = 0; i <= steps; i++) { const a = (i / steps) * 2 * Math.PI; ring.push([lon + dLon * Math.cos(a), lat + dLat * Math.sin(a)]); }
  return { type: "Polygon", coordinates: [ring] };
}

/** Real town boundary from OpenStreetMap Nominatim when OSM has one; null otherwise. */
export async function townBoundary(q: string): Promise<GeoJSON.Polygon | GeoJSON.MultiPolygon | null> {
  try {
    const u = `https://nominatim.openstreetmap.org/search?format=jsonv2&polygon_geojson=1&polygon_threshold=0.0005&countrycodes=in&limit=1&q=${encodeURIComponent(q)}`;
    const r = await fetch(u, { headers: { Accept: "application/json" }, signal: AbortSignal.timeout(4000) });
    if (!r.ok) return null;
    const g = (await r.json())?.[0]?.geojson;
    return g && (g.type === "Polygon" || g.type === "MultiPolygon") ? g : null;
  } catch { return null; }
}
