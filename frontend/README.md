# WildfireRisk & CleanAir India — Frontend Client

Interactive, high-density WebGL vector mapping dashboard built with React 19, Vite, and MapLibre GL JS.

---

## 1. Architecture & Key Modules

- **`src/components/RegionMap.tsx`**: 60fps GPU-accelerated vector map powered by MapLibre GL JS and Carto Dark Matter vector tiles. Renders live NASA FIRMS active fire satellite hotspots, pulsing cluster pins, and dynamic district boundary circles.
- **`src/components/BentoCards.tsx`**: High-density Bento Grid dashboard cards featuring:
  - Canadian FWI fire danger risk gauge and key weather drivers.
  - Live meteorological indicators (temperature, humidity, wind, rainfall).
  - CPCB National AQI category and pollutant concentrations.
  - Recharts 72-hour continuous atmospheric chemical forecast area graph.
  - Dynamic NDMA emergency advisories and regional helpline directory.
- **`src/pages/Home.tsx`**: Unified search portal with instant native datalist autocomplete and quick-focus district chips.
- **`src/components/Nav.tsx`**: Header navigation bar with real-time connectivity status and link to backend OpenAPI Swagger `/docs`.
- **`src/lib/api.ts`**: Typed asynchronous client communicating with the FastAPI backend.
- **`src/types.ts`**: TypeScript interfaces strictly synchronized with backend Pydantic models.

---

## 2. Scripts & Development

```bash
# Start local development server (http://localhost:5173)
npm run dev

# Typecheck and produce production bundle
npm run build

# Preview production bundle locally
npm run preview
```
