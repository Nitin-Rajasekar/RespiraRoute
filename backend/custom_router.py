"""
Custom route search using OSRM (routing) and Nominatim (geocoding).

Fetches real AQI from Open-Meteo for sampled points along the route
to calculate pollution exposure — works for ANY route, anywhere.
"""

import asyncio
import math
import re

import httpx

from config import CITIES

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
HEADERS = {"User-Agent": "RespiraRoute/1.0 (student-hackathon-project)"}

# Semaphore to enforce 1-request-at-a-time for Nominatim (rate limit)
_nominatim_lock = asyncio.Lock()


async def autocomplete_location(query: str) -> list[dict]:
    """Return up to 5 Nominatim suggestions for a query string."""
    async with _nominatim_lock:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 5,
                    "addressdetails": 1,
                },
                headers=HEADERS,
            )
            resp.raise_for_status()
            results = resp.json()
            await asyncio.sleep(1)  # Nominatim rate limit
    return [
        {
            "display_name": r["display_name"],
            "lat": float(r["lat"]),
            "lng": float(r["lon"]),
        }
        for r in results
    ]


async def geocode_or_parse(input_str: str) -> tuple[float, float]:
    """Accept 'lat,lng' or a place name. Returns (lat, lng)."""
    input_str = input_str.strip()
    # Try parsing as lat,lng
    match = re.match(r"^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$", input_str)
    if match:
        return float(match.group(1)), float(match.group(2))

    # Geocode via Nominatim
    async with _nominatim_lock:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={"q": input_str, "format": "json", "limit": 1},
                headers=HEADERS,
            )
            resp.raise_for_status()
            results = resp.json()
            if not results:
                raise ValueError(f"Could not geocode '{input_str}'. Try a more specific name or use lat,lng.")
            # Respect Nominatim's 1-second rate limit
            await asyncio.sleep(1)
            return float(results[0]["lat"]), float(results[0]["lon"])


def _offset_point(start: tuple[float, float], end: tuple[float, float], fraction: float, offset_km: float) -> tuple[float, float]:
    """Create a waypoint offset perpendicular to the start→end line at a given fraction along it."""
    mid_lat = start[0] + fraction * (end[0] - start[0])
    mid_lng = start[1] + fraction * (end[1] - start[1])
    # Perpendicular direction (rotate 90°)
    dlat = end[0] - start[0]
    dlng = end[1] - start[1]
    length = math.sqrt(dlat**2 + dlng**2)
    if length < 1e-8:
        return (mid_lat, mid_lng)
    # ~0.009 degrees ≈ 1km
    scale = offset_km * 0.009 / length
    perp_lat = mid_lat + dlng * scale
    perp_lng = mid_lng - dlat * scale
    return (perp_lat, perp_lng)


async def _fetch_osrm_via_waypoint(
    start: tuple[float, float], end: tuple[float, float], waypoint: tuple[float, float]
) -> dict | None:
    """Fetch a single OSRM route forced through a waypoint."""
    coords = f"{start[1]},{start[0]};{waypoint[1]},{waypoint[0]};{end[1]},{end[0]}"
    url = f"{OSRM_URL}/{coords}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={
                "overview": "full", "geometries": "geojson",
            }, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            r = data["routes"][0]
            return {
                "geometry": r["geometry"],
                "duration_seconds": r["duration"],
                "distance_meters": r["distance"],
            }
    except Exception:
        pass
    return None


async def fetch_osrm_routes(
    start: tuple[float, float], end: tuple[float, float]
) -> list[dict]:
    """Call OSRM and return up to 3 alternative routes with geometry + duration.
    If OSRM doesn't return enough alternatives, generate them via offset waypoints."""
    # OSRM expects lng,lat order
    coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"
    url = f"{OSRM_URL}/{coords}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "alternatives": "true",
            },
            headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("OSRM could not find a route between these locations.")

    routes = []
    for r in data["routes"][:3]:
        routes.append({
            "geometry": r["geometry"],  # GeoJSON LineString
            "duration_seconds": r["duration"],
            "distance_meters": r["distance"],
        })

    # If we got fewer than 2 routes, generate alternatives via offset waypoints
    if len(routes) < 2:
        dist_km = haversine(start[0], start[1], end[0], end[1])
        # Offset distance scales with route length (min 1km, max 10km)
        offset_km = max(1.0, min(10.0, dist_km * 0.15))
        # Try two offsets: one on each side of the direct line
        offsets = [
            _offset_point(start, end, 0.5, offset_km),
            _offset_point(start, end, 0.5, -offset_km),
        ]
        for wp in offsets:
            if len(routes) >= 3:
                break
            alt = await _fetch_osrm_via_waypoint(start, end, wp)
            if alt and alt["distance_meters"] > 0:
                # Only add if meaningfully different from existing routes (>5% distance difference)
                dominated = False
                for existing in routes:
                    ratio = alt["distance_meters"] / max(existing["distance_meters"], 1)
                    if 0.95 < ratio < 1.05:
                        dominated = True
                        break
                if not dominated:
                    routes.append(alt)

    return routes


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))




def sample_route_points(geometry: dict, n: int = 5) -> list[tuple[float, float]]:
    """Evenly sample n points from a GeoJSON LineString geometry."""
    coords = geometry["coordinates"]  # list of [lng, lat]
    if len(coords) <= n:
        return [(c[1], c[0]) for c in coords]

    step = (len(coords) - 1) / (n - 1)
    points = []
    for i in range(n):
        idx = int(round(i * step))
        c = coords[idx]
        points.append((c[1], c[0]))  # (lat, lng)
    return points




POLLUTANT_FIELDS = ["pm2_5", "pm10", "nitrogen_dioxide", "ozone", "carbon_monoxide", "sulphur_dioxide"]
POLLUTANT_LABELS = {"pm2_5": "PM2.5", "pm10": "PM10", "nitrogen_dioxide": "NO2", "ozone": "O3", "carbon_monoxide": "CO", "sulphur_dioxide": "SO2"}

# Weights reflect relative health danger (PM2.5 most harmful)
POLLUTANT_WEIGHTS = {"pm2_5": 3.0, "pm10": 1.0, "nitrogen_dioxide": 2.0, "ozone": 1.5, "carbon_monoxide": 0.5, "sulphur_dioxide": 1.0}


def _estimate_pollutants_from_aqi(aqi: int) -> dict:
    """Estimate pollutant concentrations from AQI using EPA breakpoints.
    Not exact, but much better than showing zeros when rate-limited."""
    ratio = aqi / 150.0  # normalize around "unhealthy for sensitive" level
    return {
        "pm2_5": round(max(0, aqi * 0.25), 1),       # ~35 ug/m3 at AQI 150
        "pm10": round(max(0, aqi * 0.55), 1),         # ~80 ug/m3 at AQI 150
        "nitrogen_dioxide": round(max(0, ratio * 60), 1),  # ~60 ug/m3
        "ozone": round(max(0, ratio * 120), 1),       # ~120 ug/m3
        "carbon_monoxide": round(max(0, ratio * 4), 1),    # ~4 mg/m3
        "sulphur_dioxide": round(max(0, ratio * 20), 1),   # ~20 ug/m3
    }


def _parse_point_data(item: dict) -> dict:
    """Extract AQI and pollutant values from one Open-Meteo response item."""
    current = item.get("current", {})
    aqi = int(current.get("us_aqi") or 100)
    pollutants = {}
    for field in POLLUTANT_FIELDS:
        pollutants[field] = float(current.get(field) or 0)
    return {"aqi": aqi, "pollutants": pollutants}


def _compute_health_score(pollutants: dict) -> float:
    """Weighted health score from pollutant concentrations."""
    return sum(pollutants.get(k, 0) * POLLUTANT_WEIGHTS[k] for k in POLLUTANT_FIELDS)


async def fetch_aqi_for_points(points: list[tuple[float, float]], zone_data: dict = None) -> list[dict]:
    """Fetch real AQI + pollutants from Open-Meteo for a list of (lat, lng) points.
    Returns list of {aqi, pollutants, health_score} per point.
    Falls back to nearest zone's AQI from pipeline data if rate limited."""
    lats = ",".join(str(p[0]) for p in points)
    lngs = ",".join(str(p[1]) for p in points)
    current_fields = ",".join(["us_aqi"] + POLLUTANT_FIELDS)
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(AIR_QUALITY_URL, params={
                    "latitude": lats, "longitude": lngs, "current": current_fields,
                }, headers=HEADERS)
                if resp.status_code == 429 and attempt == 0:
                    await asyncio.sleep(3)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    results = [_parse_point_data(item) for item in data]
                elif isinstance(data, dict) and "current" in data:
                    results = [_parse_point_data(data)]
                else:
                    results = []
                for r in results:
                    r["health_score"] = _compute_health_score(r["pollutants"])
                return results
        except Exception as e:
            print(f"[CustomRouter] Open-Meteo AQI fetch error (attempt {attempt+1}): {e}")

    # Fallback: use nearest zone AQI from pipeline data (no pollutant detail)
    fallback = []
    for p in points:
        aqi = _nearest_zone_aqi(p[0], p[1], zone_data) if zone_data else 100
        pollutants = _estimate_pollutants_from_aqi(aqi)
        fallback.append({"aqi": aqi, "pollutants": pollutants, "health_score": _compute_health_score(pollutants)})
    return fallback


def _nearest_zone_aqi(lat: float, lng: float, zone_data: dict) -> int:
    """Find AQI of the nearest zone in pipeline data."""
    from config import CITIES
    best_aqi = 100
    best_dist = float("inf")
    for city_cfg in CITIES.values():
        for zone_name, z in city_cfg.get("zones", {}).items():
            d = haversine(lat, lng, z["lat"], z["lng"])
            if d < best_dist and zone_name in zone_data:
                best_dist = d
                best_aqi = zone_data[zone_name].get("aqi", 100)
    return best_aqi


NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

# Cache reverse geocode results — coords rounded to ~1km so nearby points reuse names
_geocode_cache: dict[str, str] = {}

# Pre-build a lookup of all known zone coords for fast local matching
_KNOWN_ZONES: list[tuple[float, float, str]] = []
for _city_data in CITIES.values():
    for _zone_name, _zone_data in _city_data.get("zones", {}).items():
        _KNOWN_ZONES.append((_zone_data["lat"], _zone_data["lng"], _zone_name))


def _nearest_known_zone(lat: float, lng: float, threshold_km: float = 3.0) -> str | None:
    """Return zone name if a known zone is within threshold_km, else None."""
    best_name, best_dist = None, float("inf")
    for zlat, zlng, zname in _KNOWN_ZONES:
        dist = haversine(lat, lng, zlat, zlng)
        if dist < best_dist:
            best_dist, best_name = dist, zname
    return best_name if best_dist <= threshold_km else None


def _cache_key(lat: float, lng: float) -> str:
    """Round to ~1km grid for caching."""
    return f"{lat:.2f},{lng:.2f}"


async def _reverse_geocode_name(lat: float, lng: float) -> str:
    """Get a short area name for a coordinate.
    First tries matching to a known zone (instant), then falls back to Nominatim."""
    key = _cache_key(lat, lng)
    if key in _geocode_cache:
        return _geocode_cache[key]

    # Fast path: match to a known zone from our config
    known = _nearest_known_zone(lat, lng)
    if known:
        _geocode_cache[key] = known
        return known

    async with _nominatim_lock:
        if key in _geocode_cache:
            return _geocode_cache[key]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(NOMINATIM_REVERSE_URL, params={
                    "lat": lat, "lon": lng, "format": "json", "zoom": 18,
                    "addressdetails": 1,
                }, headers=HEADERS)
                resp.raise_for_status()
                data = resp.json()
                addr = data.get("address", {})
                name = (
                    addr.get("suburb")
                    or addr.get("neighbourhood")
                    or addr.get("quarter")
                    or addr.get("village")
                    or addr.get("town")
                    or addr.get("city_district")
                    or addr.get("city")
                    or f"Area {lat:.2f}"
                )
                _geocode_cache[key] = name
                return name
        except Exception:
            fallback = f"Area {lat:.2f}"
            _geocode_cache[key] = fallback
            return fallback


async def _group_segments(points: list[tuple[float, float]], point_data: list[dict], total_duration_min: float, traffic_factor: float = 1.0) -> list[dict]:
    """Group consecutive route points into ~5 segments with real area names and pollutant breakdown."""
    n = len(points)
    if n == 0:
        return []
    num_segments = min(5, n)
    boundaries = [round(i * n / num_segments) for i in range(num_segments + 1)]
    segments = []
    midpoints = []
    for s in range(num_segments):
        start_idx, end_idx = boundaries[s], boundaries[s + 1]
        if start_idx >= end_idx:
            continue
        chunk = point_data[start_idx:end_idx]
        chunk_points = points[start_idx:end_idx]
        avg_aqi = round(sum(d["aqi"] for d in chunk) / len(chunk))
        # Average each pollutant across the chunk
        avg_pollutants = {}
        for field in POLLUTANT_FIELDS:
            avg_pollutants[field] = round(sum(d["pollutants"].get(field, 0) for d in chunk) / len(chunk), 1)
        avg_health_score = round(sum(d.get("health_score", 0) for d in chunk) / len(chunk), 1)
        time_minutes = round(total_duration_min * len(chunk) / n)
        if time_minutes == 0:
            time_minutes = 1
        mid = chunk_points[len(chunk_points) // 2]
        midpoints.append(mid)
        segments.append({
            "zone": "",
            "aqi": avg_aqi,
            "time_minutes": time_minutes,
            "traffic_factor": traffic_factor,
            "zone_exposure": round(avg_aqi * time_minutes * traffic_factor, 1),
            "health_score": avg_health_score,
            "pollutants": {POLLUTANT_LABELS[k]: v for k, v in avg_pollutants.items()},
            "lat": mid[0],
            "lng": mid[1],
        })

    # Reverse geocode all midpoints for area names
    seen_names = {}
    for i, mid in enumerate(midpoints):
        name = _nearest_known_zone(mid[0], mid[1]) or f"Segment {i+1}"  # await _reverse_geocode_name(mid[0], mid[1])
        # Deduplicate: if same area name appears twice, add a number
        if name in seen_names:
            seen_names[name] += 1
            segments[i]["zone"] = f"{name} ({seen_names[name]})"
        else:
            seen_names[name] = 1
            segments[i]["zone"] = name

    return segments


async def calculate_custom_route_exposure(
    route: dict, index: int, zone_data: dict = None
) -> dict:
    """
    Fetch real AQI from Open-Meteo for sampled points along the route,
    compute exposure = sum(segment_aqi * time_minutes).
    Works for any route, anywhere — no hardcoded zones needed.
    Falls back to pipeline zone data if Open-Meteo is rate limited.
    """
    distance_km = route["distance_meters"] / 1000.0
    n_samples = max(5, int(distance_km / 10))  # 1 per 10km, min 5
    points = sample_route_points(route["geometry"], n=n_samples)
    total_duration_min = route["duration_seconds"] / 60.0

    # Traffic factor from OSRM speed: slower route = more congestion = worse exposure
    avg_speed_kmh = distance_km / max(total_duration_min / 60, 0.01)
    if avg_speed_kmh < 20:
        traffic_factor = 1.5   # heavy congestion
    elif avg_speed_kmh < 40:
        traffic_factor = 1.2   # moderate traffic
    else:
        traffic_factor = 1.0   # free flowing

    # Fetch real AQI + pollutants for each sample point
    point_data = await fetch_aqi_for_points(points, zone_data=zone_data)

    # Group into display segments with real area names
    zone_details = await _group_segments(points, point_data, total_duration_min, traffic_factor)

    total_exposure = sum(seg["zone_exposure"] for seg in zone_details)
    total_time = sum(seg["time_minutes"] for seg in zone_details)

    # Route-level average pollutants
    avg_pollutants = {}
    for field in POLLUTANT_FIELDS:
        vals = [d["pollutants"].get(field, 0) for d in point_data]
        avg_pollutants[POLLUTANT_LABELS[field]] = round(sum(vals) / max(len(vals), 1), 1)
    avg_health_score = round(sum(d.get("health_score", 0) for d in point_data) / max(len(point_data), 1), 1)

    distance_km = round(route["distance_meters"] / 1000, 1)
    route_label = f"Route {index + 1} ({distance_km} km, {total_time} min)"

    return {
        "route_name": route_label,
        "total_exposure": round(total_exposure, 1),
        "total_time_minutes": total_time,
        "avg_exposure_per_minute": round(total_exposure / max(total_time, 1), 1),
        "health_score": avg_health_score,
        "pollutants": avg_pollutants,
        "zone_details": zone_details,
    }


async def get_custom_routes(start_input: str, end_input: str, zone_data: dict = None) -> dict:
    """
    Orchestrator: geocode -> OSRM -> fetch real AQI -> exposure calculation.
    Falls back to pipeline zone_data if Open-Meteo is rate limited.
    Returns same shape as calculate_all_routes() so RouteComparison.jsx works as-is.
    """
    start_coords = await geocode_or_parse(start_input)
    end_coords = await geocode_or_parse(end_input)

    osrm_routes = await fetch_osrm_routes(start_coords, end_coords)

    # Pre-warm the geocode cache: collect all segment midpoints across all routes
    # and reverse-geocode unique ones upfront (avoids re-geocoding shared areas)
    all_midpoints = set()
    for route in osrm_routes:
        distance_km = route["distance_meters"] / 1000.0
        n_samples = max(5, int(distance_km / 10))
        points = sample_route_points(route["geometry"], n=n_samples)
        n = len(points)
        num_segments = min(5, n)
        seg_size = max(1, n // num_segments)
        for j in range(0, n, seg_size):
            chunk = points[j:j + seg_size]
            mid = chunk[len(chunk) // 2]
            all_midpoints.add(_cache_key(mid[0], mid[1]))

    # Geocode only uncached midpoints
    # for key in all_midpoints:
    #     if key not in _geocode_cache:
    #         lat, lng = (float(x) for x in key.split(","))
    #         await _reverse_geocode_name(lat, lng)

    results = []
    for i, route in enumerate(osrm_routes):
        result = await calculate_custom_route_exposure(route, i, zone_data=zone_data)
        # Attach geometry for map rendering (GeoJSON coords are [lng, lat])
        result["geometry"] = route["geometry"]
        results.append(result)

    results.sort(key=lambda r: r["total_exposure"])

    best = results[0]["route_name"] if results else None
    worst = results[-1]["route_name"] if results else None

    # Health score based on avg AQI exposure per minute of best route
    if results:
        avg_exp = results[0]["avg_exposure_per_minute"]
        health_score = max(0, min(100, int(100 - (avg_exp - 50) * 100 / 450)))
    else:
        health_score = 50

    savings_pct = (
        round(
            (1 - results[0]["total_exposure"] / max(results[-1]["total_exposure"], 1))
            * 100,
            1,
        )
        if len(results) >= 2
        else 0
    )

    return {
        "routes": results,
        "recommended": best,
        "avoid": worst,
        "health_score": health_score,
        "savings_pct": savings_pct,
        "start": start_input,
        "end": end_input,
        "start_coords": [start_coords[0], start_coords[1]],
        "end_coords": [end_coords[0], end_coords[1]],
    }
