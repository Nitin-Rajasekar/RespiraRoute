"""
Pathway streaming pipeline for real-time AQI data processing.

Uses the actual Pathway framework for:
- Live JSONL ingestion via pw.io.jsonlines connector
- Streaming transformations (groupby, reduce, filter)
- Temporal window aggregations (dual sliding windows for rolling stats + trend)
- Z-score based anomaly detection via statistical analysis
- LLM enrichment of anomalies via Pathway LLM xPack (LiteLLMChat + Groq)
- AQI trend detection via moving average crossover
- Short-term AQI forecasting via linear extrapolation
- pw.io.subscribe() to push results into thread-safe state for FastAPI

Supports multi-city data: each record has a 'city' field.
"""

import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import pathway as pw
from pathway.xpacks.llm.llms import LiteLLMChat
from pathway.udfs import ExponentialBackoffRetryStrategy

from config import CITIES
from rag_knowledge_base import retrieve_context

STREAM_DIR = os.path.join(os.path.dirname(__file__), "stream_data")


# ── Pathway Schema ──────────────────────────────────────────────────
class ZoneSchema(pw.Schema):
    city: str
    zone: str
    aqi: int
    aqi_category: str
    wind_speed_kmh: float
    temperature_c: float
    humidity_pct: int
    timestamp: str
    tick: int


# ── Shared State (thread-safe, read by FastAPI) ─────────────────────
_lock = threading.Lock()
_latest_zone_data: dict[str, dict[str, dict]] = {}
_zone_stats: dict[str, dict[str, dict]] = {}
_trend_data: dict[str, dict[str, dict]] = {}
_anomalies: dict[str, dict] = {}  # "city:zone" -> latest anomaly state
_llm_explanations: list[dict] = []
_processed_count: int = 0

# ── LLM Cooldown (per-zone, prevents Groq rate limiting) ────────────
import time as _time
_llm_cooldown: dict[str, float] = {}  # "city:zone" -> last call timestamp
_LLM_COOLDOWN_SECS = 60  # one LLM call per zone per minute


# ── Subscribe Callbacks ─────────────────────────────────────────────
def _on_zone_update(key, row: dict, time: int, is_addition: bool):
    """Callback: latest zone readings."""
    global _processed_count
    if not is_addition:
        return
    city = row.get("city", "")
    zone = row.get("zone", "")
    if not city or not zone:
        return
    with _lock:
        if city not in _latest_zone_data:
            _latest_zone_data[city] = {}
        _latest_zone_data[city][zone] = row
        _processed_count += 1


def _on_stats_update(key, row: dict, time: int, is_addition: bool):
    """Callback: long-window rolling statistics."""
    if not is_addition:
        return
    city = row.get("city", "")
    zone = row.get("zone", "")
    if not city or not zone:
        return
    with _lock:
        if city not in _zone_stats:
            _zone_stats[city] = {}
        _zone_stats[city][zone] = row


def _on_trend_update(key, row: dict, time: int, is_addition: bool):
    """Callback: trend + forecast computed inside Pathway via join of short/long windows."""
    if not is_addition:
        return
    city = row.get("city", "")
    zone = row.get("zone", "")
    if not city or not zone:
        return
    with _lock:
        if city not in _trend_data:
            _trend_data[city] = {}
        _trend_data[city][zone] = {
            "city": city,
            "zone": zone,
            "short_avg_aqi": row.get("short_avg_aqi", 0),
            "long_avg_aqi": row.get("avg_aqi", 0),
            "trend": row.get("trend", "stable"),
            "forecast_aqi": row.get("forecast_aqi", 0),
        }


def _aqi_description(aqi: int) -> str:
    if aqi <= 50:   return "good air quality"
    if aqi <= 100:  return "moderate air quality"
    if aqi <= 150:  return "unhealthy conditions for sensitive groups"
    if aqi <= 200:  return "unhealthy air quality"
    if aqi <= 300:  return "very unhealthy air quality"
    return "hazardous air quality"


def _rule_based_explanation(zone: str, city: str, aqi: int, mean: float, zscore: float,
                             row: dict) -> str:
    wind = row.get("wind_speed_kmh", 0)
    temp = row.get("temperature_c", 0)
    desc = _aqi_description(aqi)
    above = round(aqi - mean, 1)
    parts = [
        f"{zone} ({city}) is recording AQI {aqi} — {desc}.",
    ]
    if abs(zscore) > 2.0:
        parts.append(f"This is a significant spike: {above:.0f} points above the city average of {mean:.0f} (z={zscore:+.1f}).")
    elif above > 5:
        parts.append(f"AQI is {above:.0f} points above the city average of {mean:.0f}.")
    if wind < 5:
        parts.append("Low wind speeds are limiting pollutant dispersal, causing local accumulation.")
    elif wind > 20:
        parts.append("Strong winds may be transporting pollutants from nearby industrial areas.")
    if temp > 35:
        parts.append("High temperatures are accelerating secondary pollutant formation.")
    if aqi > 150:
        parts.append("Sensitive groups should avoid outdoor activity; others should limit prolonged exertion.")
    elif aqi > 100:
        parts.append("Sensitive individuals (children, elderly, those with respiratory conditions) should reduce outdoor time.")
    return " ".join(parts)


def _on_anomaly(key, row: dict, time: int, is_addition: bool):
    """Callback: anomaly alerts with cross-zone z-score (how far above city average)."""
    if not is_addition:
        return
    city = row.get("city", "Unknown")
    zone = row.get("zone", "Unknown")
    aqi = row.get("aqi", 0)

    with _lock:
        # Cross-zone z-score: compare this zone against all zones in same city
        city_aqis = [z.get("aqi", 0) for z in _latest_zone_data.get(city, {}).values() if z.get("aqi")]
        if len(city_aqis) >= 2:
            mean = sum(city_aqis) / len(city_aqis)
            std = (sum((x - mean) ** 2 for x in city_aqis) / len(city_aqis)) ** 0.5
            zscore = round((aqi - mean) / std, 2) if std > 1.0 else 0.0
        else:
            mean = aqi
            zscore = 0.0

        ts = row.get("timestamp", datetime.now(timezone.utc).isoformat())
        _anomalies[f"{city}:{zone}"] = {
            "city": city,
            "zone": zone,
            "aqi": aqi,
            "avg_aqi": round(mean, 1),
            "zscore": zscore,
            "timestamp": ts,
            "type": "zscore_spike" if abs(zscore) > 2.0 else "high_aqi",
            "message": (
                f"{'Z-score' if abs(zscore) > 2.0 else 'AQI'} anomaly in "
                f"{zone} ({city}): AQI {aqi}, z={zscore:.1f}"
            ),
        }

        # Pre-populate insights with rule-based explanation so UI always shows content.
        # If the Pathway LLM subscription fires later, _on_llm_explanation will append
        # richer LLM-generated text on top.
        explanation = _rule_based_explanation(zone, city, aqi, mean, zscore, row)
        # Overwrite any previous entry for this city:zone key
        _llm_explanations[:] = [
            e for e in _llm_explanations if not (e.get("city") == city and e.get("zone") == zone)
        ]
        _llm_explanations.append({
            "city": city,
            "zone": zone,
            "aqi": aqi,
            "zscore": zscore,
            "explanation": explanation,
            "timestamp": ts,
            "source": "pathway_rule_based",
        })
        if len(_llm_explanations) > 30:
            del _llm_explanations[:-30]


def _on_llm_explanation(key, row: dict, time: int, is_addition: bool):
    """Callback: LLM-generated anomaly explanations from async UDF."""
    if not is_addition:
        return
    city = row.get("city", "")
    zone = row.get("zone", "")
    explanation = row.get("llm_explanation", "")
    if not explanation or not city or not zone:
        return
    with _lock:
        # Replace any existing entry for this zone with the richer LLM version
        _llm_explanations[:] = [
            e for e in _llm_explanations if not (e.get("city") == city and e.get("zone") == zone)
        ]
        _llm_explanations.append({
            "city": city,
            "zone": zone,
            "aqi": row.get("aqi", 0),
            "zscore": round(float(row.get("zscore") or 0), 2),
            "explanation": explanation,
            "timestamp": row.get("timestamp", ""),
            "source": "pathway_llm_udf",
        })


# ── UDFs (computed columns inside Pathway dataflow) ─────────────────
@pw.udf
def compute_volatility(sum_sq: float, count: int, mean: float) -> float:
    """Standard deviation from sum-of-squares (online algorithm)."""
    if count < 2:
        return 0.0
    variance = sum_sq / count - mean * mean
    return round(max(0.0, variance) ** 0.5, 1)


@pw.udf
def compute_zscore(aqi: int, avg_aqi: float, volatility: float) -> float:
    """Z-score: how many standard deviations from rolling mean."""
    if volatility < 1.0:
        return 0.0
    return round((aqi - avg_aqi) / volatility, 2)


@pw.udf
def classify_trend(short_avg: float, long_avg: float) -> str:
    """Detect trend via moving average crossover (short vs long window)."""
    if long_avg < 1:
        return "stable"
    diff_pct = (short_avg - long_avg) / long_avg * 100
    if diff_pct > 5:
        return "worsening"
    elif diff_pct < -5:
        return "improving"
    return "stable"


@pw.udf
def forecast_aqi(short_avg: float, long_avg: float) -> int:
    """1-hour AQI forecast: capped ±15% change from current short-window avg."""
    rate_pct = (short_avg - long_avg) / max(long_avg, 1)
    rate_pct = max(-0.15, min(0.15, rate_pct))
    return max(5, min(500, int(round(short_avg * (1 + rate_pct)))))


# ── LLM Cooldown UDF — gates LLM to once per zone per 5 minutes ────
@pw.udf
def check_llm_cooldown(zone: str, city: str) -> bool:
    """Return True (allow LLM call) only if zone hasn't been called recently."""
    key = f"{city}:{zone}"
    now = _time.time()
    if key in _llm_cooldown and (now - _llm_cooldown[key]) < _LLM_COOLDOWN_SECS:
        return False
    _llm_cooldown[key] = now
    return True


# ── Pathway LLM xPack — Groq via LiteLLMChat ──────────────────────
_llm_chat = LiteLLMChat(
    model="groq/llama-3.3-70b-versatile",
    retry_strategy=ExponentialBackoffRetryStrategy(max_retries=2),
    temperature=0.5,
)


@pw.udf
def build_anomaly_prompt(
    zone: str, city: str, aqi: int, avg_aqi: float, zscore: float,
    wind_speed_kmh: float, temperature_c: float,
) -> pw.Json:
    """Build chat messages for the Pathway LLM xPack to explain an anomaly."""
    if aqi <= 100:
        severity = "moderate"
    elif aqi <= 150:
        severity = "unhealthy for sensitive groups"
    elif aqi <= 200:
        severity = "unhealthy"
    else:
        severity = "very unhealthy/hazardous"

    wind_desc = "calm/stagnant" if wind_speed_kmh < 5 else ("moderate" if wind_speed_kmh < 15 else "strong")

    # RAG: retrieve zone + city + health guideline context
    retrieved = retrieve_context(zone, city, aqi)

    prompt = (
        f"You are analyzing a SPECIFIC air quality anomaly. Give a unique, specific explanation.\n\n"
        f"LIVE DATA:\n"
        f"  Zone: {zone} in {city}\n"
        f"  AQI: {aqi} ({severity}) | Rolling avg: {avg_aqi:.0f} | Z-score: {zscore:.1f}\n"
        f"  Conditions: Wind {wind_speed_kmh} km/h ({wind_desc}), Temp: {temperature_c}°C\n\n"
        f"RETRIEVED CONTEXT (use this to ground your explanation):\n{retrieved}\n\n"
        f"Instructions:\n"
        f"- Start with the zone name '{zone}'\n"
        f"- Name the SPECIFIC pollution source for this zone based on the retrieved context\n"
        f"- Explain how current wind/temp conditions interact with local sources\n"
        f"- Give ONE specific actionable health tip informed by the CPCB advisory above\n"
        f"- Keep it to 2-3 sentences. Do NOT repeat the retrieved text verbatim.\n"
    )

    return pw.Json([
        {"role": "system", "content": (
            "You are an urban air quality scientist with deep knowledge of Indian cities. "
            "You are given live sensor data AND retrieved context about the zone and health guidelines. "
            "Use the retrieved context to give grounded, specific explanations — not generic ones. "
            "Each zone has unique pollution sources; never give the same explanation for different zones."
        )},
        {"role": "user", "content": prompt},
    ])


# ── Build the Pathway Dataflow Graph ────────────────────────────────
def _build_and_run():
    """Construct the Pathway pipeline and call pw.run() (blocking)."""

    # ─── Stage 1: INGEST — read streaming JSONL ───────────────────
    zone_data = pw.io.jsonlines.read(
        STREAM_DIR,
        schema=ZoneSchema,
        mode="streaming",
        autocommit_duration_ms=1500,
    )

    # ─── Stage 2a: LONG WINDOW — rolling stats (10-tick window) ───
    zone_stats_long = zone_data.windowby(
        zone_data.tick,
        window=pw.temporal.sliding(duration=10, hop=1),
        instance=pw.this.zone,
    ).reduce(
        zone=pw.this._pw_instance,
        avg_aqi=pw.reducers.avg(pw.this.aqi),
        max_aqi=pw.reducers.max(pw.this.aqi),
        min_aqi=pw.reducers.min(pw.this.aqi),
        count=pw.reducers.count(),
        sum_sq_aqi=pw.reducers.sum(pw.this.aqi * pw.this.aqi),
        city=pw.reducers.max(pw.this.city),
    )

    zone_stats_enriched = zone_stats_long.select(
        pw.this.city,
        pw.this.zone,
        pw.this.avg_aqi,
        pw.this.max_aqi,
        pw.this.min_aqi,
        pw.this.count,
        aqi_volatility=compute_volatility(
            pw.this.sum_sq_aqi, pw.this.count, pw.this.avg_aqi
        ),
    )

    # ─── Stage 2b: SHORT WINDOW — recent trend (3-tick window) ────
    zone_stats_short = zone_data.windowby(
        zone_data.tick,
        window=pw.temporal.sliding(duration=3, hop=1),
        instance=pw.this.zone,
    ).reduce(
        zone=pw.this._pw_instance,
        short_avg_aqi=pw.reducers.avg(pw.this.aqi),
        city=pw.reducers.max(pw.this.city),
    )

    # ─── Stage 2c: JOIN short + long windows — trend, forecast, z-score ──
    # Incremental join: every time either window updates, Pathway recomputes
    joined_stats = zone_stats_short.join(
        zone_stats_enriched,
        pw.left.zone == pw.right.zone,
    ).select(
        city=pw.left.city,
        zone=pw.left.zone,
        short_avg_aqi=pw.left.short_avg_aqi,
        avg_aqi=pw.right.avg_aqi,
        aqi_volatility=pw.right.aqi_volatility,
        trend=classify_trend(pw.left.short_avg_aqi, pw.right.avg_aqi),
        forecast_aqi=forecast_aqi(pw.left.short_avg_aqi, pw.right.avg_aqi),
    )

    # ─── Stage 3: ANOMALY DETECTION — threshold + z-score via join ───
    anomalies_raw = zone_data.filter(pw.this.aqi > 100)

    # Join anomalies with rolling stats to compute z-score inside Pathway
    anomalies = anomalies_raw.join(
        zone_stats_enriched,
        pw.left.zone == pw.right.zone,
    ).select(
        city=pw.left.city,
        zone=pw.left.zone,
        aqi=pw.left.aqi,
        timestamp=pw.left.timestamp,
        avg_aqi=pw.right.avg_aqi,
        aqi_volatility=pw.right.aqi_volatility,
        zscore=compute_zscore(pw.left.aqi, pw.right.avg_aqi, pw.right.aqi_volatility),
    )

    # LLM only fires for severe anomalies (AQI > 100) to avoid rate limits
    severe_anomalies = zone_data.filter(pw.this.aqi > 100)

    # Join severe anomalies with stats for real avg_aqi and zscore in prompts
    severe_with_stats = severe_anomalies.join(
        zone_stats_enriched,
        pw.left.zone == pw.right.zone,
    ).select(
        city=pw.left.city,
        zone=pw.left.zone,
        aqi=pw.left.aqi,
        wind_speed_kmh=pw.left.wind_speed_kmh,
        temperature_c=pw.left.temperature_c,
        timestamp=pw.left.timestamp,
        avg_aqi=pw.right.avg_aqi,
        zscore=compute_zscore(pw.left.aqi, pw.right.avg_aqi, pw.right.aqi_volatility),
    )

    # Throttle: only call LLM once per zone per 5 minutes
    severe_throttled = severe_with_stats.filter(
        check_llm_cooldown(pw.this.zone, pw.this.city)
    )

    # Pathway LLM xPack enrichment using real rolling stats
    anomaly_prompts = severe_throttled.select(
        pw.this.city,
        pw.this.zone,
        pw.this.aqi,
        pw.this.timestamp,
        pw.this.avg_aqi,
        pw.this.zscore,
        prompt=build_anomaly_prompt(
            pw.this.zone, pw.this.city, pw.this.aqi,
            pw.this.avg_aqi, pw.this.zscore,
            pw.this.wind_speed_kmh,
            pw.this.temperature_c,
        ),
    )
    anomalies_explained = anomaly_prompts.select(
        pw.this.city,
        pw.this.zone,
        pw.this.aqi,
        pw.this.timestamp,
        pw.this.avg_aqi,
        pw.this.zscore,
        llm_explanation=_llm_chat(pw.this.prompt),
    )

    # ─── Stage 4: OUTPUT — subscribe to push into shared state ────
    pw.io.subscribe(zone_data, on_change=_on_zone_update)
    pw.io.subscribe(zone_stats_enriched, on_change=_on_stats_update)
    pw.io.subscribe(joined_stats, on_change=_on_trend_update)
    pw.io.subscribe(anomalies, on_change=_on_anomaly)
    pw.io.subscribe(anomalies_explained, on_change=_on_llm_explanation)

    pw.run()


# ── Pipeline Wrapper ────────────────────────────────────────────────
class PathwayPipeline:
    """
    Wraps the real Pathway pipeline. Runs pw.run() in a daemon thread
    and exposes get_latest_state() / get_zone_data_dict() for FastAPI.
    """

    def __init__(self):
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the Pathway engine in a background thread."""
        self._thread = threading.Thread(target=_build_and_run, daemon=True)
        self._thread.start()
        print("[Pipeline] Started Pathway streaming pipeline")

    def stop(self):
        print("[Pipeline] Stopped")

    def _merge_zone(self, city: str, zone_name: str, data: dict) -> dict:
        """Merge raw zone data with rolling stats + trend + forecast."""
        merged = dict(data)
        stats = _zone_stats.get(city, {}).get(zone_name, {})
        trend_info = _trend_data.get(city, {}).get(zone_name, {})

        if stats:
            merged["aqi_rolling_avg"] = round(stats.get("avg_aqi", data.get("aqi", 0)), 1)
            merged["aqi_min_window"] = stats.get("min_aqi", data.get("aqi", 0))
            merged["aqi_max_window"] = stats.get("max_aqi", data.get("aqi", 0))
            merged["aqi_volatility"] = stats.get("aqi_volatility", 0)
        else:
            merged["aqi_rolling_avg"] = data.get("aqi", 0)
            merged["aqi_volatility"] = 0

        # Pathway-computed trend (from moving average crossover)
        if trend_info:
            merged["aqi_trend"] = trend_info.get("trend", "stable")
            merged["short_avg_aqi"] = round(trend_info.get("short_avg_aqi", 0), 1)
            merged["forecast_aqi"] = trend_info.get("forecast_aqi", data.get("aqi", 0))
        else:
            merged["aqi_trend"] = "stable"
            merged["forecast_aqi"] = data.get("aqi", 0)

        return merged

    def get_city_overview(self) -> dict:
        """Get one record per city (city-center readings) for the overview."""
        with _lock:
            zones = {}
            for city_name in CITIES:
                city_data = _latest_zone_data.get(city_name, {})
                data = city_data.get(city_name)
                if data:
                    zones[city_name] = self._merge_zone(city_name, city_name, data)

            return {
                "zones": zones,
                "anomalies": list(_anomalies.values()),
                "processed_records": _processed_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_latest_state(self, city: str = None) -> dict:
        """Get zone data. If city given, return that city's zones."""
        if city is None:
            return self.get_city_overview()

        with _lock:
            city_data = _latest_zone_data.get(city, {})
            zones = {}
            for zone_name, data in city_data.items():
                if zone_name == city:
                    continue
                zones[zone_name] = self._merge_zone(city, zone_name, data)

            return {
                "zones": zones,
                "anomalies": [a for a in _anomalies.values() if a.get("city") == city],
                "processed_records": _processed_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_zone_data_dict(self, city: str = None) -> dict[str, dict]:
        """Get zone data as a simple dict for route calculation."""
        if city is None:
            city = "Delhi"
        with _lock:
            city_data = _latest_zone_data.get(city, {})
            return {k: dict(v) for k, v in city_data.items() if k != city}

    def get_llm_explanations(self, city: str = None) -> list[dict]:
        """Get LLM-generated anomaly explanations from Pathway pipeline."""
        with _lock:
            if city:
                return [e for e in _llm_explanations if e.get("city") == city]
            return list(_llm_explanations)


# Singleton pipeline instance
pipeline = PathwayPipeline()
