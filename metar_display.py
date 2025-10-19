#!/usr/bin/env python3
"""
Display Manager

Handles all display output including LED summary, airport data display, and legends.
"""

import logging
from constants import COLORS, FLIGHT_CATEGORIES, THRESHOLDS, DISPLAY_FORMATTING, MODE_INDICATOR_COLOR, MODE_NAMES
from weather_status import get_warning_text
from led_status_calculator import LEDStatusCalculator


class DisplayManager:
    """Manages all display output for the METAR monitor"""
    
    def __init__(self, config, led_controller=None):
        self.config = config
        self.led_controller = led_controller
        self.logger = logging.getLogger("display_manager")
        
        # Create airport to LED mapping
        self.airport_to_led = {}
        for airport_info in config["airports"]:
            icao = airport_info["icao"]
            led_index = airport_info["led"]
            if led_index < config.get("led_count", 0):
                self.airport_to_led[icao] = led_index
    
    def print_color_legend(self):
        """Print a legend for the colors used in the display"""
        self.logger.info("Displaying color legend")
        print("\n" + DISPLAY_FORMATTING["HEADER_LINE"])
        print("Color Legend:")
        
        # Print flight categories
        from constants import CATEGORY_COLOR_MAP
        for category, color in CATEGORY_COLOR_MAP.items():
            description = FLIGHT_CATEGORIES.get(category, "")
            print(f"{COLORS[color]}{color.title()}: {category} ({description}){COLORS['RESET']}")
        
        # Print weather warning
        wind_threshold = THRESHOLDS["WINDS"]
        gust_threshold = THRESHOLDS["GUSTS"]
        crosswind_threshold = THRESHOLDS["CROSSWINDS"]
        print(f"{COLORS['YELLOW']}Yellow: Strong winds (>{wind_threshold}kts), gusts (>{gust_threshold}kts), thunderstorms, or crosswind (>{crosswind_threshold}kts){COLORS['RESET']}")
        
        print(DISPLAY_FORMATTING["HEADER_LINE"])
    
    def print_led_mapping(self):
        """Print the mapping between LEDs and airports"""
        self.logger.info("Displaying LED to airport mapping")
        print("\nLED to Airport Mapping:")
        for airport_info in self.config["airports"]:
            icao = airport_info["icao"]
            name = airport_info["name"]
            led = airport_info["led"]
            if led < self.config.get("led_count", 0):
                print(f"LED {led:2d}: {icao} - {name}")
    
    def display_airport_data(self, station_id, airport_data):
        """Display formatted data for a single airport"""
        raw_text = airport_data["raw_metar"]
        status_color = airport_data["status_color"]
        flight_category = airport_data["flight_category"]
        
        # Format the display
        color_code = COLORS.get(status_color, COLORS["RESET"])
        status_text = flight_category if flight_category else "Unknown"
        warning_text = get_warning_text(status_color, raw_text, station_id, 
                                      airport_data.get("wind_data"), self.config)
        
        print(f"{station_id} - {airport_data['name']}: {color_code}{status_text}{warning_text}{COLORS['RESET']}")
        print(f"{DISPLAY_FORMATTING['AIRPORT_INDENT']}METAR: {raw_text}")
        
        # Display forecast information if available
        if "forecasts" in airport_data:
            forecasts = airport_data["forecasts"]
            if forecasts:
                print(f"{DISPLAY_FORMATTING['AIRPORT_INDENT']}Forecasts:")
                for hours, forecast in sorted(forecasts.items()):
                    forecast_color = COLORS.get(forecast["color"], COLORS["RESET"])
                    forecast_text = forecast["category"]
                    print(f"{DISPLAY_FORMATTING['FORECAST_INDENT']}{hours}h: {forecast_color}{forecast_text}{COLORS['RESET']} - {forecast['taf_summary']}")
        
        # Set the LED for this airport if we have an LED controller
        if self.led_controller and station_id in self.airport_to_led:
            led_index = self.airport_to_led[station_id]
            print(f"{DISPLAY_FORMATTING['AIRPORT_INDENT']}Setting LED {led_index} to {status_color}")
            self.logger.debug(f"Setting LED {led_index} for {station_id} to {status_color}")
            self.led_controller.set_led(led_index, status_color)
            
        print(DISPLAY_FORMATTING["SEPARATOR_LINE"])
    
    def print_led_summary(self, airport_data, display_mode, current_forecast_hour):
        """Print a summary of all LEDs with their colors and airport names"""
        self.logger.info("Displaying LED summary")
        print("\n" + DISPLAY_FORMATTING["HEADER_LINE"])
        print("LED Summary:")
        print(DISPLAY_FORMATTING["SEPARATOR_LINE"])
        
        sorted_airports = self._get_sorted_airports()
        
        for led_index, icao, name in sorted_airports:
            airport_info = airport_data.get(icao)
            # Find airport config for this ICAO
            airport_config = None
            for config in self.config["airports"]:
                if config["icao"] == icao:
                    airport_config = config
                    break
            
            status_color, flight_category = LEDStatusCalculator.get_status_for_airport(
                icao, airport_info, display_mode, current_forecast_hour, airport_config
            )
            
            # Get warning text if applicable
            warning_text = ""
            if (status_color == "YELLOW" and 
                display_mode != 2 and  # DisplayMode.AIRPORTS_VISITED
                icao in airport_data):
                warning_text = get_warning_text(
                    status_color, airport_data[icao].get("raw_metar", ""), icao,
                    airport_data[icao].get("wind_data"), self.config
                )
            
            # Print the LED summary line
            color_code = COLORS.get(status_color, COLORS["RESET"])
            print(f"LED {led_index:2d}: {color_code}{DISPLAY_FORMATTING['LED_INDICATOR']}{COLORS['RESET']} {icao} - {color_code}{flight_category}{warning_text}{COLORS['RESET']} - {name}")
        
        self._print_mode_indicator_led(display_mode, current_forecast_hour)
        print(DISPLAY_FORMATTING["HEADER_LINE"])
    
    def _get_sorted_airports(self):
        """Get airports sorted by LED index"""
        return sorted(
            [(info["led"], icao, info["name"]) 
             for icao, info in zip(
                 [airport["icao"] for airport in self.config["airports"]],
                 [airport for airport in self.config["airports"]]
             ) 
             if info["led"] < self.config.get("led_count", 0)],
            key=lambda x: x[0]
        )
    
    def _print_mode_indicator_led(self, display_mode, current_forecast_hour):
        """Print the mode indicator LED status"""
        mode_led_index = self.config.get("mode_indicator_led")
        if mode_led_index is None or mode_led_index >= self.config.get("led_count", 0):
            return
            
        indicator_color = MODE_INDICATOR_COLOR
        if display_mode == 0:  # METAR
            mode_name = MODE_NAMES["METAR"]
        elif display_mode == 1:  # TAF
            mode_name = MODE_NAMES["TAF"].format(hour=current_forecast_hour)
        elif display_mode == 2:  # AIRPORTS_VISITED
            mode_name = MODE_NAMES["AIRPORTS_VISITED"]
        else:  # TEST
            mode_name = MODE_NAMES["TEST"]
            
        color_code = COLORS.get(indicator_color, COLORS["RESET"])
        print(f"LED {mode_led_index:2d}: {color_code}{DISPLAY_FORMATTING['LED_INDICATOR']}{COLORS['RESET']} Mode Indicator - {color_code}{mode_name}{COLORS['RESET']}")