# tools/walk_airports.py
import time, json
from rpi_ws281x import Adafruit_NeoPixel, Color

cfg = json.load(open("metar_config.json"))
LED_PIN = 18; LED_FREQ_HZ = 800000; LED_DMA = 10; LED_INVERT = False; LED_CHANNEL = 0
LED_COUNT = 103  # must match physical strip

strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, 255, LED_CHANNEL)
strip.begin()

def setpix(i, c): 
    if 0 <= i < LED_COUNT: strip.setPixelColor(i, c)

# Dim white so you can see it clearly
W = Color(64,64,64)  
OFF = Color(0,0,0)

airports = sorted(cfg["airports"], key=lambda a: a["led"])
for ap in airports:
    i = ap["led"]
    name = f'{ap.get("icao","?")} ({i})'
    # clear
    for j in range(LED_COUNT): setpix(j, OFF)
    # light only the airport’s configured LED
    setpix(i, W)
    strip.show()
    print("Lighting", name)
    time.sleep(0.35)

# finish with everything on for mapped airports
for j in range(LED_COUNT): setpix(j, OFF)
for ap in airports: setpix(ap["led"], W)
strip.show()

