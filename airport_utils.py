#!/usr/bin/env python3
"""
Airport utilities for METAR Monitor.
Contains functions for runway data management and crosswind calculations.
Uses runway data directly from the metar_config.json file.
"""

import re
import math
import logging

logger = logging.getLogger("airport_utils")

def get_runway_data(config, icao):
    """Get runway data for a specific airport by ICAO code from config.
    
    Args:
        config (dict): The configuration dictionary containing airport data
        icao (str): The ICAO code of the airport
        
    Returns:
        list: A list of runway dictionaries for the airport, or an empty list
              if the airport is not found or has no runway data
    """
    # Find the matching airport in the config
    for airport in config.get("airports", []):
        if airport["icao"] == icao:
            return airport.get("runways", [])
            
    return []

def determine_active_runway(wind_direction, runways):
    """Determine most likely active runway based on wind direction.
    
    Selects the runway with minimal crosswind by finding the runway
    heading that produces the smallest angle with the wind direction.
    
    Args:
        wind_direction: Direction in degrees (0-360) or "VRB" for variable
        runways: List of runway dictionaries with "name" and "direction" keys
        
    Returns:
        dict: The most likely active runway dictionary, or None if no runway
              can be determined (e.g., variable winds or no runways provided)
    """
    if wind_direction == "VRB" or not runways:
        return None
        
    try:
        wind_dir = int(wind_direction)
        min_angle = 180
        best_runway = None
        
        for runway in runways:
            # Calculate the absolute angle between wind and runway
            runway_dir = int(runway["direction"])
            
            # Calculate angle difference (0-180)
            angle = abs((runway_dir - wind_dir + 180) % 360 - 180)
            
            # Find the runway with the smallest angle to the wind
            if angle < min_angle:
                min_angle = angle
                best_runway = runway
                
        return best_runway
    except (ValueError, TypeError):
        logger.warning(f"Invalid wind direction: {wind_direction}")
        # If wind direction can't be converted to an integer
        return None

def calculate_crosswind(wind_speed, wind_direction, runway_direction):
    """Calculate crosswind and headwind components.
    
    Args:
        wind_speed (int): Wind speed in knots
        wind_direction (int): Wind direction in degrees
        runway_direction (int): Runway direction in degrees
        
    Returns:
        tuple: (crosswind, headwind) components in knots,
               or (None, None) if inputs are invalid
    """
    try:
        # Ensure all inputs are proper numbers
        wind_speed = float(wind_speed)
        wind_direction = float(wind_direction)
        runway_direction = float(runway_direction)
        
        # Calculate the angular difference between wind and runway
        angle_diff = abs((wind_direction - runway_direction + 180) % 360 - 180)
        angle_rad = math.radians(angle_diff)
        
        # Calculate components
        crosswind = abs(wind_speed * math.sin(angle_rad))
        headwind = wind_speed * math.cos(angle_rad)
        
        return crosswind, headwind
    except (ValueError, TypeError) as e:
        logger.warning(f"Error calculating crosswind: {e}")
        return None, None

def extract_wind_data(raw_metar):
    """Extract wind direction, speed, and gusts from METAR.
    
    Args:
        raw_metar (str): Raw METAR string
        
    Returns:
        dict: Dictionary with wind data including direction, speed, gust, and variable flag
    """
    wind_data = {"direction": None, "speed": None, "gust": None, "variable": False}
    
    if not raw_metar:
        return wind_data
    
    # Check for variable winds
    if "VRB" in raw_metar:
        wind_data["variable"] = True
        # Try to extract speed from VRB format
        vrb_match = re.search(r'VRB(\d{2})KT', raw_metar)
        if vrb_match:
            wind_data["speed"] = int(vrb_match.group(1))
        return wind_data
    
    # Regular wind pattern (e.g., 27015KT or 27015G25KT)
    wind_match = re.search(r'(\d{3})(\d{2})(?:G(\d+))?KT', raw_metar)
    if wind_match:
        wind_data["direction"] = int(wind_match.group(1))
        wind_data["speed"] = int(wind_match.group(2))
        if wind_match.group(3):  # Gust data
            wind_data["gust"] = int(wind_match.group(3))
    
    return wind_data

def calculate_airport_crosswind(config, airport_id, raw_metar):
    """Calculate crosswind for an airport based on METAR and runway data
    
    Args:
        config (dict): The configuration dictionary containing airport data
        airport_id (str): ICAO code of the airport
        raw_metar (str): Raw METAR string
        
    Returns:
        dict: Wind data dictionary including crosswind information if available
    """
    # Extract wind data from METAR
    wind_data = extract_wind_data(raw_metar)
    
    # Calculate crosswind component if possible
    if not wind_data["variable"] and wind_data["direction"] is not None and wind_data["speed"] is not None:
        # Get runway data for this airport
        runways = get_runway_data(config, airport_id)
        
        if runways:
            # Determine most likely active runway based on wind direction
            active_runway = determine_active_runway(wind_data["direction"], runways)
            
            if active_runway:
                # Calculate crosswind component
                crosswind, headwind = calculate_crosswind(
                    wind_data["speed"], 
                    wind_data["direction"], 
                    active_runway["direction"]
                )
                
                if crosswind is not None:
                    # Store crosswind information in wind_data
                    wind_data["crosswind"] = crosswind
                    wind_data["headwind"] = headwind
                    wind_data["active_runway"] = active_runway
                    
                    logger.debug(
                        "%s: Wind %03d@%02d, Runway %s (%03d°), Crosswind: %.1f, Headwind: %.1f",
                        airport_id, wind_data["direction"], wind_data["speed"],
                        active_runway["name"], active_runway["direction"],
                        crosswind, headwind
                    )
    
    return wind_data
