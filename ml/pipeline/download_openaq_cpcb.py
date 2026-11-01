"""Download real daily PM2.5/PM10 station data for India from OpenAQ v3.

Government monitors only (providers CPCB, caaqm). One CSV per sensor under
data/raw/openaq/sensors/, resumable. Values are OpenAQ's daily aggregates with
their coverage percentage; nothing is filled or imputed.
API key is injected by the sandbox proxy (header X-API-Key) or OPENAQ_API_KEY.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.openaq.org/v3"
PROVIDERS = {"CPCB", "caaqm"}
PARAMS = {"pm25", "pm10"}
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def get(url: str) -> dict:
    headers = {"Accept": "application/json"}
    key = os.environ.get("OPENAQ_API_KEY")
    if key:
        headers["X-API-Key"] = key
    for attempt in range(6):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                remaining = int(r.headers.get("X-Ratelimit-Remaining", "10"))
                reset = int(r.headers.get("X-Ratelimit-Reset", "60"))
                body = json.load(r)
            if remaining <= 1:
                time.sleep(reset + 1)
            return body
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("X-Ratelimit-Reset", "60")) + 1)
                continue
            if e.code >= 500:
                time.sleep(10 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"failed after retries: {url}")


def list_sensors(out: Path) -> list[dict]:
    meta = out / "sensors.csv"
    if meta.exists():
        with meta.open() as f:
            return list(csv.DictReader(f))
    rows: list[dict] = []
    page = 1
    while True:
        d = get(f"{API}/locations?countries_id=9&limit=1000&page={page}")
        for loc in d["results"]:
            prov = (loc.get("provider") or {}).get("name")
            if prov not in PROVIDERS or loc.get("isMobile"):
                continue
            for s in loc["sensors"]:
                if s["parameter"]["name"] in PARAMS:
                    rows.append(
                        {
                            "sensor_id": s["id"],
                            "parameter": s["parameter"]["name"],
                            "units": s["parameter"]["units"],
                            "location_id": loc["id"],
                            "location": loc["name"],
                            "provider": prov,
                            "lat": loc["coordinates"]["latitude"],
                            "lon": loc["coordinates"]["longitude"],
                        }
                    )
        if len(d["results"]) < 1000:
            break
        page += 1
    out.mkdir(parents=True, exist_ok=True)
    with meta.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def download_sensor(sid: str, start: str, end: str, path: Path) -> int:
    out: list[tuple] = []
    page = 1
    while True:
        d = get(f"{API}/sensors/{sid}/days?limit=1000&page={page}")
        res = d["results"]
        for r in res:
            m = DATE_RE.search(str(r["period"]["datetimeFrom"]["local"]))
            if not m:
                continue
            day = m.group(1)
            if start <= day <= end and r.get("value") is not None:
                cov = r.get("coverage") or {}
                out.append((day, r["value"], cov.get("observedCount"), cov.get("percentComplete")))
        if len(res) < 1000:
            break
        page += 1
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value", "observed_hours", "pct_complete"])
        w.writerows(sorted(set(out)))
    tmp.rename(path)
    return len(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, default=Path("data/raw/openaq"))
    p.add_argument("--start", default="2022-08-01")
    p.add_argument("--end", required=True)
    p.add_argument("--max-minutes", type=float, default=18.0)
    a = p.parse_args()
    t0 = time.time()
    sensors = list_sensors(a.out_dir)
    sdir = a.out_dir / "sensors"
    sdir.mkdir(parents=True, exist_ok=True)
    todo = [s for s in sensors if not (sdir / f"{s['sensor_id']}.csv").exists()]
    print(f"{len(sensors)} sensors, {len(todo)} to download", flush=True)
    done = 0
    for s in todo:
        if (time.time() - t0) / 60 > a.max_minutes:
            break
        n = download_sensor(s["sensor_id"], a.start, a.end, sdir / f"{s['sensor_id']}.csv")
        done += 1
        if done % 25 == 0:
            print(f"{done} sensors this run (last {s['sensor_id']}: {n} days)", flush=True)
    left = len(todo) - done
    print(f"done {done} this run, {left} remaining", flush=True)


if __name__ == "__main__":
    main()
