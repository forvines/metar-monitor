#!/usr/bin/env python3
"""
Test script for BH1750 light sensor
Run this to verify the light sensor is working correctly
"""

import time
import sys
from light_sensor import LightSensor

def main():
    print("BH1750 Light Sensor Test")
    print("=" * 40)
    
    # Initialize sensor
    sensor = LightSensor()
    
    if not sensor.available:
        print("❌ Light sensor not available!")
        print("Check wiring and I2C configuration:")
        print("  - Run 'sudo raspi-config' and enable I2C")
        print("  - Run 'i2cdetect -y 1' to verify sensor connection")
        print("  - Expected address: 0x23 or 0x5C")
        sys.exit(1)
    
    print("✅ Light sensor initialized successfully!")
    print("\nReading light levels (Ctrl+C to exit):")
    print("Light Level (lux) | Brightness (%)")
    print("-" * 35)
    
    try:
        while True:
            # Read light level
            lux = sensor.read_light_level()
            
            if lux is not None:
                # Calculate brightness
                brightness = sensor.calculate_brightness(lux)
                
                # Display results
                print(f"{lux:8.1f} lux    |    {brightness:3d}%")
            else:
                print("Failed to read sensor")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nTest completed!")
        sensor.close()

if __name__ == "__main__":
    main()