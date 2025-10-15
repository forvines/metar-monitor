#!/usr/bin/env python3
"""
Mode Manager

Handles display mode switching and LED display updates.
"""

import logging
from constants import DisplayMode


class ModeManager:
    """Manages display modes and LED updates"""
    
    def __init__(self, config, led_controller=None):
        self.config = config
        self.led_controller = led_controller
        self.display_mode = DisplayMode.METAR
        self.current_forecast_hour = 6
        self.forecast_hour_index = 0
        self.logger = logging.getLogger("mode_manager")
        
        # Create airport to LED mapping
        self.airport_to_led = {}
        for airport_info in config["airports"]:
            icao = airport_info["icao"]
            led_index = airport_info["led"]
            if led_index < config.get("led_count", 0):
                self.airport_to_led[icao] = led_index
        
        # Create legend LEDs mapping
        self.legend_leds = {}
        if "legend" in config:
            for legend_item in config["legend"]:
                name = legend_item["name"]
                color = legend_item["color"]
                led = legend_item["led"]
                self.legend_leds[led] = {"name": name, "color": color}
            self.logger.debug(f"Initialized {len(self.legend_leds)} legend LEDs")
    
    def toggle_display_mode(self):
        """Cycle through display modes"""
        forecast_hours = self.config["forecast_hours"]
        if not isinstance(forecast_hours, list) or not forecast_hours:
            forecast_hours = [4]
        
        if self.display_mode == DisplayMode.METAR:
            self.display_mode = DisplayMode.TAF
            self.forecast_hour_index = 0
            self.current_forecast_hour = forecast_hours[self.forecast_hour_index]
            self.logger.info(f"Display mode changed to TAF {self.current_forecast_hour}-Hour Forecast")
        elif self.display_mode == DisplayMode.TAF:
            self.forecast_hour_index = (self.forecast_hour_index + 1) % len(forecast_hours)
            
            if self.forecast_hour_index == 0:
                self.display_mode = DisplayMode.AIRPORTS_VISITED
                self.logger.info("Display mode changed to Airports Visited")
            else:
                self.current_forecast_hour = forecast_hours[self.forecast_hour_index]
                self.logger.info(f"Display mode changed to TAF {self.current_forecast_hour}-Hour Forecast")
        elif self.display_mode == DisplayMode.AIRPORTS_VISITED:
            self.display_mode = DisplayMode.TEST
            self.logger.info("Display mode changed to Test Mode")
        else:
            self.display_mode = DisplayMode.METAR
            self.logger.info("Display mode changed to METAR (Current Conditions)")
            
        return self.display_mode
    
    def update_led_display(self, airport_data):
        """Update LEDs based on current display mode"""
        if not self.led_controller:
            self.logger.debug("LED controller not available, skipping LED display update")
            return
            
        mode_name = "METAR" if self.display_mode == DisplayMode.METAR else \
                   f"TAF {self.current_forecast_hour}h" if self.display_mode == DisplayMode.TAF else \
                   "Airports Visited" if self.display_mode == DisplayMode.AIRPORTS_VISITED else \
                   "Test"
        self.logger.info("Updating LED display in %s mode", mode_name)
        
        # Update airport LEDs if we have data
        if airport_data:
            visited_airports = self.config.get("visited_airports", [])
            
            for airport, data in airport_data.items():
                if airport not in self.airport_to_led:
                    continue
                    
                led_index = self.airport_to_led[airport]
                status_color = self._get_led_color_for_mode(airport, data, visited_airports)
                self.led_controller.set_led(led_index, status_color)
        
        # Update the legend LEDs
        if self.legend_leds:
            self._set_legend_leds()
            
        # Update mode LEDs
        self._update_mode_leds()
    
    def _get_led_color_for_mode(self, airport, data, visited_airports):
        """Get LED color based on current display mode"""
        if self.display_mode == DisplayMode.METAR:
            return data.get("status_color", "OFF")
        elif self.display_mode == DisplayMode.TAF:
            if "forecasts" in data and data["forecasts"]:
                forecast_hour = self.current_forecast_hour
                if forecast_hour in data["forecasts"]:
                    return data["forecasts"][forecast_hour]["color"]
                else:
                    # Find closest available forecast hour
                    available_hours = sorted(data["forecasts"].keys())
                    closest_hour = min(available_hours, key=lambda x: abs(x - forecast_hour))
                    return data["forecasts"][closest_hour]["color"]
            return "OFF"
        elif self.display_mode == DisplayMode.AIRPORTS_VISITED:
            return "GREEN" if airport in visited_airports else "RED"
        else:  # DisplayMode.TEST
            return "GREEN" if data.get("raw_metar") else "RED"
    
    def _set_legend_leds(self):
        """Set the legend LEDs to their corresponding colors"""
        if not self.led_controller:
            return
        
        self.logger.info("Setting up legend LEDs")
        for led_index, legend_item in self.legend_leds.items():
            color = legend_item["color"]
            name = legend_item["name"]
            self.led_controller.set_led(led_index, color)
            self.logger.debug(f"Set legend LED {led_index} to {color} ({name})")
            
        self.logger.info(f"Legend display initialized with {len(self.legend_leds)} LEDs")
    
    def _update_mode_leds(self):
        """Update the mode LEDs"""
        mode_leds_cfg = self.config.get("mode_leds")
        if not mode_leds_cfg or not self.led_controller:
            return
            
        # Clear all mode LEDs first
        all_mode_leds = []
        if "metar" in mode_leds_cfg:
            all_mode_leds.append(mode_leds_cfg["metar"])
        if "airports_visited" in mode_leds_cfg:
            all_mode_leds.append(mode_leds_cfg["airports_visited"])
        if "test" in mode_leds_cfg:
            all_mode_leds.append(mode_leds_cfg["test"])
        taf_map = mode_leds_cfg.get("taf", {})
        for v in taf_map.values():
            try:
                all_mode_leds.append(int(v))
            except Exception:
                continue

        # Turn off all mode LEDs
        for idx in all_mode_leds:
            if isinstance(idx, int) and idx < self.config.get("led_count", 0):
                self.led_controller.set_led(idx, "OFF")

        # Light up the active mode LED
        active_idx = None
        if self.display_mode == DisplayMode.METAR:
            active_idx = mode_leds_cfg.get("metar")
        elif self.display_mode == DisplayMode.TAF:
            if taf_map:
                key = str(self.current_forecast_hour)
                if key in taf_map:
                    active_idx = int(taf_map[key])
                else:
                    try:
                        closest_key = min(taf_map.keys(), key=lambda k: abs(int(k) - self.current_forecast_hour))
                        active_idx = int(taf_map[closest_key])
                    except Exception:
                        active_idx = None
        elif self.display_mode == DisplayMode.AIRPORTS_VISITED:
            active_idx = mode_leds_cfg.get("airports_visited")
        else:  # DisplayMode.TEST
            active_idx = mode_leds_cfg.get("test")

        if active_idx is not None and active_idx < self.config.get("led_count", 0):
            self.led_controller.set_led(active_idx, "WHITE")
            self.logger.debug(f"Set mode LED {active_idx} to WHITE")