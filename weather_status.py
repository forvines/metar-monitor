#!/usr/bin/env python3
"""
Weather status module for METAR Monitor
Handles determining status colors and generating warning text
"""

import re
import logging
from typing import Dict, Any, Optional, Union

from constants import THRESHOLDS, CATEGORY_COLOR_MAP, REGEX_PATTERNS

logger = logging.getLogger(__name__)


def determine_status_color(raw_weather_text: str, flight_category: str, wind_data: Dict = None) -> str:
    """Determine the status color based on weather data and wind/crosswind conditions
    
    Args:
        raw_weather_text: Raw METAR/TAF string
        flight_category: Flight category (VFR, MVFR, IFR, LIFR)
        wind_data: Optional wind data including crosswind information
        
    Returns:
        str: Color name representing the flight status
    """
    # Check for crosswind threshold exceedance first if wind data is provided
    if wind_data and wind_data.get("crosswind") is not None:
        crosswind_threshold = THRESHOLDS["CROSSWINDS"]
        if wind_data["crosswind"] > crosswind_threshold:
            return "YELLOW"
    
    # Check for strong winds, gusts, or thunderstorms
    if raw_weather_text:
        # Check for winds over threshold knots
        wind_match = re.search(REGEX_PATTERNS["WINDS"], raw_weather_text)
        if wind_match and int(wind_match.group(1)) > THRESHOLDS["WINDS"]:
            return "YELLOW"
        
        # Check for gusts over threshold knots
        gust_match = re.search(REGEX_PATTERNS["GUSTS"], raw_weather_text)
        if gust_match and int(gust_match.group(1)) > THRESHOLDS["GUSTS"]:
            return "YELLOW"
        
        # Check for thunderstorms
        if any(pattern in raw_weather_text for pattern in REGEX_PATTERNS["THUNDERSTORM"]):
            return "YELLOW"
    
    # Then check flight category and map to appropriate color
    if flight_category in CATEGORY_COLOR_MAP:
        return CATEGORY_COLOR_MAP[flight_category]
    
    # Default if we can't determine
    return "OFF"


def get_warning_text(status_color: str, raw_text: str, airport_id: str = None, wind_data: Dict = None, config: Dict = None) -> str:
    """Generate a warning text description for weather conditions
    
    Args:
        status_color: The color indicating the airport status
        raw_text: Raw METAR/TAF string
        airport_id: Optional airport ID for reference
        wind_data: Optional dictionary with wind data
        config: Optional configuration dictionary
        
    Returns:
        str: Warning text describing the reason for the status color
    """
    if status_color != "YELLOW":
        return ""
        
    # Check if we have wind data with crosswind information
    if wind_data and "crosswind" in wind_data and "active_runway" in wind_data and "direction" in wind_data:
        crosswind = wind_data["crosswind"]
        runway = wind_data["active_runway"]["name"]
        wind_direction = wind_data["direction"]
        threshold = 10  # Default - should be from config in real use
        if config:
            threshold = config.get("crosswind_threshold", 10)
            
        if crosswind > threshold:
            return f" - Crosswind {crosswind:.1f}KT from {wind_direction:03d}° on RWY {runway}"
    
    # Check for thunderstorms (highest priority)
    if any(pattern in raw_text for pattern in REGEX_PATTERNS["THUNDERSTORM"]):
        return " - Thunderstorm"
        
    # Check for gusts (second priority)
    if "G" in raw_text and re.search(REGEX_PATTERNS["GUSTS"], raw_text):
        gust_match = re.search(REGEX_PATTERNS["GUSTS"], raw_text)
        return f" - Gusts {gust_match.group(1)}KT"
        
    # Check for strong winds (third priority)
    if re.search(REGEX_PATTERNS["WINDS"], raw_text):
        wind_match = re.search(REGEX_PATTERNS["WINDS"], raw_text)
        return f" - Winds {wind_match.group(1)}KT"
        
    # Default warning if we can't determine the specific reason
    return " - Weather warning"
