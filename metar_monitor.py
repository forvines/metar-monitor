#!/usr/bin/env python3
"""
METAR Status Monitor for airports near KSEA
Displays color-coded status for flight conditions:
- Green: VFR (Visual Flight Rules)
- Blue: MVFR (Marginal Visual Flight Rules)
- Red: IFR (Instrument Flight Rules)
- Purple: LIFR (Low Instrument Flight Rules)
- Yellow: Strong winds (>30kts), gusts (>20kts), or thunderstorms

This version supports WS2811 LED output on a Raspberry Pi
"""

import urllib.request
import json
import time
import re
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
from metar_api_client import METARAPIClient, APIRequestFailed

# Display modes
class DisplayMode:
    """Display modes for the application"""
    METAR = 0     # Show current conditions (default)
    TAF = 1       # Show forecast data
    
    @staticmethod
    def get_name(mode, forecast_hour=None):
        """Get the name of a display mode
        
        Args:
            mode: The display mode
            forecast_hour: The current forecast hour (if in TAF mode)
        """
        if mode == DisplayMode.METAR:
            return "METAR (Current Conditions)"
        elif mode == DisplayMode.TAF:
            if forecast_hour:
                return f"TAF {forecast_hour}-Hour Forecast"
            else:
                return "TAF Forecast"
        return "Unknown"

# Constants for the application
class Constants:
    """Constants and configuration values for the application"""
    
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

# Use the constants for easier reference
COLORS = Constants.COLORS

# Try to import the rpi_ws281x library for LED control
LED_ENABLED = False
LED_COLORS = {}
try:
    from rpi_ws281x import PixelStrip, Color
    # LED RGB color values - only define if the library is available
    LED_COLORS = {
        "GREEN": Color(0, 255, 0),    # VFR
        "BLUE": Color(0, 0, 255),     # MVFR
        "RED": Color(255, 0, 0),      # IFR
        "PURPLE": Color(128, 0, 128), # LIFR
        "YELLOW": Color(255, 255, 0), # Wind/Storm warnings
        "WHITE": Color(255, 255, 255), # Mode indicator - METAR
        "CYAN": Color(0, 255, 255),   # Mode indicator - TAF 6h
        "ORANGE": Color(255, 165, 0), # Mode indicator - TAF 12h
        "PINK": Color(255, 105, 180), # Mode indicator - TAF 24h
        "OFF": Color(0, 0, 0)         # Off
    }
    LED_ENABLED = True
    print("LED support enabled")
except ImportError:
    print("rpi_ws281x library not found. Running in console-only mode.")

# Default configuration
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

CONFIG_FILE = "metar_config.json"

def load_config():
    """Load configuration from file or create default if not exists"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Ensure all required keys are present
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except Exception as e:
            print(f"Error loading config file: {e}")
            print("Using default configuration")
            return DEFAULT_CONFIG
    else:
        # Create default config file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(f"Created default configuration file: {CONFIG_FILE}")
        return DEFAULT_CONFIG

class LEDController:
    def __init__(self, config):
        self.strip = None
        self.config = config
        self.initialized = False
        
        if LED_ENABLED:
            try:
                # Create NeoPixel object with appropriate configuration
                self.strip = PixelStrip(
                    config["led_count"],
                    config["led_pin"],
                    config["led_freq_hz"],
                    config["led_dma"],
                    config["led_invert"],
                    config["led_brightness"],
                    config["led_channel"]
                )
                
                # Initialize the library (must be called once before other functions)
                self.strip.begin()
                self.initialized = True
                print("LED strip initialized successfully")
                
                # Turn off all LEDs initially
                self.clear()
            except Exception as e:
                print(f"Error initializing LED strip: {e}")
                self.initialized = False
    
    def set_led(self, index, color_name):
        """Set an LED to a specific color"""
        if not self.initialized or index >= self.config["led_count"]:
            print(f"LED index {index} out of range or LED strip not initialized.")
            return
            
        if color_name in LED_COLORS:
            color = LED_COLORS[color_name]
            self.strip.setPixelColor(index, color)
            self.strip.show()
        else:
            print(f"Unknown color name: {color_name}. Using default OFF color.")
            self.strip.setPixelColor(index, LED_COLORS["OFF"])
            self.strip.show()
    
    def clear(self):
        """Turn off all LEDs"""
        if not self.initialized:
            return
            
        for i in range(self.config["led_count"]):
            self.strip.setPixelColor(i, LED_COLORS["OFF"])
        self.strip.show()

class METARStatus:
    def print_color_legend(self):
        """Print a legend for the colors used in the display"""
        print("\n" + "=" * 60)
        print("Color Legend:")
        
        # Print flight categories
        for category, color in Constants.CATEGORY_COLOR_MAP.items():
            description = Constants.FLIGHT_CATEGORIES.get(category, "")
            print(f"{COLORS[color]}{color.title()}: {category} ({description}){COLORS['RESET']}")
        
        # Print weather warning
        wind_threshold = Constants.THRESHOLDS["WINDS"]
        gust_threshold = Constants.THRESHOLDS["GUSTS"]
        print(f"{COLORS['YELLOW']}Yellow: Strong winds (>{wind_threshold}kts), gusts (>{gust_threshold}kts), or thunderstorms{COLORS['RESET']}")
        
        print("=" * 60)
    
    def print_led_mapping(self):
        """Print the mapping between LEDs and airports"""
        print("\nLED to Airport Mapping:")
        for airport_info in self.config["airports"]:
            icao = airport_info["icao"]
            name = airport_info["name"]
            led = airport_info["led"]
            if led < self.config.get("led_count", 0):
                print(f"LED {led:2d}: {icao} - {name}")
        
    def __init__(self, config, led_controller=None):
        self.config = config
        self.last_update = None
        self.airport_data = {}
        self.led_controller = led_controller
        self.display_mode = DisplayMode.METAR  # Start in METAR mode
        self.current_forecast_hour = 6  # Default forecast hour for TAF mode
        self.forecast_hour_index = 0  # Index into forecast_hours list
        
        # Set up logging first
        self.logger = logging.getLogger("metar_status")
        
        # Create a mapping of airports to LED indices
        self.airport_to_led = {}
        for airport_info in config["airports"]:
            icao = airport_info["icao"]
            led_index = airport_info["led"]
            if led_index < config.get("led_count", 0):
                self.airport_to_led[icao] = led_index
        
        # Create a mapping of legend LEDs
        self.legend_leds = {}
        if "legend" in config:
            for legend_item in config["legend"]:
                name = legend_item["name"]
                color = legend_item["color"]
                led = legend_item["led"]
                self.legend_leds[led] = {"name": name, "color": color}
            self.logger.debug(f"Initialized {len(self.legend_leds)} legend LEDs")
        
        # Initialize API client
        self.api_client = METARAPIClient(
            base_metar_url=config["metar_url"],
            base_taf_url=config["taf_url"]
        )
        self.logger.info("Initialized METAR Status with API client")
        
        # Set up legend LEDs if we have an LED controller
        if self.led_controller and self.legend_leds:
            self.set_legend_leds()
            
    def set_legend_leds(self):
        """Set the legend LEDs to their corresponding colors
        
        This sets up the legend LEDs according to the configuration, displaying
        the different flight categories and conditions directly on the LED strip.
        """
        if not self.led_controller:
            return
        
        self.logger.info("Setting up legend LEDs")
        for led_index, legend_item in self.legend_leds.items():
            color = legend_item["color"]
            name = legend_item["name"]
            
            # Set the LED to its designated color
            self.led_controller.set_led(led_index, color)
            self.logger.debug(f"Set legend LED {led_index} to {color} ({name})")
            
        self.logger.info(f"Legend display initialized with {len(self.legend_leds)} LEDs")
        
    def toggle_display_mode(self):
        """Cycle through display modes: METAR -> TAF (6h) -> TAF (12h) -> TAF (24h) -> METAR"""
        forecast_hours = self.config["forecast_hours"]
        if not isinstance(forecast_hours, list) or not forecast_hours:
            forecast_hours = [6]  # Default if not defined or empty
        
        if self.display_mode == DisplayMode.METAR:
            # Switch to TAF mode with the first forecast hour
            self.display_mode = DisplayMode.TAF
            self.forecast_hour_index = 0
            self.current_forecast_hour = forecast_hours[self.forecast_hour_index]
            self.logger.info(f"Display mode changed to TAF {self.current_forecast_hour}-Hour Forecast")
        else:
            # Already in TAF mode, cycle through forecast hours
            self.forecast_hour_index = (self.forecast_hour_index + 1) % len(forecast_hours)
            
            # If we wrapped around to the first hour, switch back to METAR
            if self.forecast_hour_index == 0:
                self.display_mode = DisplayMode.METAR
                self.logger.info("Display mode changed to METAR (Current Conditions)")
            else:
                self.current_forecast_hour = forecast_hours[self.forecast_hour_index]
                self.logger.info(f"Display mode changed to TAF {self.current_forecast_hour}-Hour Forecast")
            
        # Update the LED display based on the new mode
        self.update_led_display()
        
        # Print status message
        print("\n" + "=" * 60)
        if self.display_mode == DisplayMode.METAR:
            print(f"Display mode changed to: {DisplayMode.get_name(self.display_mode)}")
        else:
            print(f"Display mode changed to: {DisplayMode.get_name(self.display_mode, self.current_forecast_hour)}")
        print("=" * 60)
        
        return self.display_mode
        
    def update_led_display(self):
        """Update LEDs based on current display mode"""
        if not self.led_controller:
            return
        
        # Update airport LEDs if we have data
        if self.airport_data:
            for airport, data in self.airport_data.items():
                if airport not in self.airport_to_led:
                    continue
                    
                led_index = self.airport_to_led[airport]
                
                if self.display_mode == DisplayMode.METAR:
                    # Show current conditions
                    status_color = data.get("status_color", "OFF")
                else:
                    # Use the current forecast hour
                    forecast_hour = self.current_forecast_hour
                    
                    # Show forecast for the selected hour
                    if "forecasts" in data and data["forecasts"]:
                        if forecast_hour in data["forecasts"]:
                            # Use the forecast for the selected hour
                            status_color = data["forecasts"][forecast_hour]["color"]
                        else:
                            # Find the closest available forecast hour
                            available_hours = sorted(data["forecasts"].keys())
                            closest_hour = min(available_hours, key=lambda x: abs(x - forecast_hour))
                            status_color = data["forecasts"][closest_hour]["color"]
                            self.logger.debug(f"Using {closest_hour}h forecast for {airport} instead of requested {forecast_hour}h")
                    else:
                        # No forecast data, use OFF
                        status_color = "OFF"
                
                self.led_controller.set_led(led_index, status_color)
        
        # Update the legend LEDs to ensure they stay at their proper colors
        if self.legend_leds:
            self.set_legend_leds()
            
        # Update the mode indicator LED
        mode_led_index = self.config.get("mode_indicator_led")
        if mode_led_index is not None and mode_led_index < self.config.get("led_count", 0):
            # Map display mode to indicator color
            if self.display_mode == DisplayMode.METAR:
                indicator_color = "WHITE"  # METAR mode
            elif self.display_mode == DisplayMode.TAF:
                # Choose color based on forecast hour
                if self.current_forecast_hour <= 8:
                    indicator_color = "CYAN"    # TAF 8h or less
                elif self.current_forecast_hour <= 12:
                    indicator_color = "ORANGE"  # TAF 12h or less
                else:
                    indicator_color = "PINK"    # TAF >12h
            else:
                indicator_color = "OFF"    # Unknown mode
            
            # Set the indicator LED
            self.led_controller.set_led(mode_led_index, indicator_color)
            self.logger.debug(f"Set mode indicator LED {mode_led_index} to {indicator_color}")
    
    def _fetch_raw_metar_data(self, airports):
        """Fetch raw METAR data from the API for the specified airports
        
        Makes an HTTP request to the Aviation Weather API to retrieve METAR data 
        for multiple airports in a single batch request. Processes the response
        to ensure only the most recent observation for each airport is kept.
        
        Args:
            airports (list): List of airport ICAO identifiers
            
        Returns:
            dict: Dictionary mapping airport IDs to their most recent METAR data
                  Empty dictionary if the request fails
        """
        try:
            self.logger.info("Fetching METAR data for %d airports", len(airports))
            # Use the API client to fetch METAR data with retry and timeout
            all_metar_data = self.api_client.fetch_metar_data(airports)
            
            # Process the METAR data to get the most recent observations
            airport_metars = self.api_client.get_most_recent_metars(all_metar_data)
            
            self.logger.info("Successfully retrieved METAR data for %d airports", len(airport_metars))
            return airport_metars
            
        except APIRequestFailed as e:
            self.logger.error("API request failed: %s", str(e))
            return {}
        except Exception as e:
            self.logger.exception("Unexpected error fetching METAR data: %s", str(e))
            return {}
            
    def _process_airport_data(self, station_id, metar_data, taf_data, airport_name):
        """Process METAR and TAF data for a single airport
        
        Takes raw METAR data for an airport and processes it to determine
        flight category and status color. Stores the processed data in the
        airport_data dictionary and processes TAF data if available.
        
        Args:
            station_id (str): The ICAO identifier of the airport
            metar_data (dict): The raw METAR data from the API
            taf_data (list): List of TAF data objects for the airport, or None
            airport_name (str): The friendly name of the airport
            
        Returns:
            tuple: (status_color, flight_category) - The color and flight category 
                  for this airport's current conditions
        """
        raw_text = metar_data.get("rawOb")
        
        # Determine flight category based on ceiling and visibility
        flight_category = self.determine_flight_category(metar_data)
        
        # Determine status color
        status_color = self.determine_status_color(raw_text, flight_category)
        
        # Initialize airport data
        self.airport_data[station_id] = {
            "raw_metar": raw_text,
            "flight_category": flight_category,
            "status_color": status_color,
            "forecast": None,
            "forecast_category": None,
            "forecast_color": None,
            "name": airport_name
        }
        
        # Process TAF data if available
        if taf_data:
            self.process_taf_data(station_id, taf_data)
            
        return status_color, flight_category
            
    def _display_airport_data(self, station_id, status_color, flight_category):
        """Display formatted data for a single airport
        
        Prints formatted information about an airport's weather conditions to the console
        with appropriate color coding. Also controls the associated LED if available.
        
        Args:
            station_id (str): The ICAO identifier of the airport
            status_color (str): The color name representing the airport's status
            flight_category (str): The flight category of the airport ('VFR', 'MVFR', etc.)
        """
        airport_data = self.airport_data[station_id]
        raw_text = airport_data["raw_metar"]
        
        # Format the display
        color_code = COLORS.get(status_color, COLORS["RESET"])
        status_text = flight_category if flight_category else "Unknown"
        warning_text = self.get_warning_text(status_color, raw_text)
        
        print(f"{station_id} - {airport_data['name']}: {color_code}{status_text}{warning_text}{COLORS['RESET']}")
        print(f"  METAR: {raw_text}")
        
        # Display forecast information if available
        if "forecasts" in airport_data:
            forecasts = airport_data["forecasts"]
            if forecasts:
                print(f"  Forecasts:")
                for hours, forecast in sorted(forecasts.items()):
                    forecast_color = COLORS.get(forecast["color"], COLORS["RESET"])
                    forecast_text = forecast["category"]
                    print(f"    {hours}h: {forecast_color}{forecast_text}{COLORS['RESET']} - {forecast['taf_summary']}")
        
        # Set the LED for this airport if we have an LED controller
        if self.led_controller and station_id in self.airport_to_led:
            led_index = self.airport_to_led[station_id]
            print(f"  Setting LED {led_index} to {status_color}")
            self.led_controller.set_led(led_index, status_color)
            
        print("-" * 60)
    
    def print_led_summary(self):
        """Print a summary of all LEDs with their colors and airport names"""
        print("\n" + "=" * 60)
        print("LED Summary:")
        print("-" * 60)
        
        # Get all airports sorted by LED index
        sorted_airports = sorted(
            [(info["led"], icao, info["name"]) 
             for icao, info in zip(
                 [airport["icao"] for airport in self.config["airports"]],
                 [airport for airport in self.config["airports"]]
             ) 
             if info["led"] < self.config.get("led_count", 0)],
            key=lambda x: x[0]
        )
        
        # Print each LED with its color and airport
        for led_index, icao, name in sorted_airports:
            if icao in self.airport_data:
                if self.display_mode == DisplayMode.METAR:
                    # Show current conditions
                    status_color = self.airport_data[icao].get("status_color", "OFF")
                else:
                    # Use the current forecast hour
                    forecast_hour = self.current_forecast_hour
                    status_color = "OFF"
                    
                    # Show forecast for the selected hour
                    if "forecasts" in self.airport_data[icao] and self.airport_data[icao]["forecasts"]:
                        if forecast_hour in self.airport_data[icao]["forecasts"]:
                            status_color = self.airport_data[icao]["forecasts"][forecast_hour]["color"]
                        elif self.airport_data[icao]["forecasts"]:
                            # Find the closest available forecast hour
                            available_hours = sorted(self.airport_data[icao]["forecasts"].keys())
                            closest_hour = min(available_hours, key=lambda x: abs(x - forecast_hour))
                            status_color = self.airport_data[icao]["forecasts"][closest_hour]["color"]
                
                # Get the color code for display
                color_code = COLORS.get(status_color, COLORS["RESET"])
                flight_category = self.airport_data[icao].get("flight_category", "Unknown")
                
                # Get warning text if applicable
                warning_text = ""
                if status_color == "YELLOW":
                    warning_text = self.get_warning_text(
                        status_color, self.airport_data[icao].get("raw_metar", "")
                    )
                
                # Print the LED summary line
                print(f"LED {led_index:2d}: {color_code}■{COLORS['RESET']} {icao} - {color_code}{flight_category}{warning_text}{COLORS['RESET']} - {name}")
        
        # Print the mode indicator LED if it exists
        mode_led_index = self.config.get("mode_indicator_led")
        if mode_led_index is not None and mode_led_index < self.config.get("led_count", 0):
            # Determine indicator color based on current mode
            if self.display_mode == DisplayMode.METAR:
                indicator_color = "WHITE"
                mode_name = "METAR Mode"
            else:
                if self.current_forecast_hour <= 8:
                    indicator_color = "CYAN"
                elif self.current_forecast_hour <= 12:
                    indicator_color = "ORANGE"
                else:
                    indicator_color = "PINK"
                mode_name = f"TAF {self.current_forecast_hour}h Mode"
                
            color_code = COLORS.get(indicator_color, COLORS["RESET"])
            print(f"LED {mode_led_index:2d}: {color_code}■{COLORS['RESET']} Mode Indicator - {color_code}{mode_name}{COLORS['RESET']}")
        
        print("=" * 60)
    
    def fetch_metar_data(self):
        """Fetch and process METAR data for all configured airports"""
        # Get list of airport IDs
        airports = [airport["icao"] for airport in self.config["airports"]]
        
        # Print legends and headers
        self.print_color_legend()
        self.print_led_mapping()
        print("\nFetching METAR data for airports...")
        print("=" * 60)
        
        # Reset data
        self.airport_data = {}
        self.last_update = datetime.now()
        
        # Create a mapping of ICAO codes to airport names for easy lookup
        airport_names = {airport["icao"]: airport["name"] for airport in self.config["airports"]}
        
        # Step 1: Fetch METAR data
        airport_metars = self._fetch_raw_metar_data(airports)
        if not airport_metars:
            print("No METAR data was retrieved.")
            return False
            
        # Step 2: Fetch TAF data for all airports at once
        all_taf_data = self.fetch_all_taf_data(airports)
        
        # Step 3: Process each airport's data
        for station_id, metar_data in airport_metars.items():
            if station_id in airport_names:
                # Process data for this airport
                taf_data = all_taf_data.get(station_id, None)
                status_color, flight_category = self._process_airport_data(
                    station_id, metar_data, taf_data, airport_names[station_id]
                )
                
                # Display the results
                self._display_airport_data(station_id, status_color, flight_category)
        
        # Print a summary of all LEDs with their colors
        self.print_led_summary()
        
        return len(self.airport_data) > 0
    
    def fetch_all_taf_data(self, airports):
        """Fetch TAF data for all airports at once using batch API
        
        Uses the API client to fetch TAF data with retry logic, timeout handling,
        and proper error logging.
        
        Args:
            airports (list): List of airport ICAO identifiers
            
        Returns:
            dict: Dictionary mapping airport IDs to lists of their TAF data
                 Empty dictionary if the request fails
        """
        try:
            self.logger.info("Fetching TAF data for %d airports", len(airports))
            
            # Use the API client to fetch TAF data with retry and timeout
            taf_data_list = self.api_client.fetch_taf_data(airports)
            
            # Process the TAF data to group by airport
            all_taf_data = self.api_client.group_tafs_by_airport(taf_data_list)
            
            self.logger.info("Successfully retrieved TAF data for %d airports", len(all_taf_data))
            return all_taf_data
            
        except APIRequestFailed as e:
            self.logger.error("TAF API request failed: %s", str(e))
            return {}
        except Exception as e:
            self.logger.exception("Unexpected error fetching TAF data: %s", str(e))
            return {}
    
    def _get_most_recent_taf(self, taf_data_list):
        """Extract the most recent TAF from a list of TAFs
        
        Searches a list of TAF data objects for the most recent one, prioritizing
        those marked with the mostRecent=1 flag. Falls back to the first TAF in the
        list if none have this flag set.
        
        Args:
            taf_data_list (list): List of TAF data objects from the API
            
        Returns:
            dict: The most recent TAF data object, or None if the list is empty
        """
        if not taf_data_list:
            return None
            
        # First look for the TAF with mostRecent=1 flag
        for taf in taf_data_list:
            if taf.get("mostRecent") == 1:
                return taf
                
        # If no mostRecent flag found, fall back to first TAF
        return taf_data_list[0]
        
    def _find_relevant_forecast_period(self, forecast_periods, target_time):
        """Find the forecast period that covers the target time
        
        Searches through a list of forecast periods to find the one that includes
        the specified target time. Converts epoch timestamps to datetime objects
        for comparison.
        
        Args:
            forecast_periods (list): List of forecast period objects from the TAF data
            target_time (datetime): The target time to find a forecast for
            
        Returns:
            tuple: (period, from_time) - The matching forecast period and its start time,
                  or (None, None) if no matching period is found
        """
        if not forecast_periods:
            return None, None
            
        for period in forecast_periods:
            time_from = period.get("timeFrom")
            time_to = period.get("timeTo")
            
            if not time_from or not time_to:
                continue
                
            # Convert epoch times to datetime objects - with type checking
            try:
                # Ensure timestamps are integers
                time_from_int = int(time_from)
                time_to_int = int(time_to)
                
                # Convert to datetime objects
                from_time = datetime.fromtimestamp(time_from_int)
                to_time = datetime.fromtimestamp(time_to_int)
                
                # Check if target time is within this period
                if from_time <= target_time <= to_time:
                    # Return both the period and the from_time for display
                    return period, from_time
                
            except (TypeError, ValueError) as e:
                # Log the error but continue processing other periods
                self.logger.warning("Invalid timestamp in forecast period: %s", str(e))
                continue
                
        return None, None
            
    def _format_clouds_info(self, clouds):
        """Format cloud information into a readable string
        
        Converts a list of cloud data objects into a formatted string representation
        of cloud layers (e.g., "BKN025 OVC080").
        
        Args:
            clouds (list): List of cloud data objects, each containing 'cover' and 'base'
            
        Returns:
            str: Formatted string of cloud information (e.g., "BKN025 OVC080")
                 Empty string if no valid cloud information is available
        """
        if not clouds:
            return ""
            
        clouds_info = []
        for cloud in clouds:
            cover = cloud.get("cover", "")
            base = cloud.get("base", "")
            if cover and base:
                clouds_info.append(f"{cover}{base}")
            
        return " ".join(clouds_info)
    
    def _process_forecast_period(self, period, from_time, airport):
        """Process a single forecast period and return its information
        
        Takes a single forecast period from a TAF and extracts the relevant data,
        formats it for display, and determines the flight category and status color.
        
        Args:
            period (dict): A forecast period object from the TAF data
            from_time (datetime): The start time of this forecast period
            airport (str): The ICAO identifier of the airport
            
        Returns:
            dict: A dictionary containing formatted forecast information including
                  category, color, summary text, and time range, or None if processing fails
        """
        if not period or not from_time:
            return None
            
        # Extract forecast data
        fcst_change = period.get("fcstChange", "")
        wdir = period.get("wdir", "")
        wspd = period.get("wspd", "")
        visib = period.get("visib", "")
        
        # Format from time and clouds
        from_time_str = from_time.strftime("%d%H%M")
        clouds_str = self._format_clouds_info(period.get("clouds", []))
        
        # Format wind and create summary
        wind_text = self._format_wind(wdir, wspd)
        taf_summary = f"{fcst_change} {from_time_str} {wind_text}KT {visib} {clouds_str}"
        
        # Determine flight category and color
        forecast_category = self.determine_forecast_category(period)
        
        # Create text for weather warnings check
        forecast_text = self._format_wind(wdir, wspd) + f"KT {visib} {clouds_str}"
        forecast_color = self.determine_status_color(forecast_text, forecast_category)
        
        return {
            "category": forecast_category,
            "color": forecast_color,
            "taf_summary": taf_summary,
            "time_from": from_time,
            "time_to": datetime.fromtimestamp(period.get("timeTo"))
        }
            
    def process_taf_data(self, airport, taf_data_list):
        """Process TAF data for a specific airport
        
        Takes a list of TAF data for an airport and processes it to determine
        forecast information for the configured forecast hours. Stores the processed
        data in the airport_data dictionary.
        
        Args:
            airport (str): The ICAO identifier of the airport
            taf_data_list (list): List of TAF data objects for the airport
        """
        try:
            self.logger.debug("Processing TAF data for %s", airport)
            
            # Get the most recent TAF
            most_recent_taf = self._get_most_recent_taf(taf_data_list)
            if not most_recent_taf:
                self.logger.warning("No valid TAF found for %s", airport)
                return
            
            # Store the raw TAF
            raw_taf = most_recent_taf.get("rawTAF")
            self.airport_data[airport]["forecast"] = raw_taf
            self.airport_data[airport]["forecasts"] = {}
            
            # Get forecast hours, ensure it's a list
            forecast_hours = self.config["forecast_hours"]
            if not isinstance(forecast_hours, list):
                forecast_hours = [forecast_hours]
            
            # Get all forecast periods from the TAF
            forecast_periods = most_recent_taf.get("fcsts", [])
            if not forecast_periods:
                self.logger.warning("No forecast periods in TAF for %s", airport)
                return
                
            # Process each forecast hour
            processed_hours = 0
            for hours in forecast_hours:
                # Calculate the target forecast time
                target_time = datetime.now() + timedelta(hours=hours)
                
                # Find the relevant forecast period
                relevant_period, from_time = self._find_relevant_forecast_period(
                    forecast_periods, target_time
                )
                
                if not relevant_period:
                    self.logger.debug("No forecast period found for %s at +%d hours", airport, hours)
                    continue
                
                # Process the forecast period
                forecast_data = self._process_forecast_period(relevant_period, from_time, airport)
                if not forecast_data:
                    self.logger.debug("Failed to process forecast period for %s at +%d hours", airport, hours)
                    continue
                    
                # Store the forecast information
                self.airport_data[airport]["forecasts"][hours] = forecast_data
                processed_hours += 1
                
                # For backward compatibility, store the 6-hour forecast (or first forecast if no 6-hour)
                if hours == 6 or "forecast_category" not in self.airport_data[airport]:
                    self.airport_data[airport]["forecast_category"] = forecast_data["category"]
                    self.airport_data[airport]["forecast_color"] = forecast_data["color"]
                    self.airport_data[airport]["forecast_taf_summary"] = forecast_data["taf_summary"]
            
            self.logger.debug("Successfully processed %d forecast periods for %s", processed_hours, airport)
            
        except Exception as e:
            self.logger.exception("Error processing TAF data for %s: %s", airport, str(e))
    
    def fetch_taf_data(self, airport):
        """Legacy method for backward compatibility"""
        pass  # This method is kept for backward compatibility but is no longer used
            
    def _determine_flight_category_from_values(self, visibility, ceiling):
        """Helper method to determine flight category based on visibility and ceiling values"""
        if visibility is None and ceiling is None:
            return "Unknown"
        
        # Check for LIFR conditions first (lowest ceiling/visibility)
        lifr_vis = Constants.THRESHOLDS["VISIBILITY"]["LIFR"]
        lifr_ceiling = Constants.THRESHOLDS["CEILING"]["LIFR"]
        if (visibility is not None and visibility < lifr_vis) or (ceiling is not None and ceiling < lifr_ceiling):
            return "LIFR"  # Low IFR
        
        # Check for IFR conditions
        ifr_vis = Constants.THRESHOLDS["VISIBILITY"]["IFR"]
        ifr_ceiling = Constants.THRESHOLDS["CEILING"]["IFR"]
        if (visibility is not None and visibility < ifr_vis) or (ceiling is not None and ceiling < ifr_ceiling):
            return "IFR"   # IFR
        
        # Check for MVFR conditions
        mvfr_vis = Constants.THRESHOLDS["VISIBILITY"]["MVFR"]
        mvfr_ceiling = Constants.THRESHOLDS["CEILING"]["MVFR"]
        if (visibility is not None and visibility < mvfr_vis) or (ceiling is not None and ceiling < mvfr_ceiling):
            return "MVFR"  # Marginal VFR
        
        # If none of the above, it's VFR
        return "VFR"   # VFR
    
    def determine_forecast_category(self, forecast_period):
        """Determine flight category based on forecast data"""
        # Extract visibility (in statute miles)
        visibility = forecast_period.get("visib")
        if visibility == "6+" or visibility == "P6SM":
            visibility = 6.0
        else:
            try:
                visibility = float(visibility)
            except (ValueError, TypeError):
                visibility = None
        
        # Find lowest ceiling (height of lowest broken or overcast layer)
        ceiling = None
        clouds = forecast_period.get("clouds", [])
        for cloud in clouds:
            cover = cloud.get("cover")
            if cover in ["BKN", "OVC"]:  # Broken or Overcast
                base = cloud.get("base")
                if base is not None:
                    try:
                        base = int(base)
                        if ceiling is None or base < ceiling:
                            ceiling = base
                    except (ValueError, TypeError):
                        pass
        
        # Use helper method to determine flight category
        return self._determine_flight_category_from_values(visibility, ceiling)
            
    def determine_flight_category(self, metar):
        """Determine flight category based on ceiling and visibility"""
        # Extract visibility (in statute miles)
        visibility = metar.get("visib")
        if visibility == "10+":
            visibility = 10.0
        else:
            try:
                visibility = float(visibility)
            except (ValueError, TypeError):
                visibility = None
        
        # Find lowest ceiling (height of lowest broken or overcast layer)
        ceiling = None
        clouds = metar.get("clouds", [])
        for cloud in clouds:
            cover = cloud.get("cover")
            if cover in ["BKN", "OVC"]:  # Broken or Overcast
                base = cloud.get("base")
                if base is not None:
                    if ceiling is None or base < ceiling:
                        ceiling = base
        
        # Use helper method to determine flight category
        return self._determine_flight_category_from_values(visibility, ceiling)
    
    def get_warning_text(self, status_color, raw_text):
        """Generate a warning text description for weather conditions"""
        warning_text = ""
        if status_color == "YELLOW":
            # Check for gusts
            if "G" in raw_text and re.search(Constants.REGEX_PATTERNS["GUSTS"], raw_text):
                gust_match = re.search(Constants.REGEX_PATTERNS["GUSTS"], raw_text)
                warning_text = f" - Gusts {gust_match.group(1)}KT"
            # Check for strong winds
            elif re.search(Constants.REGEX_PATTERNS["WINDS"], raw_text):
                wind_match = re.search(Constants.REGEX_PATTERNS["WINDS"], raw_text)
                warning_text = f" - Winds {wind_match.group(1)}KT"
            # Check for thunderstorms
            elif any(pattern in raw_text for pattern in Constants.REGEX_PATTERNS["THUNDERSTORM"]):
                warning_text = " - Thunderstorm"
        return warning_text
    
    def _format_wind(self, wdir, wspd):
        """Helper method to format wind direction and speed safely"""
        try:
            # Try to format as integers with padding
            wdir_fmt = f"{int(wdir):03d}" if wdir is not None else "---"
            wspd_fmt = f"{int(wspd):02d}" if wspd is not None else "--"
            return f"{wdir_fmt}{wspd_fmt}"
        except (ValueError, TypeError):
            # If conversion fails, just concatenate the raw values
            return f"{wdir or '---'}{wspd or '--'}"
    
    def determine_status_color(self, raw_metar, flight_category):
        """Determine the status color based on METAR data"""
        # Check for strong winds, gusts, or thunderstorms first
        if raw_metar:
            # Check for winds over threshold knots
            wind_match = re.search(Constants.REGEX_PATTERNS["WINDS"], raw_metar)
            if wind_match and int(wind_match.group(1)) > Constants.THRESHOLDS["WINDS"]:
                return "YELLOW"
            
            # Check for gusts over threshold knots
            gust_match = re.search(Constants.REGEX_PATTERNS["GUSTS"], raw_metar)
            if gust_match and int(gust_match.group(1)) > Constants.THRESHOLDS["GUSTS"]:
                return "YELLOW"
            
            # Check for thunderstorms
            if any(pattern in raw_metar for pattern in Constants.REGEX_PATTERNS["THUNDERSTORM"]):
                return "YELLOW"
        
        # Then check flight category and map to appropriate color
        if flight_category in Constants.CATEGORY_COLOR_MAP:
            return Constants.CATEGORY_COLOR_MAP[flight_category]
        
        # Default if we can't determine
        return "OFF"

def main():
    # Configure logging with log rotation
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Set up file handler with rotation - 7 days of logs, rotating at midnight
    file_handler = TimedRotatingFileHandler(
        filename="metar_monitor.log",
        when="midnight",
        interval=1,
        backupCount=7,  # Keep 7 days of logs
        encoding="utf-8",
        delay=False
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.suffix = "%Y-%m-%d"  # Use YYYY-MM-DD date format in rotated log filenames
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Get application logger
    logger = logging.getLogger("metar_monitor")
    logger.info("Starting METAR Monitor with log rotation (7 days retention)")
    
    # Try to import ButtonHandler
    try:
        from button_handler import ButtonHandler
        button_available = True
        logger.info("Button handler module available")
    except ImportError:
        button_available = False
        logger.warning("Button handler module not available. Button functionality disabled.")
    
    # Load configuration
    config = load_config()
    
    logger.info("Starting METAR Monitor")
    logger.info("Monitoring %d airports: %s", 
               len(config['airports']), 
               ", ".join([airport["icao"] for airport in config['airports']]))
    logger.info("Update interval: %d seconds", config['update_interval'])
    logger.info("Forecast hours: %s", str(config['forecast_hours']))
    
    # Initialize LED controller if possible
    led_controller = None
    if LED_ENABLED:
        logger.info("LED support is enabled, initializing controller")
        led_controller = LEDController(config)
    else:
        logger.info("LED support is disabled, running in console-only mode")
    
    # Initialize METAR status with LED controller
    metar_status = METARStatus(config, led_controller)
    
    # Set up button handler if available
    button_handler = None
    if button_available:
        # Configure the button handler with the toggle display mode callback
        button_pin = config.get("button_pin", Constants.DEFAULT_BUTTON_PIN)
        logger.info("Setting up button handler on GPIO pin %d", button_pin)
        
        def toggle_mode_callback():
            mode = metar_status.toggle_display_mode()
            logger.info("Button pressed: Display mode toggled to %s", 
                       DisplayMode.get_name(mode))
        
        button_handler = ButtonHandler(button_pin, toggle_mode_callback)
        button_success = button_handler.start()
        
        if button_success:
            logger.info("Button handler started successfully")
            print(f"Button on GPIO {button_pin} enabled. Press button to toggle between METAR and TAF display.")
        else:
            logger.warning("Failed to start button handler")
    
    try:
        # Initial data fetch
        if metar_status.fetch_metar_data():
            print("\nCompleted fetching all airport data.")
            
            # Update LED display based on initial mode
            metar_status.update_led_display()
        
        while True:
            # Wait for the configured update interval
            print(f"\nNext update in {config['update_interval'] // 60} minutes. Press Ctrl+C to exit.")
            print(f"Current display mode: {DisplayMode.get_name(metar_status.display_mode)}")
            
            if button_handler:
                print("Press button to toggle between METAR and TAF display modes.")
                
            time.sleep(config['update_interval'])
            
            # Fetch updated data
            if metar_status.fetch_metar_data():
                print("\nCompleted updating airport data.")
                
                # Update LED display based on current mode
                metar_status.update_led_display()
    
    except KeyboardInterrupt:
        print("\nExiting METAR Status Monitor.")
        # Clean up resources
        if button_handler:
            button_handler.stop()
            logger.info("Button handler stopped")
            
        if led_controller:
            led_controller.clear()
            logger.info("LED controller cleared")

if __name__ == "__main__":
    main()
