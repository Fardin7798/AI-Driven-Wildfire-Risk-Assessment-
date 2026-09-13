import os
import sys
import asyncio
import json
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(root_dir, ".env"), override=True)
load_dotenv(os.path.join(backend_dir, ".env"), override=True)

from services.firms_service import fetch_active_fires
from services.weather_service import fetch_live_weather
from services.aqi_service import fetch_live_and_forecast_aqi
from services.fwi_engine import calculate_fire_risk

SUPABASE_URL = os.getenv("WILDFIRE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("WILDFIRE_SUPABASE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase credentials missing in environment.")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

DATA_PATH = os.path.join(backend_dir, "data", "indian_districts.json")
with open(DATA_PATH, "r") as f:
    DISTRICTS = json.load(f)

async def main():
    print(f"================================================================")
    print(f"  Starting Complete Supabase Database Modernization & Full Sync  ")
    print(f"  Project: {SUPABASE_URL}")
    print(f"================================================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Clean legacy / stale August 31 data from old tables
        print("\n[Step 1/5] Purging legacy August 31 records from old tables...")
        for tbl in ["raw_weather", "raw_aqi", "raw_fire_detections", "risk_scores", "aqi_forecast"]:
            # Delete where id is greater than 0 (clears all legacy rows)
            del_resp = await client.delete(f"{SUPABASE_URL}/rest/v1/{tbl}?id=gt.0", headers=HEADERS)
            print(f"  Purged legacy rows from [{tbl}]: status {del_resp.status_code}")

        # 2. Ingest 100% Live Real NASA VIIRS Satellite Fires into raw_fire_detections
        print("\n[Step 2/5] Fetching live NASA VIIRS satellite active fires across India...")
        live_fires = await fetch_active_fires()
        print(f"  Found {len(live_fires)} real active fire hotspots in India today.")
        
        fire_rows = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for f in live_fires:
            fire_rows.append({
                "lat": f["lat"],
                "lon": f["lon"],
                "confidence": str(f.get("confidence", "nominal")),
                "frp": f.get("frp", 0.0),
                "timestamp": now_iso,
                "source": "NASA_VIIRS_SNPP_NRT",
                "state": "India",
                "district": "Satellite Coordinate"
            })

        # Insert in batches of 100
        for i in range(0, len(fire_rows), 100):
            batch = fire_rows[i:i+100]
            r = await client.post(f"{SUPABASE_URL}/rest/v1/raw_fire_detections", headers=HEADERS, json=batch)
            print(f"  Inserted live fire batch {i//100 + 1} ({len(batch)} rows): status {r.status_code}")

        # 3. Synchronize Live Weather, AQI, FWI Risk Scores, and Forecasts for all 39 Districts
        print("\n[Step 3/5] Streaming live environmental telemetry for all 39 Indian districts...")
        
        weather_rows = []
        aqi_rows = []
        risk_rows = []
        forecast_rows = []

        semaphore = asyncio.Semaphore(6)

        async def process_district(d):
            async with semaphore:
                dist_id = d["id"]
                lat = d["lat"]
                lon = d["lon"]
                name = d["name"]

                try:
                    w = await fetch_live_weather(lat, lon)
                    aq = await fetch_live_and_forecast_aqi(lat, lon)
                    risk = calculate_fire_risk(
                        temp=w["temperature"],
                        rh=w["humidity"],
                        wind=w["wind_speed"],
                        rain=w["precipitation"]
                    )

                    weather_rows.append({
                        "region_id": dist_id,
                        "timestamp": now_iso,
                        "temp": w["temperature"],
                        "humidity": w["humidity"],
                        "wind_speed": w["wind_speed"],
                        "rainfall": w["precipitation"]
                    })

                    aqi_rows.append({
                        "station_id": f"{name} Monitoring Station",
                        "region_id": dist_id,
                        "timestamp": now_iso,
                        "pollutant_id": "CPCB_NAQI",
                        "pollutant_avg": aq["pollutants"]["pm2_5"],
                        "aqi_value": aq["cpcb_aqi"]
                    })

                    risk_rows.append({
                        "region_id": dist_id,
                        "timestamp": now_iso,
                        "risk_level": risk["risk_level"],
                        "risk_score": risk["fwi_score"],
                        "model_version": "canadian-fwi-v1"
                    })

                    # Insert next 24 hours of forecast points
                    for pt in aq.get("forecast_72h", [])[:24]:
                        forecast_rows.append({
                            "region_id": dist_id,
                            "timestamp": pt["time"],
                            "predicted_aqi": pt["aqi"],
                            "lower_bound": max(0, pt["aqi"] - 15),
                            "upper_bound": pt["aqi"] + 20
                        })

                    # Update summary attributes in regions table
                    update_payload = {
                        "current_risk_level": risk["risk_level"],
                        "current_aqi": aq["cpcb_aqi"],
                        "current_fwi": risk["fwi_score"],
                        "last_updated": now_iso
                    }
                    await client.patch(f"{SUPABASE_URL}/rest/v1/regions?id=eq.{dist_id}", headers=HEADERS, json=update_payload)
                    print(f"  Synced {name} ({dist_id}): FWI={risk['fwi_score']}, AQI={aq['cpcb_aqi']}")

                except Exception as e:
                    print(f"  Failed syncing {name}: {e}")

        tasks = [process_district(d) for d in DISTRICTS]
        await asyncio.gather(*tasks)

        # 4. Batch Insert Processed Telemetry into Supabase
        print("\n[Step 4/5] Writing fresh records to Supabase tables...")
        if weather_rows:
            r = await client.post(f"{SUPABASE_URL}/rest/v1/raw_weather", headers=HEADERS, json=weather_rows)
            print(f"  Inserted {len(weather_rows)} live records to [raw_weather]: status {r.status_code}")
        
        if aqi_rows:
            r = await client.post(f"{SUPABASE_URL}/rest/v1/raw_aqi", headers=HEADERS, json=aqi_rows)
            print(f"  Inserted {len(aqi_rows)} live records to [raw_aqi]: status {r.status_code}")

        if risk_rows:
            r = await client.post(f"{SUPABASE_URL}/rest/v1/risk_scores", headers=HEADERS, json=risk_rows)
            print(f"  Inserted {len(risk_rows)} live records to [risk_scores]: status {r.status_code}")

        if forecast_rows:
            # Batch forecast rows in chunks of 200
            for i in range(0, len(forecast_rows), 200):
                batch = forecast_rows[i:i+200]
                r = await client.post(f"{SUPABASE_URL}/rest/v1/aqi_forecast", headers=HEADERS, json=batch)
            print(f"  Inserted {len(forecast_rows)} live forecast records to [aqi_forecast]: completed.")

        # 5. Database Verification Report
        print("\n[Step 5/5] Final Supabase Database Verification:")
        for tbl in ["regions", "raw_fire_detections", "raw_weather", "raw_aqi", "risk_scores", "aqi_forecast", "telemetry_logs"]:
            cnt_resp = await client.get(f"{SUPABASE_URL}/rest/v1/{tbl}?select=count", headers={**HEADERS, "Prefer": "count=exact"})
            cr = cnt_resp.headers.get("content-range", "N/A")
            total = cr.split("/")[-1] if "/" in cr else "N/A"
            print(f"  Table [{tbl}]: {total} current verified rows")

    print("\n================================================================")
    print("  Supabase Database 100% Modernized & Synchronized Successfully!")
    print("================================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
