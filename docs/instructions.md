# Build Instructions — How This Project Was Built (Systematic Methodology)

This document records the **actual chronological process** used to build this
platform from an empty planning-only repo to a fully deployed, real-data,
ML-powered full-stack application. It's meant as both a project history and a
reusable methodology for future work on this repo (or similar projects).

## Core Principles Followed Throughout

1. **Verify, never assume.** Every API, every library, every config was
   actually tested with a real call before being trusted or documented.
2. **Build in small, independently-testable steps.** Never wrote a large
   chunk of untested code — each piece (one endpoint, one ingestion
   function, one component) was written, then tested, then moved on.
3. **Contract-first for the backend.** Built the API shape with seed/mock
   data first, so the frontend and deployment pipeline had something
   stable to build against — then swapped seed data for real data
   incrementally.
4. **Label fake vs. real, always, out loud.** Whenever something was a
   placeholder/hardcoded value, that was stated explicitly. Once replaced
   with real data, that was stated too. Never let "looks done" pass as
   "is done."
5. **Deploy early, verify in production constantly.** Not just "code
   compiles" — after almost every change, the actual live production URL
   was curled/screenshotted to confirm real behavior, not assumed behavior.
6. **Fix root causes, not symptoms.** Every bug encountered was traced to
   its actual cause (e.g. an IPv6/IPv4 networking mismatch, not just
   "retry until it works") before being fixed.
7. **Keep documentation in sync with reality.** After every real change,
   `CONTEXT.md` and `docs/api-docs.md` were updated so future sessions
   (or other developers) never work from stale assumptions.

---

## The Per-Change Loop (followed for every real change in this project)

This exact cycle repeated for almost every single change made on this
project, not just at big milestones:

1. Write the smallest piece of the change (one endpoint, one function,
   one component).
2. Test it directly — run it locally, curl it, or query the database
   directly. Never moved on based on "the code looks right."
3. `git add` + `git commit` with a message describing what changed,
   what was tested, and any bug found+fixed in that specific commit
   (see the many commit messages in this repo's history — each one
   documents its own verification, not just "fixed stuff").
4. `git push` to GitHub.
5. Trigger a deploy (Render) — not batched with other changes.
6. Verify the **actual live production URL** (curl or a Playwright
   screenshot), not just "deploy status: live."
7. If production verification found a problem (this happened several
   times — see the Bug List below), that became the next change,
   starting back at step 1, before moving on to new features.

This is why the git history for this project has many small, focused
commits with detailed messages instead of a few giant ones — each
commit represents one verified, working change.

---

## Phase 1 — Read Every Doc Before Writing Any Code

Before touching code, all existing planning docs were read in full:
`docs/PRD_Wildfire_AQI_Platform.md`, `docs/architecture.md`,
`docs/api-docs.md`, `docs/tech-stack.md`, `CONTEXT.md`, `TEST.md`. This
established: the exact API contract to build against, the DB schema,
the tech stack decisions already made, and what data sources were
planned (FSI, NASA FIRMS, CPCB, IMD/Open-Meteo, SAFAR, Bhuvan).

## Phase 2 — Verify Every Planned Data Source With Real API Calls

Rather than trusting the docs' assumptions, every listed data source was
actually queried live:

| Source | Result |
|---|---|
| NASA FIRMS | ✅ Real free API, MAP_KEY signup confirmed working |
| CPCB (data.gov.in) | ✅ Real free API, personal key signup confirmed working |
| Open-Meteo (weather) | ✅ Real, zero-friction, no key needed |
| FSI Fire Alert System | ❌ No public API exists — site-only, WMS restricted to govt depts |
| SAFAR (IITM Pune) | ❌ No API — static images only, site was unreachable during testing |
| Bhuvan (ISRO) NDVI | ❌ API exists but has no NDVI-specific endpoint |

This step **changed the architecture** before any code was written: FSI was
dropped as the primary fire source in favor of NASA FIRMS (same underlying
MODIS/VIIRS data, but with an actual API).

## Phase 3 — Fix Stale/Broken Documentation Before Building

A grep across all docs turned up leftovers from an earlier Canada/BC
version of this project (`bc-kelowna` region IDs, Kelowna coordinates,
a PurpleAir reference that isn't part of the India data stack) plus a
broken reference to a `docs/instructions.md` file that didn't exist yet
(this file). All of these were fixed/removed so the docs matched reality
before implementation started.

## Phase 4 — Backend Skeleton With Seed Data (Contract-First)

A minimal FastAPI app (`backend/main.py`) was built implementing all 6
documented endpoints (`/regions`, `/risk`, `/aqi`, `/alerts`, `/trends`,
`/preparedness`) plus `/health`, initially returning **hardcoded seed
data** shaped exactly like the documented JSON contract. This was tested
locally (`uvicorn`) before any real data or deployment was introduced —
the goal was to validate the API *shape* independently of data
correctness.

---

## Phase 5 — Deploy the Skeleton Immediately (Render)

Rather than building everything locally first, the seed-data backend was
deployed to Render right away, via the Render MCP connector. This
surfaced a real bug immediately: Render's default Python 3.14 had no
prebuilt `pydantic-core` wheel, causing every build to fail. Fixed by
pinning `PYTHON_VERSION=3.12.3` as an environment variable. Deploying
early meant this class of "works on my machine, fails on the platform"
issue was caught in minutes, not discovered later.

## Phase 6 — Real Database (Supabase, Not Local Docker)

A design decision was made (and confirmed with the user, with tradeoffs
presented — local Docker is more offline-friendly, Supabase is easier
to demo remotely) to use Supabase (hosted Postgres+PostGIS, free tier)
instead of the originally-planned local Docker Compose setup. Cost was
explicitly verified (`$0/month` confirmed via the Supabase MCP's
`get_cost`/`confirm_cost` flow) before provisioning, not assumed from
"free tier" alone. Provisioned via the Supabase MCP connector: project
created in the Mumbai region (closest to India, lowest latency),
PostGIS extension enabled, the full schema from `architecture.md`
created via SQL migrations, and 2 pilot regions (Nainital, Delhi)
seeded.

Connecting the backend to it surfaced a second real bug: Supabase's
direct connection host is **IPv6-only** on the free tier, and Render has
**no IPv6 egress** — every connection attempt failed with "Network is
unreachable". Fixed by switching to Supabase's Supavisor connection
pooler (`aws-0-ap-south-1.pooler.supabase.com:6543`), which is
IPv4-compatible. This was diagnosed by reading the actual error logs
from the live Render deployment, not guessed at.

## Phase 7 — Data Ingestion Pipeline (Real APIs → Real Database)

`backend/ingestion.py` was built with one function per data source
(`fetch_weather`, `fetch_fire_detections`, `fetch_aqi`), each writing
real API responses into the corresponding Postgres table. Two more real
bugs were found and fixed here, both by testing against the live
pipeline rather than assuming success:

- **data.gov.in silently blocks the default `python-requests` User-Agent**
  — every CPCB call hung until timeout. `curl` worked instantly with the
  same URL, which was the actual diagnostic clue. Fixed with a
  browser-like `User-Agent` header.
- **NASA FIRMS returns `acq_time` unpadded** (e.g. `"807"` instead of
  `"0807"` for 8:07am), which broke timestamp parsing and crashed
  inserts. Fixed with `.zfill(4)`.

The pipeline was wired into the FastAPI app via `APScheduler` (hourly)
plus a manual `POST /admin/ingest` trigger for on-demand testing —
proved via a live curl to production returning real row counts
(`{"weather_rows":2,"fire_rows":99,"aqi_rows":58}`), not just "the code
looks right."

## Phase 8 — Honest Interim: Rule-Based Risk Score (Before ML)

Before any ML model existed, `/risk` still returned a **hardcoded**
`0.78` — this was called out explicitly as fake, not silently left in.
As a first honest improvement (before ML was feasible — no historical
data existed yet), a simple rule-based fire-danger formula was built
using real inputs (humidity, wind, temperature, nearby fire-detection
count) instead of a fixed number. This was explicitly labeled
`model_version: "rule-based-v1"` in the API response so it was never
confused with a real trained model.

---

## Phase 9 — ML Model 1: Fire Risk (XGBoost, Google Colab)

Once the rule-based interim was in place, real ML training was tackled.
Key realization: training data did **not** need to wait for the live
ingestion pipeline to accumulate weeks of data — both NASA FIRMS and
Open-Meteo have free historical/archive APIs going back years, so a
training dataset could be built immediately:

1. A Python notebook (`ml/wildfire_risk_training.ipynb`) was generated
   programmatically (via `nbformat`, not hand-written JSON, to avoid
   malformed-notebook errors).
2. It downloads ~6 months of real historical NASA FIRMS fire detections
   for all of India (looped in 5-day chunks, since the API caps
   `day_range` per request), samples random no-fire points/dates as
   negative examples, and fetches real historical weather for every
   point via Open-Meteo's Historical Weather API.
3. Both data-fetching functions were tested with real API calls
   **before** being trusted inside the notebook, to catch bugs early
   (found and fixed the same unpadded-`acq_time` bug here too).
4. The notebook was uploaded to Google Colab (free tier) and actually
   run by the user; the resulting `fire_risk_model.pkl` was downloaded
   and placed back into the repo.
5. Before integrating, the model was sanity-checked locally: humid/calm
   weather correctly predicted ~0.3% fire probability, hot/dry/windy
   weather predicted ~68% — confirming it had learned real patterns, not
   noise.
6. Integrated into `ingestion.py`'s `compute_risk()`, replacing the
   rule-based formula (`model_version` updated to `"xgboost-v1"`).
   Live-verified on production: real, different predictions per region.
7. **A known limitation was documented, not hidden**: the model only
   sees weather features, no land-cover context, so hot+dry urban
   weather (e.g. Delhi) can score the same as hot+dry forest weather —
   flagged explicitly in `CONTEXT.md` as a v2 improvement, not swept
   under the rug.

## Phase 10 — ML Model 2: AQI Forecasting (Prophet, Google Colab)

Same methodology repeated for AQI forecasting:

1. Verified Open-Meteo's **Air Quality API** has a free historical
   endpoint (CAMS reanalysis) going back over a year, with a real test
   call before building anything.
2. Generated a second notebook (`ml/aqi_forecasting_training.ipynb`)
   that downloads real daily-average PM2.5 per region and trains one
   Prophet model per region.
3. Run in Colab by the user, resulting `.pkl` files placed back in the
   repo, loaded and sanity-checked locally (real 7-day forecast values
   with sensible confidence bounds) before integration.
4. Integrated into `/aqi/{region_id}` — the previously **empty forecast
   array with an honest "not built yet" note** was replaced with real
   Prophet predictions. The honest-empty-array step is notable: rather
   than fake a forecast to fill the gap while the real model didn't
   exist yet, the API explicitly said so until it was genuinely ready.

## Phase 11 — MCP Tooling for Non-Code Work

Throughout Phases 6–10, MCP connectors were used directly for
infrastructure work instead of manual dashboard clicking: the Supabase
MCP for all database provisioning/schema/queries, and the Render MCP
for all deployment/env-var/build-trigger work — both driven
conversationally and verified with real tool calls (e.g. `execute_sql`
to confirm rows actually landed, `get_deploy` to confirm build status)
rather than assumed from a "should have worked" state.

---

## Phase 12 — Frontend: Design First, Then Build

Before writing frontend code, a short design plan was made (per the
project's frontend-design guidance): a specific color palette (not a
generic default), two purposeful fonts (a display serif + a data-dense
body sans), and a layout principle ("visual weight follows real risk
data, never arbitrary") — so the UI would look intentional, not
templated.

Scaffolded with Vite + React + TypeScript + Tailwind CSS v4 + React
Router + Recharts (matching `tech-stack.md`). A real, machine-specific
bug was hit immediately: a system-wide `NODE_ENV=production` setting
was silently stripping all `devDependencies` (including `vite` and
`tsc` themselves) on every `npm install` — diagnosed by comparing
`node_modules` contents before/after, not guessed. Fixed permanently
with a project-level `.npmrc` (`include=dev`).

Built out all 3 documented routes (dashboard, region detail,
preparedness) wired to the live backend API via a typed API client
(`lib/api.ts`), reusing the same `Region`/`RiskResponse`/etc. types the
backend contract defines.

## Phase 13 — Using MCP Component Registries for Real UI Code

Rather than hand-rolling every UI element, the shadcn-ui-mcp-server MCP
tool was used to fetch a **real, current** shadcn/ui `Card` component
(not written from memory/training data, which can be stale), which was
then integrated by mapping shadcn's standard color-token names onto the
project's own custom palette so the fetched component matched the
design system without a separate theme file.

## Phase 14 — Screenshot-Driven Verification (Not Just "It Compiles")

At every meaningful step, a headless-Chromium (Playwright) screenshot of
the actual running app was taken and visually reviewed — this caught
real bugs that `tsc --noEmit` and `npm run build` both passed cleanly
without catching:

- The dashboard's big risk number was a **hardcoded per-level lookup**
  (e.g. always "92" for Extreme), not the real `risk_score` — only
  visible by actually looking at the rendered number against the known
  real API value.
- A trend chart mixed a 0–1 scale (`risk_score`) and a 0–500 scale
  (`aqi`) on one shared Y-axis, making the risk line **invisible** —
  a build/type error would never catch this, only looking at the chart.
- `maplibre-gl`'s installed version has **no default export**, which
  produced a fully blank white page at runtime with zero build-time
  errors — caught by checking the browser console via Playwright
  (`page.on('pageerror', ...)`), not by the build succeeding.

## Phase 15 — Interactive Map (MapLibre GL JS)

A real map component was built using MapLibre GL JS with a free CARTO
Positron basemap (verified live before use, no API key needed) —
markers placed at each region's real coordinates, colored by real
`current_risk_level`, clickable to navigate to region detail. This
fulfilled a `tech-stack.md` requirement that had initially been skipped
in favor of a decorative gradient — the gap was explicitly flagged to
the user rather than left unmentioned, then filled.

## Phase 16 — Deploy Frontend, Verify Production Matches Local

Deployed as a Render Static Site via the Render MCP connector, with
`VITE_API_BASE` set at build time to the live backend URL (since the
dev-only proxy doesn't exist in a static production build). After
deploy, a Playwright screenshot of the **actual live production URL**
was taken and compared against local dev — confirming the deployed
version genuinely matched, not just "should be the same."

---

## Phase 17 — Discovering a Generalization Gap (in progress)

After the full stack was live, a real gap was identified: both the
Prophet AQI forecast models and the `regions` table only covered 2
pilot cities (Delhi, Nainital) — not genuinely "all of India" as the
PRD intends. This wasn't caught earlier because testing had (correctly,
per Phase 6-equivalent guidance) started with a small pilot set, but
"done" was never re-checked against the full intended scope until the
user explicitly asked whether any city in India could be searched.

Key finding while investigating: the XGBoost fire-risk model itself
**does** generalize (it takes only weather features, not
location-specific ones), so it already works for any coordinates — the
real gap is the AQI forecast (per-region-trained Prophet models) and
the fixed 2-row `regions` table blocking arbitrary city search. A free
geocoding API (Open-Meteo's, no key needed) and CPCB's existing
city-level filter were verified as the path to a real fix (in
progress as of this writing).

---

## Full Bug List (Found by Testing, Fixed at the Root Cause)

Every one of these was caught by actually running/deploying/testing —
none were caught by code review alone:

| # | Bug | Root cause | Fix |
|---|---|---|---|
| 1 | Render build failures | Python 3.14 default had no prebuilt `pydantic-core` wheel | Pin `PYTHON_VERSION=3.12.3` |
| 2 | DB connection "Network is unreachable" | Supabase direct host is IPv6-only; Render has no IPv6 egress | Use Supavisor pooler (IPv4) |
| 3 | CPCB API calls hang until timeout | data.gov.in blocks default `python-requests` User-Agent | Send a browser-like User-Agent header |
| 4 | Fire-detection insert crashes | FIRMS `acq_time` isn't always zero-padded (`"807"` not `"0807"`) | `.zfill(4)` before parsing |
| 5 | Dashboard risk number is fake | Hardcoded per-risk-level lookup table instead of real `risk_score` | Fetch and display the real score |
| 6 | Trend chart risk line invisible | Two metrics (0-1 and 0-500 scale) sharing one Y-axis | Split into dual Y-axis |
| 7 | Frontend blank white page | `maplibre-gl` has no default export in the installed version | `import * as maplibregl` instead of default import |
| 8 | `npm install` silently breaks builds | Machine-wide `NODE_ENV=production` strips devDependencies | `frontend/.npmrc` with `include=dev` |
| 9 | GitHub API key leaked risk | No `.gitignore` existed in the repo at all | Created one before any `.env` was added |
| 10 | Direct URL / page refresh on any nested route (`/search`, `/region/:id`) returns "Not Found" in production | Render Static Site has no SPA fallback by default; a Netlify-style `_redirects` file was tried first and does NOT work on Render (verified via search before deploying it — Render needs a dashboard-configured rewrite rule or `render.yaml` routes, not `_redirects`) | Added a Rewrite rule in Render dashboard (Source `/*` → Destination `/index.html`); verified with direct navigation + hard refresh on `/search` and `/region/dl-delhi`, both now return real data instead of a 404 |

---

## How to Continue Working on This Repo (Same Methodology)

1. Read `CONTEXT.md` first — it's kept current after every real change.
2. Before adding a new data source or API, verify it with a real call —
   don't trust a blog post, doc, or training-data memory of "how the API
   works."
3. Build the smallest testable slice, test it (locally and, once
   deployed, in production), *then* move to the next slice.
4. If something is a placeholder, say so in the code/docs/response —
   never let a fake value look finished.
5. When a bug appears, read the actual error/log before guessing at a
   fix.
6. Update `CONTEXT.md` (and `docs/api-docs.md` if the API contract
   changed) as part of finishing the change, not as an afterthought.
