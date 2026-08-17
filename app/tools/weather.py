"""Weather, via Open-Meteo.

Chosen because it needs no API key and no account, which keeps the whole
project free. Two calls: place name to coordinates, then coordinates to
forecast.
"""
import logging

import requests

from .. import config
from . import register

log = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 15
MAX_DAYS = 7

# WMO weather codes, grouped so the model gets plain words rather than numbers.
CONDITIONS = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail",
}


def _describe_code(code) -> str:
    return CONDITIONS.get(code, f"unknown (code {code})")


def _geocode(place: str) -> dict:
    response = requests.get(
        GEOCODE_URL, params={"name": place, "count": 1, "language": "en"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise ValueError(f"Could not find a place called '{place}'")
    return results[0]


@register(
    name="get_weather",
    description=(
        "Get the weather forecast. Use for questions about rain, temperature, "
        "or whether to take an umbrella or a jacket. Temperatures are Celsius."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "Place name; defaults to the user's city"},
            "days": {"type": "integer", "description": "How many days ahead, 1 to 7"},
        },
        "required": [],
    },
)
def get_weather(chat_id: int, location: str | None = None, days: int = 1) -> dict:
    place_name = (location or config.DEFAULT_WEATHER_LOCATION).strip()
    span = max(1, min(int(days), MAX_DAYS))

    try:
        place = _geocode(place_name)
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                         "precipitation_probability_max,precipitation_sum",
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
                "forecast_days": span,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        log.warning("Weather lookup failed: %s", type(exc).__name__)
        return {"error": f"Could not reach the weather service ({type(exc).__name__})"}

    daily = data.get("daily", {})
    forecast = [
        {
            "date": daily["time"][i],
            "condition": _describe_code(daily["weather_code"][i]),
            "high_c": daily["temperature_2m_max"][i],
            "low_c": daily["temperature_2m_min"][i],
            "rain_chance_percent": daily["precipitation_probability_max"][i],
            "rain_mm": daily["precipitation_sum"][i],
        }
        for i in range(len(daily.get("time", [])))
    ]

    current = data.get("current", {})
    return {
        "location": f"{place['name']}, {place.get('country', '')}".strip(", "),
        "now": {
            "temperature_c": current.get("temperature_2m"),
            "condition": _describe_code(current.get("weather_code")),
        },
        "forecast": forecast,
    }
