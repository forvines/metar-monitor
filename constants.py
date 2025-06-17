#!/usr/bin/env python3
"""
Constants for METAR Monitor
Contains all constant values and configuration defaults used throughout the application
"""

# Default GPIO pin for mode toggle button
DEFAULT_BUTTON_PIN = 17

# Flight categories and their descriptions
FLIGHT_CATEGORIES = {
    "VFR": "Visual Flight Rules",
    "MVFR": "Marginal Visual Flight Rules",
    "IFR": "Instrument Flight Rules",
    "LIFR": "Low Instrument Flight Rules"
}

# Weather patterns for METAR parsing
REGEX_PATTERNS = {
    "WINDS": r'\b\d{3}(\d{2})(?:G\d+)?KT\b',  # Wind pattern (e.g. 27015KT)
    "GUSTS": r'\b\d{3}\d{2}G(\d+)KT\b',       # Gust pattern (e.g. 27015G25KT)
    "THUNDERSTORM": ["TSRA", " TS "]          # Thunderstorm indicators
}

# Thresholds for flight categories
THRESHOLDS = {
    "VISIBILITY": {
        "LIFR": 1.0,     # Below 1 mile
        "IFR": 3.0,      # 1-3 miles
        "MVFR": 5.0      # 3-5 miles
        # VFR is above 5 miles
    },
    "CEILING": {
        "LIFR": 500,     # Below 500 feet
        "IFR": 1000,     # 500-1000 feet
        "MVFR": 3000     # 1000-3000 feet
        # VFR is above 3000 feet
    },
    "WINDS": 30,         # Strong wind threshold (knots)
    "GUSTS": 20          # Gust threshold (knots)
}

# ANSI color codes for terminal output
COLORS = {
    "GREEN": "\033[92m",  # VFR
    "BLUE": "\033[34m",   # MVFR - Changed to a more distinct blue color
    "RED": "\033[91m",    # IFR
    "PURPLE": "\033[95m", # LIFR
    "YELLOW": "\033[93m", # Wind/Storm warnings
    "RESET": "\033[0m"    # Reset color
}

# Mapping between flight categories and LED colors
CATEGORY_COLOR_MAP = {
    "VFR": "GREEN",
    "MVFR": "BLUE",
    "IFR": "RED",
    "LIFR": "PURPLE"
}

# Default configuration for the application
DEFAULT_CONFIG = {
    "airports": ["KSEA", "KBFI", "KRNT", "KPAE", "KTIW", "KOLM"],
    "update_interval": 900,  # 15 minutes in seconds
    "metar_url": "https://aviationweather.gov/api/data/metar",
    "taf_url": "https://aviationweather.gov/api/data/taf",
    "forecast_hours": [4, 6, 12, 18, 24],  # Hours ahead to forecast using TAF
    "led_pin": 18,           # GPIO pin connected to the pixels (18 uses PWM)
    "led_count": 50,         # Number of LED pixels
    "led_brightness": 50,    # Set to 0 for darkest and 255 for brightest
    "led_freq_hz": 800000,   # LED signal frequency in Hz (usually 800khz)
    "led_dma": 10,           # DMA channel to use for generating signal
    "led_invert": False,     # True to invert the signal (when using NPN transistor level shift)
    "led_channel": 0,        # set to '1' for GPIOs 13, 19, 41, 45 or 53
    "mode_indicator_led": 49 # LED to use for indicating current display mode (last LED by default)
}

# Configuration file path
CONFIG_FILE = "metar_config.json"
