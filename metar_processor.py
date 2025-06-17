#!/usr/bin/env python3
"""
METAR data processing module for METAR Monitor
Handles parsing and analysis of METAR data
"""

import logging
from typing import Dict, Any, Optional, Tuple

from constants import THRESHOLDS

logger = logging.getLogger(__name__)


def determine_flight_category_from_values(visibility: Optional[float], ceiling: Optional[int]) -> str:
    """Determine flight category based on visibility and ceiling values
    
    Args:
        visibility: Visibility in statute miles
        ceiling: Ceiling height in feet
        
    Returns:
        str: Flight category (VFR, MVFR, IFR, LIFR, or Unknown)
    """
    if visibility is None and ceiling is None:
        return "Unknown"
    
    # Check for LIFR conditions first (lowest ceiling/visibility)
    lifr_vis = THRESHOLDS["VISIBILITY"]["LIFR"]
    lifr_ceiling = THRESHOLDS["CEILING"]["LIFR"]
    if (visibility is not None and visibility < lifr_vis) or (ceiling is not None and ceiling < lifr_ceiling):
        return "LIFR"  # Low IFR
    
    # Check for IFR conditions
    ifr_vis = THRESHOLDS["VISIBILITY"]["IFR"]
    ifr_ceiling = THRESHOLDS["CEILING"]["IFR"]
    if (visibility is not None and visibility < ifr_vis) or (ceiling is not None and ceiling < ifr_ceiling):
        return "IFR"   # IFR
    
    # Check for MVFR conditions
    mvfr_vis = THRESHOLDS["VISIBILITY"]["MVFR"]
    mvfr_ceiling = THRESHOLDS["CEILING"]["MVFR"]
    if (visibility is not None and visibility < mvfr_vis) or (ceiling is not None and ceiling < mvfr_ceiling):
        return "MVFR"  # Marginal VFR
    
    # If none of the above, it's VFR
    return "VFR"   # VFR


def determine_flight_category(metar: Dict[str, Any]) -> str:
    """Determine flight category based on METAR data
    
    Args:
        metar: Dictionary containing METAR data
        
    Returns:
        str: Flight category (VFR, MVFR, IFR, LIFR, or Unknown)
    """
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
                try:
                    base = int(base)
                    if ceiling is None or base < ceiling:
                        ceiling = base
                except (ValueError, TypeError):
                    pass
    
    # Use helper method to determine flight category
    return determine_flight_category_from_values(visibility, ceiling)


def process_metar_data(station_id: str, metar_data: Dict[str, Any], airport_name: str) -> Dict[str, Any]:
    """Process METAR data for a single airport
    
    Args:
        station_id: The ICAO identifier of the airport
        metar_data: The raw METAR data from the API
        airport_name: The friendly name of the airport
        
    Returns:
        dict: Processed METAR data including flight category
    """
    raw_text = metar_data.get("rawOb")
    
    # Determine flight category based on ceiling and visibility
    flight_category = determine_flight_category(metar_data)
    
    # Create processed METAR data
    processed_data = {
        "raw_metar": raw_text,
        "flight_category": flight_category,
        "name": airport_name
    }
    
    logger.info("Processed METAR for %s - %s: %s", station_id, airport_name, flight_category)
    
    return processed_data
