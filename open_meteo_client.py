#!/usr/bin/env python3
"""
Open-Meteo fallback client for airports without METAR data.
Fetches current weather conditions and estimates flight categories.
"""

import urllib.request
import json
import logging
from typing import Dict, List, Optional

from metar_processor import determine_flight_category_from_values

logger = logging.getLogger("open_meteo_client")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _meters_to_statute_miles(meters: float) -> float:
    return meters / 1609.34


def _estimate_ceiling_from_cloud_cover(cloud_cover_low: float, cloud_cover_mid: float) -> Optional[int]:
    """Estimate ceiling height from cloud cover percentages.

    This is a rough heuristic — real ceilings require ceilometer data.
    Returns estimated ceiling in feet, or None if sky appears clear/few.
    """
    # BKN/OVC is typically >= 60% coverage
    if cloud_cover_low >= 60:
        return 1500  # Conservative low-layer estimate
    if cloud_cover_low >= 30:
        return 2500  # SCT-BKN low layer
    if cloud_cover_mid >= 60:
        return 8000  # Mid-layer ceiling
    return None  # No significant ceiling detected


def fetch_open_meteo_weather(airports: List[Dict]) -> Dict[str, Dict]:
    """Fetch current weather from Open-Meteo for a list of airports.

    Args:
        airports: List of airport config dicts, each must have 'icao', 'latitude', 'longitude'

    Returns:
        Dict mapping ICAO to processed weather data compatible with airport_data_manager format
    """
    results = {}

    # Open-Meteo supports multi-location in one call
    lats = []
    lons = []
    valid_airports = []
    for ap in airports:
        lat = ap.get("latitude")
        lon = ap.get("longitude")
        if lat is not None and lon is not None:
            lats.append(str(lat))
            lons.append(str(lon))
            valid_airports.append(ap)

    if not valid_airports:
        return results

    params = (
        f"latitude={','.join(lats)}"
        f"&longitude={','.join(lons)}"
        "&current=temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,"
        "cloud_cover,cloud_cover_low,cloud_cover_mid,visibility,weather_code"
        "&wind_speed_unit=kn"
    )
    url = f"{OPEN_METEO_URL}?{params}"

    try:
        logger.info("Fetching Open-Meteo data for %d airports", len(valid_airports))
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req, timeout=15)
        data = json.loads(response.read())
    except Exception as e:
        logger.error("Open-Meteo request failed: %s", e)
        return results

    # Single location returns a dict; multiple returns a list
    if isinstance(data, dict):
        data = [data]

    for i, ap in enumerate(valid_airports):
        try:
            current = data[i].get("current", {})
            icao = ap["icao"]

            visibility_m = current.get("visibility")
            visibility_mi = _meters_to_statute_miles(visibility_m) if visibility_m is not None else None

            cloud_low = current.get("cloud_cover_low", 0)
            cloud_mid = current.get("cloud_cover_mid", 0)
            ceiling = _estimate_ceiling_from_cloud_cover(cloud_low, cloud_mid)

            flight_category = determine_flight_category_from_values(visibility_mi, ceiling)

            wind_speed = current.get("wind_speed_10m")
            wind_dir = current.get("wind_direction_10m")
            wind_gusts = current.get("wind_gusts_10m")
            cloud_cover = current.get("cloud_cover", 0)

            # Build a pseudo raw text for display
            raw_parts = [f"Open-Meteo estimate"]
            if visibility_mi is not None:
                raw_parts.append(f"Vis:{visibility_mi:.1f}SM")
            if wind_speed is not None:
                wind_str = f"{int(wind_dir or 0):03d}{int(wind_speed):02d}"
                if wind_gusts and wind_gusts > wind_speed + 5:
                    wind_str += f"G{int(wind_gusts)}"
                wind_str += "KT"
                raw_parts.append(wind_str)
            raw_parts.append(f"Clouds:{cloud_cover}%")
            if ceiling:
                raw_parts.append(f"EstCeil:{ceiling}ft")
            raw_text = " ".join(raw_parts)

            results[icao] = {
                "raw_metar": raw_text,
                "flight_category": flight_category,
                "name": ap.get("name", icao),
                "estimated": True,
                "wind_data": {
                    "speed": wind_speed,
                    "direction": wind_dir,
                    "gusts": wind_gusts,
                    "crosswind": None,
                },
            }

            logger.info("Open-Meteo fallback for %s: %s (vis=%.1fSM, ceil=%s)",
                        icao, flight_category,
                        visibility_mi if visibility_mi else 0,
                        ceiling)
        except Exception as e:
            logger.warning("Failed to process Open-Meteo data for %s: %s", ap.get("icao"), e)

    return results
