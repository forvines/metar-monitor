#!/usr/bin/env python3
"""
Airport visit tracker using OpenSky Network live API.

Checks if tracked aircraft are on the ground near configured airports.
If found, marks the airport as visited in metar_config.json.
Maintains a visit log in visited_log.json with timestamps.

Designed to run periodically via cron (every 10-15 minutes).
Uses only the free, unauthenticated OpenSky API.
"""

import json
import math
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "metar_config.json"
VISIT_LOG_FILE = SCRIPT_DIR / "visited_log.json"
AIRPORT_CACHE_FILE = SCRIPT_DIR / "airport_coords_cache.json"

OPENSKY_API = "https://opensky-network.org/api/states/all"
AIRPORT_API = "https://aviationweather.gov/api/data/airport"

# Aircraft to track: tail number -> (icao24 hex, earliest visit date)
TRACKED_AIRCRAFT = {
    "N8279Z": {"icao24": "ab4e87", "since": "2024-09-01"},
    "N7331A": {"icao24": "a9d8ac", "since": "2026-01-01"},
}

# Maximum distance (nm) from airport to count as "at" the airport
PROXIMITY_NM = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("visit_tracker")


def nm_between(lat1, lon1, lat2, lon2):
    """Great-circle distance in nautical miles."""
    r = 3440.065  # Earth radius in nm
    lat1, lon1, lat2, lon2 = (math.radians(v) for v in (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def fetch_airport_coords(icao_ids):
    """Fetch coordinates from aviationweather API and cache them."""
    cache = load_json(AIRPORT_CACHE_FILE)
    missing = [icao for icao in icao_ids if icao not in cache]

    if missing:
        # API accepts comma-separated IDs
        ids = ",".join(missing)
        url = f"{AIRPORT_API}?ids={ids}&format=json"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read())
            for ap in data:
                icao = ap.get("icaoId") or ap.get("stationId")
                if icao and ap.get("lat") is not None:
                    cache[icao] = {"lat": ap["lat"], "lon": ap["lon"]}
            save_json(AIRPORT_CACHE_FILE, cache)
            logger.info("Cached coordinates for %d airports", len(missing))
        except Exception as e:
            logger.warning("Failed to fetch airport coords: %s", e)

    return cache


def get_aircraft_states(icao24_list):
    """Query OpenSky for current state of tracked aircraft."""
    params = "&".join(f"icao24={h}" for h in icao24_list)
    url = f"{OPENSKY_API}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("states") or []
    except urllib.error.HTTPError as e:
        logger.warning("OpenSky API error: %s", e)
        return []
    except Exception as e:
        logger.warning("Failed to query OpenSky: %s", e)
        return []


def check_visits():
    config = load_json(CONFIG_FILE)
    if not config:
        logger.error("Could not load %s", CONFIG_FILE)
        return

    airports = config.get("airports", [])
    icao_ids = [ap["icao"] for ap in airports]

    # Get coordinates for all airports
    coords = fetch_airport_coords(icao_ids)

    # Query OpenSky for tracked aircraft
    icao24_list = [info["icao24"] for info in TRACKED_AIRCRAFT.values()]
    states = get_aircraft_states(icao24_list)

    if not states:
        logger.info("No tracked aircraft currently reporting")
        return

    # Build hex -> tail lookup
    hex_to_tail = {info["icao24"]: tail for tail, info in TRACKED_AIRCRAFT.items()}

    visit_log = load_json(VISIT_LOG_FILE)
    config_changed = False
    now = datetime.utcnow().isoformat() + "Z"

    for state in states:
        icao24 = state[0]
        on_ground = state[8]
        lat = state[6]
        lon = state[5]
        tail = hex_to_tail.get(icao24)

        if not tail or not on_ground or lat is None or lon is None:
            if tail:
                logger.info("%s (%s): airborne or no position", tail, icao24)
            continue

        logger.info("%s (%s): on ground at %.4f, %.4f", tail, icao24, lat, lon)

        # Check proximity to each airport
        for ap in airports:
            icao = ap["icao"]
            if ap.get("visited"):
                continue

            ap_coords = coords.get(icao)
            if not ap_coords:
                continue

            dist = nm_between(lat, lon, ap_coords["lat"], ap_coords["lon"])
            if dist <= PROXIMITY_NM:
                since = TRACKED_AIRCRAFT[tail]["since"]
                if now >= since:
                    logger.info("VISIT: %s at %s (%.1f nm) by %s", icao, now, dist, tail)
                    ap["visited"] = True
                    config_changed = True
                    visit_log.setdefault(icao, []).append({
                        "aircraft": tail,
                        "date": now,
                        "distance_nm": round(dist, 1),
                    })

    if config_changed:
        save_json(CONFIG_FILE, config)
        save_json(VISIT_LOG_FILE, visit_log)
        logger.info("Config updated with new visits")
    else:
        logger.info("No new visits detected")


if __name__ == "__main__":
    check_visits()
