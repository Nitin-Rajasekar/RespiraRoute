"""
FastAPI server for RespiraRoute.

Provides REST endpoints and real-time data to the frontend.
Also runs the data simulator in a background thread.
"""

import json
import os
import sys
import threading
import time

from dotenv import load_dotenv
load_dotenv()
from typing import Optional

from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add backend dir to path
sys.path.insert(0, os.path.dirname(__file__))

from config import API_HOST, API_PORT, CITIES
from ai_explainer import explain_route_safety, explain_pollution_spike, give_health_advice
from pathway_pipeline import pipeline
from data_simulator import run_simulator
from custom_router import get_custom_routes, autocomplete_location, _reverse_geocode_name

app = FastAPI(title="RespiraRoute", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Start the data simulator and Pathway pipeline on server startup."""
    sim_thread = threading.Thread(target=run_simulator, daemon=True)
    sim_thread.start()

    time.sleep(1)

    pipeline.start()


@app.get("/")
async def root():
    return {"service": "RespiraRoute", "status": "running"}


@app.get("/api/cities")
async def get_cities():
    """List all available cities with their coordinates."""
    cities = []
    for name, data in CITIES.items():
        cities.append({
            "name": name,
            "lat": data["lat"],
            "lng": data["lng"],
            "zone_count": len(data["zones"]),
        })
    return {"cities": cities}


@app.get("/api/zones")
async def get_zones(city: Optional[str] = Query(None)):
    """Get latest zone data with AQI, traffic, weather."""
    state = pipeline.get_latest_state(city=city)
    return state



@app.get("/api/dashboard")
async def get_dashboard(city: Optional[str] = Query(None)):
    """Combined endpoint: zones + routes + metadata for the dashboard."""
    zone_data = pipeline.get_zone_data_dict(city=city)
    state = pipeline.get_latest_state(city=city)

    # Build zone_config for the response
    if city:
        zone_config = {
            name: {"lat": z["lat"], "lng": z["lng"]}
            for name, z in CITIES.get(city, {}).get("zones", {}).items()
        }
    else:
        zone_config = {
            name: {"lat": c["lat"], "lng": c["lng"]}
            for name, c in CITIES.items()
        }

    return {
        "zones": state["zones"],
        "anomalies": state["anomalies"],
        "processed_records": state["processed_records"],
        "timestamp": state["timestamp"],
        "zone_config": zone_config,
        "city": city,
    }


@app.get("/api/autocomplete")
async def autocomplete(q: str):
    """Location autocomplete using Nominatim."""
    if len(q.strip()) < 2:
        return {"suggestions": []}
    try:
        return {"suggestions": await autocomplete_location(q)}
    except Exception:
        return {"suggestions": []}


@app.get("/api/custom-routes")
async def custom_routes(start: str, end: str):
    """Get route exposure for custom start/end locations using OSRM + real AQI."""
    # Collect all zone data as fallback if Open-Meteo is rate limited
    all_zone_data = pipeline.get_zone_data_dict()
    try:
        return await get_custom_routes(start, end, zone_data=all_zone_data)
    except ValueError as e:
        return {"routes": [], "recommended": None, "error": str(e)}


@app.post("/api/enrich-route-names")
async def enrich_route_names(body: dict):
    """Reverse geocode a list of coordinates to get real area names."""
    coords = body.get("coords", [])
    names = []
    for c in coords:
        name = await _reverse_geocode_name(c["lat"], c["lng"])
        names.append(name)
    return {"names": names}


@app.post("/api/explain/route")
async def explain_route(body: dict = Body(default={}), city: Optional[str] = Query(None)):
    """AI explanation: Why is this route safer? Accepts dynamic route_data from frontend."""
    zone_data = pipeline.get_zone_data_dict(city=city)
    route_data = body.get("route_data") or {}
    explanation = explain_route_safety(route_data, zone_data)
    return {"question": "Why is this route safer?", "explanation": explanation}


@app.get("/api/explain/pollution")
async def explain_pollution(city: Optional[str] = Query(None)):
    """AI explanation: What caused the pollution spike?"""
    zone_data = pipeline.get_zone_data_dict(city=city)
    explanation = explain_pollution_spike(zone_data)
    return {"question": "What caused the pollution spike?", "explanation": explanation}


@app.post("/api/explain/health")
async def explain_health(body: dict = Body(default={}), city: Optional[str] = Query(None)):
    """AI explanation: Health advice. Accepts dynamic route_data from frontend."""
    zone_data = pipeline.get_zone_data_dict(city=city)
    route_data = body.get("route_data") or {}
    explanation = give_health_advice(zone_data, route_data)
    return {"question": "Health advice for your commute", "explanation": explanation}


@app.get("/api/anomaly-insights")
async def get_anomaly_insights(city: Optional[str] = Query(None)):
    """Get LLM-generated explanations for anomalies (produced by Pathway async UDF)."""
    explanations = pipeline.get_llm_explanations(city=city)
    return {
        "insights": explanations[-10:],
        "count": len(explanations),
        "source": "pathway_llm_udf",
    }


@app.get("/api/stream")
async def stream_data(city: Optional[str] = Query(None)):
    """Server-Sent Events stream for real-time updates."""

    async def event_generator():
        last_processed = 0
        while True:
            state = pipeline.get_latest_state(city=city)
            current_processed = state["processed_records"]

            if current_processed != last_processed:
                payload = {
                    "zones": state["zones"],
                    "anomalies": state["anomalies"],
                    "timestamp": state["timestamp"],
                }
                yield f"data: {json.dumps(payload)}\n\n"
                last_processed = current_processed

            await _async_sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _async_sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
