"""
AI Explanation Engine for RespiraRoute.

Generates natural-language explanations about route recommendations,
pollution spikes, and health advice using the latest streamed data.

Uses litellm (same library as Pathway LLM xPack) with Groq backend,
falling back to rule-based explanations if the API is unavailable.
"""

import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

_SYSTEM_PROMPT = (
    "You are an environmental health AI assistant for RespiraRoute. "
    "Give concise, helpful explanations about air quality, route safety, "
    "and health recommendations. Use data provided. Keep responses under 150 words."
)


def _get_aqi_description(aqi: int) -> str:
    if aqi <= 50:
        return "good"
    elif aqi <= 100:
        return "moderate"
    elif aqi <= 150:
        return "unhealthy for sensitive groups"
    elif aqi <= 200:
        return "unhealthy"
    elif aqi <= 300:
        return "very unhealthy"
    return "hazardous"


def _try_llm(prompt: str) -> str | None:
    """Call LLM via litellm (same library as Pathway LLM xPack). Returns None if unavailable."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        import litellm
        litellm.suppress_debug_info = True
        response = litellm.completion(
            model="groq/llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=130,
            temperature=0.7,
            api_key=api_key,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[AI Explainer] LLM error: {e}")
        return None


def explain_route_safety(route_data: dict, zone_data: dict[str, dict]) -> str:
    """Explain why the recommended route is safer."""
    routes = route_data.get("routes", [])
    recommended = route_data.get("recommended", "")
    if not routes:
        return "No route data available yet."

    best = routes[0]
    worst = routes[-1]

    context = (
        f"Best route: {best['route_name']} (exposure: {best['total_exposure']}, "
        f"time: {best['total_time_minutes']} min). "
        f"Worst route: {worst['route_name']} (exposure: {worst['total_exposure']}, "
        f"time: {worst['total_time_minutes']} min). "
        f"Zone details for best route: {best['zone_details']}. "
        f"Savings: {route_data.get('savings_pct', 0)}%."
    )

    ai_response = _try_llm(
        f"Explain why this route is the healthiest choice for a commuter:\n{context}"
    )
    if ai_response:
        return ai_response

    # Rule-based fallback
    best_zones = best["zone_details"]
    worst_zone_in_best = max(best_zones, key=lambda z: z["aqi"])
    cleanest_zone = min(best_zones, key=lambda z: z["aqi"])

    explanation = (
        f"**{best['route_name']}** is recommended with an exposure score of "
        f"**{best['total_exposure']:,.0f}** — that's **{route_data.get('savings_pct', 0)}% less pollution exposure** "
        f"compared to {worst['route_name']} ({worst['total_exposure']:,.0f}).\n\n"
        f"This route passes through **{cleanest_zone['zone']}** (AQI: {cleanest_zone['aqi']}, "
        f"{_get_aqi_description(cleanest_zone['aqi'])}) which has significantly cleaner air. "
        f"The highest AQI zone on this route is {worst_zone_in_best['zone']} "
        f"at {worst_zone_in_best['aqi']}, but you only spend {worst_zone_in_best['time_minutes']} minutes there.\n\n"
        f"Total travel time: **{best['total_time_minutes']} minutes** — a small detour for much cleaner air."
    )
    return explanation


def explain_pollution_spike(zone_data: dict[str, dict]) -> str:
    """Explain what's causing high pollution in certain zones."""
    high_aqi_zones = [
        (name, data) for name, data in zone_data.items()
        if data.get("aqi", 0) > 150
    ]

    if not high_aqi_zones:
        all_aqis = {name: data.get("aqi", 0) for name, data in zone_data.items()}
        context = f"Current AQI readings: {all_aqis}"
        ai_response = _try_llm(
            f"All zones have moderate or good air quality. Summarize the current conditions:\n{context}"
        )
        if ai_response:
            return ai_response
        return (
            "All zones currently show **moderate to good air quality**. "
            "No significant pollution spikes detected. Enjoy the clean air!"
        )

    high_aqi_zones.sort(key=lambda x: x[1]["aqi"], reverse=True)

    context = "\n".join(
        f"- {name}: AQI {d['aqi']}, wind: {d.get('wind_speed_kmh', 'N/A')} km/h"
        for name, d in high_aqi_zones
    )

    ai_response = _try_llm(
        f"Explain the likely causes of these pollution spikes:\n{context}"
    )
    if ai_response:
        return ai_response

    # Rule-based fallback
    lines = []
    for name, data in high_aqi_zones:
        aqi = data["aqi"]
        wind = data.get("wind_speed_kmh", 0)

        causes = []
        if "Industrial" in name:
            causes.append("industrial emissions from nearby factories")
        if "Highway" in name:
            causes.append("high vehicular emissions on the highway corridor")
        if wind < 3:
            causes.append("low wind speed trapping pollutants")
        if not causes:
            causes.append("elevated baseline pollution levels")

        lines.append(
            f"**{name}** (AQI: {aqi} — {_get_aqi_description(aqi)}): "
            f"Likely caused by {', '.join(causes)}."
        )

    return "**Pollution Spike Analysis:**\n\n" + "\n\n".join(lines)


def give_health_advice(zone_data: dict[str, dict], route_data: dict) -> str:
    """Provide health recommendations based on current conditions."""
    avg_aqi = sum(d.get("aqi", 0) for d in zone_data.values()) / max(len(zone_data), 1)
    max_aqi = max((d.get("aqi", 0) for d in zone_data.values()), default=0)
    recommended = route_data.get("recommended", "the recommended route")
    health_score = route_data.get("health_score", 50)

    context = (
        f"Average city AQI: {avg_aqi:.0f}. Max zone AQI: {max_aqi}. "
        f"Recommended route: {recommended}. Health score: {health_score}/100."
    )

    ai_response = _try_llm(
        f"Give practical health advice for someone commuting in these conditions:\n{context}"
    )
    if ai_response:
        return ai_response

    # Rule-based fallback
    advice = []

    if avg_aqi > 150:
        advice.append("Consider wearing an **N95 mask** during your commute — air quality is unhealthy across multiple zones.")
        advice.append("If possible, **delay outdoor activities** until air quality improves.")
    elif avg_aqi > 100:
        advice.append("**Sensitive individuals** (asthma, heart conditions, elderly) should limit outdoor exposure.")
        advice.append("Keep car windows **closed** and use recirculated air in your vehicle.")
    else:
        advice.append("Air quality is currently **acceptable** for most people.")
        advice.append("Great time for outdoor activities — just avoid high-traffic areas.")

    advice.append(f"Take **{recommended}** for {route_data.get('savings_pct', 0)}% less pollution exposure.")

    if max_aqi > 200:
        worst_zone = max(zone_data.items(), key=lambda x: x[1].get("aqi", 0))
        advice.append(f"**Avoid {worst_zone[0]}** if possible — AQI is at {worst_zone[1]['aqi']} (very unhealthy).")

    advice.append("Stay hydrated and take breaks in well-ventilated indoor spaces.")

    now = datetime.now()
    if 7 <= now.hour <= 9 or 17 <= now.hour <= 19:
        advice.append("You're commuting during **rush hour** — expect higher pollution near roadways.")

    return "**Health Recommendations:**\n\n" + "\n\n".join(f"- {a}" for a in advice)
