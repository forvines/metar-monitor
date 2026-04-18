import time
from rpi_ws281x import PixelStrip, Color

# === CONFIGURE THESE ===
LED_COUNT      = 103      # total number of LEDs in your strip
LED_PIN        = 18       # GPIO pin connected to the DATA line (must support PWM)
LED_FREQ_HZ    = 800000   # LED signal frequency in hertz (usually 800kHz)
LED_DMA        = 10       # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 64      # 0-255 (lower if you're testing weak power supply)
LED_INVERT     = False    # True to invert the signal (usually False)
LED_CHANNEL    = 0        # 0 for GPIO18, 1 for GPIO13, GPIO19, etc.

# =========================

# Initialize the library
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT,
                   LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

print(f"Testing {LED_COUNT} LEDs on GPIO{LED_PIN}...")

# --- Test 1: full white (power test) ---
print("Full white test: all LEDs should light white for 3 seconds")
for i in range(strip.numPixels()):
    strip.setPixelColor(i, Color(255, 255, 255))
strip.show()
time.sleep(3)

# --- Test 2: red chase (data integrity) ---
print("Red chase test: moving red dot should traverse entire strip")
for i in range(strip.numPixels()):
    if i > 0:
        strip.setPixelColor(i - 1, Color(0, 0, 0))
    strip.setPixelColor(i, Color(255, 0, 0))
    strip.show()
    time.sleep(0.03)

# --- Test 3: green, blue, and rainbow cycle (optional visuals) ---
colors = [(0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255)]
print("Color cycle test: cycling through basic colors")
for (r,g,b) in colors:
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(r,g,b))
    strip.show()
    time.sleep(1)

# --- Turn all off ---
for i in range(strip.numPixels()):
    strip.setPixelColor(i, 0)
strip.show()

print("LED test complete.")

