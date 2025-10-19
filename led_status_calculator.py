#!/usr/bin/env python3
"""
LED Status Calculator

Handles the logic for determining LED colors and status text based on display mode
and airport data availability.
"""

from constants import DisplayMode


class LEDStatusCalculator:
    """Calculates LED status based on display mode and airport data"""
    
    @staticmethod
    def get_status_for_airport(icao, airport_data, display_mode, current_forecast_hour, airport_config):
        """
        Determine status color and flight category for an airport LED
        
        Args:
            icao (str): Airport ICAO code
            airport_data (dict): Airport data if available, None otherwise
            display_mode (int): Current display mode
            current_forecast_hour (int): Current forecast hour for TAF mode
            airport_config (dict): Airport configuration with visited flag
            
        Returns:
            tuple: (status_color, flight_category)
        """
        if airport_data:
            return LEDStatusCalculator._get_status_with_data(
                icao, airport_data, display_mode, current_forecast_hour, airport_config
            )
        else:
            return LEDStatusCalculator._get_status_without_data(
                icao, display_mode, airport_config
            )
    
    @staticmethod
    def _get_status_with_data(icao, airport_data, display_mode, current_forecast_hour, airport_config):
        """Get status when airport data is available"""
        if display_mode == DisplayMode.METAR:
            return (
                airport_data.get("status_color", "OFF"),
                airport_data.get("flight_category", "Unknown")
            )
        elif display_mode == DisplayMode.TAF:
            return LEDStatusCalculator._get_taf_status(airport_data, current_forecast_hour)
        elif display_mode == DisplayMode.AIRPORTS_VISITED:
            return LEDStatusCalculator._get_visited_status(airport_config)
        else:  # DisplayMode.TEST
            has_metar = bool(airport_data.get("raw_metar"))
            return ("GREEN" if has_metar else "RED", "Valid METAR" if has_metar else "No METAR")
    
    @staticmethod
    def _get_status_without_data(icao, display_mode, airport_config):
        """Get status when no airport data is available"""
        if display_mode == DisplayMode.AIRPORTS_VISITED:
            return LEDStatusCalculator._get_visited_status(airport_config)
        elif display_mode == DisplayMode.TEST:
            return ("RED", "No METAR")
        else:
            return ("OFF", "No Data")
    
    @staticmethod
    def _get_taf_status(airport_data, current_forecast_hour):
        """Get TAF forecast status"""
        forecasts = airport_data.get("forecasts", {})
        if not forecasts:
            return ("OFF", "Unknown")
            
        if current_forecast_hour in forecasts:
            forecast = forecasts[current_forecast_hour]
            return (forecast["color"], forecast.get("category", "Unknown"))
        
        # Find closest available forecast hour
        available_hours = sorted(forecasts.keys())
        if available_hours:
            closest_hour = min(available_hours, key=lambda x: abs(x - current_forecast_hour))
            forecast = forecasts[closest_hour]
            return (forecast["color"], forecast.get("category", "Unknown"))
        
        return ("OFF", "Unknown")
    
    @staticmethod
    def _get_visited_status(airport_config):
        """Get visited airport status"""
        is_visited = airport_config.get("visited", False) if airport_config else False
        return ("GREEN" if is_visited else "RED", "Visited" if is_visited else "Not Visited")