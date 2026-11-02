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
