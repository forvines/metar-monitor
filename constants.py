#!/usr/bin/env python3
"""
Constants for METAR Monitor
Contains all constant values and configuration defaults used throughout the application
"""

# Default GPIO pin for mode toggle button
DEFAULT_BUTTON_PIN = 17

# Light sensor configuration
DEFAULT_LIGHT_SENSOR_UPDATE_INTERVAL = 30  # seconds
DEFAULT_MIN_BRIGHTNESS = 10  # minimum LED brightness percentage
DEFAULT_MAX_BRIGHTNESS = 100  # maximum LED brightness percentage

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
    "WINDS": 20,         # Strong wind threshold (knots)
    "GUSTS": 25,         # Gust threshold (knots)
    "CROSSWINDS": 15      # Crosswind threshold (knots)
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

# Configuration file path
CONFIG_FILE = "metar_config.json"

# Display formatting constants
DISPLAY_FORMATTING = {
    "SEPARATOR_LINE": "-" * 60,
    "HEADER_LINE": "=" * 60,
    "LED_INDICATOR": "■",
    "FORECAST_INDENT": "    ",
    "AIRPORT_INDENT": "  "
}

# Mode indicator colors
MODE_INDICATOR_COLOR = "WHITE"

# Display mode names
MODE_NAMES = {
    "METAR": "METAR Mode",
    "TAF": "TAF {hour}h Mode",
    "AIRPORTS_VISITED": "Airports Visited Mode",
    "TEST": "Test Mode"
}

# Display modes
class DisplayMode:
    """Display modes for the application"""
    METAR = 0     # Show current conditions (default)
    TAF = 1       # Show forecast data
    AIRPORTS_VISITED = 2  # Show visited airports
    TEST = 3      # Test mode - show METAR data availability
    
    @staticmethod
    def get_name(mode, forecast_hour=None):
        """Get the name of a display mode"""
        if mode == DisplayMode.METAR:
            return "METAR (Current Conditions)"
        elif mode == DisplayMode.TAF:
            if forecast_hour:
                return f"TAF {forecast_hour}-Hour Forecast"
            else:
                return "TAF Forecast"
        elif mode == DisplayMode.AIRPORTS_VISITED:
            return "Airports Visited"
        elif mode == DisplayMode.TEST:
            return "Test Mode (METAR Data Availability)"
        return "Unknown"
