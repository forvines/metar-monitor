#!/usr/bin/env python3
"""Walk through each airport LED one at a time, 3 seconds each, logging details."""
import time, json, logging
from rpi_ws281x import PixelStrip, Color

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("walk_airports_slow")

cfg = json.load(open("metar_config.json"))
strip = PixelStrip(cfg["led_count"], cfg["led_pin"], cfg["led_freq_hz"],
                   cfg["led_dma"], cfg["led_invert"], 255, cfg["led_channel"])
strip.begin()

OFF = Color(0, 0, 0)
WHITE = Color(255, 255, 255)

airports = sorted(cfg["airports"], key=lambda a: a["led"])

for ap in airports:
    # Clear all LEDs
    for i in range(cfg["led_count"]):
        strip.setPixelColor(i, OFF)
    # Light this airport
    strip.setPixelColor(ap["led"], WHITE)
    strip.show()
    logger.info("LED %2d: %s - %s (visited: %s)",
                ap["led"], ap["icao"], ap["name"], ap.get("visited", False))
    time.sleep(3)

# Clear all when done
for i in range(cfg["led_count"]):
    strip.setPixelColor(i, OFF)
strip.show()
logger.info("Walk complete — all LEDs off")
