# TEST.md — Build & Test Commands

## Purpose
This file lists every command to run, build, and test the project, so you (or Claude Code) can quickly verify nothing is broken before committing or after pulling changes.

---

## 1. Environment Setup Check

```bash
# Check Python version (need 3.10+)
python3 --version

# Check Node.js version (need 18+)
node --version
npm --version

# Check Docker is running
docker --version
docker compose version
```

---

## 2. Database (PostgreSQL + PostGIS)

```bash
# Start the database container
docker compose up -d postgres

# Check it's running and healthy
docker ps

# Connect to verify PostGIS extension is enabled
docker exec -it wildfire-db psql -U postgres -c "SELECT PostGIS_Version();"
```

**Expected result:** A version number prints, no connection errors.

---

## 3. Backend (FastAPI)

```bash
cd backend

# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt --break-system-packages

# Run the dev server
uvicorn main:app --reload --port 8000
```

**Health check (in a separate terminal):**
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

**Run backend tests:**
```bash
pytest tests/ -v
```

**Check for import/syntax errors without starting the server:**
```bash
python -c "import main"
```

**Lint check:**
```bash
ruff check .
```

---

## 4. Frontend (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

**Build for production (this is the real "does it break" test):**
```bash
npm run build
```
**Expected result:** Build completes with no errors, produces a `dist/` folder.

**Type check:**
```bash
npm run typecheck
# or: npx tsc --noEmit
```

**Lint check:**
```bash
npm run lint
```

**Run frontend tests (if using Vitest):**
```bash
npm run test
```

---

## 5. Full Stack — Docker Compose (all services together)

```bash
# Build and start everything
docker compose up -d --build

# Check all containers are running
docker compose ps

# View logs if something fails
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres

# Stop everything
docker compose down
```

**Expected result:** All three containers show `Up` / `healthy` status in `docker compose ps`.

---

## 6. API Endpoint Smoke Tests

Run these once the backend is up, to confirm each endpoint responds correctly.

```bash
curl http://localhost:8000/regions
curl http://localhost:8000/risk/bc-kelowna
curl http://localhost:8000/aqi/bc-kelowna
curl http://localhost:8000/alerts
curl http://localhost:8000/trends/bc-kelowna
curl http://localhost:8000/preparedness/bc-kelowna
```

**Expected result:** Each returns a `200 OK` with JSON — not a `500` or connection refused.

---

## 7. Data Ingestion Test (external APIs reachable)

```bash
# Test Open-Meteo (no key needed)
curl "https://api.open-meteo.com/v1/forecast?latitude=49.88&longitude=-119.49&current_weather=true"

# Test NASA FIRMS (replace YOUR_KEY)
curl "https://firms.modaps.eosdis.nasa.gov/api/area/csv/YOUR_KEY/VIIRS_SNPP_NRT/world/1"
```

**Expected result:** Both return data, not an auth error or timeout.

---

## 8. Pre-Commit Checklist

Run this full sequence before every commit to make sure nothing is broken:

```bash
# Backend
cd backend && ruff check . && pytest tests/ -v && cd ..

# Frontend
cd frontend && npm run typecheck && npm run lint && npm run build && cd ..

# Full stack sanity check
docker compose up -d --build && docker compose ps
```

**If all of the above pass with no errors — safe to commit and push.**

---

## 9. Common Failure Points & Fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| `uvicorn` fails to start | Missing dependency | `pip install -r requirements.txt --break-system-packages` |
| `npm run build` fails | TypeScript type error | Run `npm run typecheck` to see exact error |
| `docker compose up` fails on postgres | Port 5432 already in use | `docker ps` to find conflicting container, or change port in `docker-compose.yml` |
| API returns 500 on `/risk/{region_id}` | Region not in DB yet | Check `regions` table has been seeded |
| FIRMS/PurpleAir requests fail | Missing/invalid API key | Check `.env` file has correct keys |
| PostGIS function not found | Extension not enabled | Run `CREATE EXTENSION postgis;` in the DB |
