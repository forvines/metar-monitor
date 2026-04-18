#!/usr/bin/env python3
"""Walk through each airport LED interactively. Press any key to advance, 'b' to go back, 'q' to quit."""
import sys, tty, termios, json, logging
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

def show_airport(idx):
    ap = airports[idx]
    for i in range(cfg["led_count"]):
        strip.setPixelColor(i, OFF)
    strip.setPixelColor(ap["led"], WHITE)
    strip.show()
    logger.info("[%d/%d] LED %2d: %s - %s (visited: %s)",
                idx + 1, len(airports), ap["led"], ap["icao"], ap["name"], ap.get("visited", False))

def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

idx = 0
show_airport(idx)
print("Controls: any key = next, b = back, q = quit")

while True:
    key = getch()
    if key == 'q':
        break
    elif key == 'b':
        idx = max(0, idx - 1)
    else:
        idx += 1
        if idx >= len(airports):
            break
    show_airport(idx)

for i in range(cfg["led_count"]):
    strip.setPixelColor(i, OFF)
strip.show()
logger.info("Walk complete — all LEDs off")
