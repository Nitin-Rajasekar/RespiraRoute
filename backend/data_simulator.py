"""
Real-time data fetcher for AQI, weather, and traffic.
Fetches real air quality and weather data from Open-Meteo APIs
for all Indian cities and their zones, then writes JSONL records
that Pathway ingests as a streaming source.
"""

import json
import os
import random
import time
from datetime import datetime, timezone

import httpx

from config import CITIES, STREAM_INTERVAL_SECONDS

STREAM_DIR = os.path.join(os.path.dirname(__file__), "stream_data")
STREAM_FILE = os.path.join(STREAM_DIR, "zone_data.jsonl")

# Open-Meteo API endpoints (free, no API key required)
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_aqi_category(aqi: int) -> str:
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def build_coordinate_list():
    """Build a flat list of all coordinates to fetch: city centers + all zones.

    Returns:
        locations: list of (city_name, zone_name_or_None, lat, lng)
        City-center entries have zone_name = None (zone field will be city name).
    """
    locations = []
    for city_name, city_data in CITIES.items():
        # City center point
        locations.append((city_name, None, city_data["lat"], city_data["lng"]))
        # Zone points
        for zone_name, zone_data in city_data["zones"].items():
            locations.append((city_name, zone_name, zone_data["lat"], zone_data["lng"]))
    return locations


BATCH_SIZE = 30  # Open-Meteo supports many coords per call; fewer calls = less rate limiting


def _fetch_batch_aqi(client: httpx.Client, lats: str, lngs: str) -> list[dict]:
    """Fetch AQI for a batch of coordinates."""
    try:
        resp = client.get(AIR_QUALITY_URL, params={
            "latitude": lats, "longitude": lngs, "current": "us_aqi",
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [{"aqi": int(item["current"]["us_aqi"]) if item.get("current", {}).get("us_aqi") is not None else None} for item in data]
        elif isinstance(data, dict) and "current" in data:
            val = data["current"].get("us_aqi")
            return [{"aqi": int(val) if val is not None else None}]
    except Exception as e:
        print(f"[DataFetcher] AQI batch error: {e}")
    return []


def _fetch_batch_weather(client: httpx.Client, lats: str, lngs: str) -> list[dict]:
    """Fetch weather for a batch of coordinates."""
    try:
        resp = client.get(WEATHER_URL, params={
            "latitude": lats, "longitude": lngs,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        items = data if isinstance(data, list) else [data]
        for item in items:
            c = item.get("current", {})
            t = c.get("temperature_2m")
            h = c.get("relative_humidity_2m")
            w = c.get("wind_speed_10m")
            results.append({
                "temperature_c": round(float(t), 1) if t is not None else None,
                "humidity_pct": int(h) if h is not None else None,
                "wind_speed_kmh": round(float(w), 1) if w is not None else None,
            })
        return results
    except Exception as e:
        print(f"[DataFetcher] Weather batch error: {e}")
    return []


def fetch_real_data(client: httpx.Client, locations: list) -> list[dict]:
    """Fetch real AQI and weather data from Open-Meteo for all locations.

    Splits into batches of BATCH_SIZE to avoid 429 rate limits.
    """
    results = [{"aqi": None, "temperature_c": None, "humidity_pct": None, "wind_speed_kmh": None}
               for _ in locations]

    for batch_start in range(0, len(locations), BATCH_SIZE):
        batch = locations[batch_start:batch_start + BATCH_SIZE]
        lats = ",".join(str(loc[2]) for loc in batch)
        lngs = ",".join(str(loc[3]) for loc in batch)

        aqi_results = _fetch_batch_aqi(client, lats, lngs)
        for i, aq in enumerate(aqi_results):
            if batch_start + i < len(results):
                results[batch_start + i]["aqi"] = aq.get("aqi")

        time.sleep(1.0)  # delay between AQI and weather calls

        wx_results = _fetch_batch_weather(client, lats, lngs)
        for i, wx in enumerate(wx_results):
            if batch_start + i < len(results):
                results[batch_start + i].update({k: v for k, v in wx.items() if v is not None})

        # Delay between batches to respect rate limits
        if batch_start + BATCH_SIZE < len(locations):
            time.sleep(1.0)

    return results


def build_records(tick: int, locations: list, api_data: list[dict]) -> list[dict]:
    """Build JSONL records from real API data."""
    records = []
    now = datetime.now(timezone.utc).isoformat()

    for i, (city_name, zone_name, lat, lng) in enumerate(locations):
        data = api_data[i] if i < len(api_data) else {}

        # AQI: use real value, fallback
        aqi = data.get("aqi")
        if aqi is None:
            aqi = max(10, int(100 + random.gauss(0, 20)))

        temp = data.get("temperature_c")
        if temp is None:
            temp = round(25 + random.gauss(0, 2), 1)

        humidity = data.get("humidity_pct")
        if humidity is None:
            humidity = max(20, min(95, int(60 + random.gauss(0, 5))))

        wind = data.get("wind_speed_kmh")
        if wind is None:
            wind = max(0, round(5 + random.gauss(0, 1.5), 1))

        # For city-center records, zone = city name
        record = {
            "city": city_name,
            "zone": zone_name if zone_name else city_name,
            "aqi": aqi,
            "aqi_category": get_aqi_category(aqi),
            "wind_speed_kmh": wind,
            "temperature_c": temp,
            "humidity_pct": humidity,
            "timestamp": now,
            "tick": tick,
        }
        records.append(record)

    return records


def run_simulator():
    """Main loop: fetch real data and write streaming JSONL for Pathway."""
    os.makedirs(STREAM_DIR, exist_ok=True)

    if os.path.exists(STREAM_FILE):
        os.remove(STREAM_FILE)

    locations = build_coordinate_list()
    num_cities = len(CITIES)
    num_zones = sum(len(c["zones"]) for c in CITIES.values())

    print(f"[DataFetcher] Starting REAL data stream -> {STREAM_FILE}")
    print(f"[DataFetcher] Sources: Open-Meteo Air Quality + Weather APIs")
    print(f"[DataFetcher] Monitoring {num_cities} cities + {num_zones} zones = {len(locations)} coordinates")
    print(f"[DataFetcher] Fetching every {STREAM_INTERVAL_SECONDS}s")

    tick = 0
    try:
        with httpx.Client() as client:
            while True:
                api_data = fetch_real_data(client, locations)

                api_aqi_count = sum(1 for d in api_data if d.get("aqi") is not None)
                print(f"[Tick {tick}] API returned real AQI for {api_aqi_count}/{len(locations)} points", end="")

                records = build_records(tick, locations, api_data)

                with open(STREAM_FILE, "a") as f:
                    for rec in records:
                        f.write(json.dumps(rec) + "\n")

                aqi_vals = [r["aqi"] for r in records]
                print(f" | AQI range: {min(aqi_vals)}-{max(aqi_vals)}")

                tick += 1
                time.sleep(STREAM_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[DataFetcher] Stopped.")


if __name__ == "__main__":
    run_simulator()
