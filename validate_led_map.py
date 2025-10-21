# tools/validate_led_map.py
import json, sys
cfg = json.load(open("metar_config.json"))
LED_COUNT = 103  # <- set to your actual strip length

legend_leds = {x["led"] for x in cfg.get("legend", [])}
airport_leds = {}
dupes = []
for ap in cfg.get("airports", []):
    idx = ap["led"]
    if idx in airport_leds:
        dupes.append((idx, airport_leds[idx]["icao"], ap["icao"]))
    airport_leds[idx] = ap

all_leds = set(range(LED_COUNT))
unmapped = sorted(all_leds - legend_leds - set(airport_leds.keys()))

print(f"LED_COUNT: {LED_COUNT}")
print(f"Legend LEDs: {sorted(legend_leds)}")
print(f"Airports mapped: {len(airport_leds)}")
print("First 50 unmapped indices:", unmapped[:50])
if dupes:
    print("Duplicates (idx, first ICAO, second ICAO):")
    for d in dupes:
        print("  ", d)

# Bonus: show whether your problem indices are mapped
problem = [14,17,24,25,27,30,32,34,37,41]
print("\nProblem indices mapping:")
for i in problem:
    ap = airport_leds.get(i)
    print(f"  {i}: {'MAPPED to '+ap['icao'] if ap else 'UNMAPPED'}")

