#!/usr/bin/env python3
"""
TAF data processing module for METAR Monitor
Handles parsing and analysis of TAF (forecast) data
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

from constants import THRESHOLDS
from metar_processor import determine_flight_category_from_values

logger = logging.getLogger(__name__)


def get_most_recent_taf(taf_data_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract the most recent TAF from a list of TAFs
    
    Args:
        taf_data_list: List of TAF data objects from the API
        
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


def find_relevant_forecast_period(forecast_periods: List[Dict[str, Any]], target_time: datetime) -> Tuple[Optional[Dict[str, Any]], Optional[datetime]]:
    """Find the forecast period that covers the target time
    
    Args:
        forecast_periods: List of forecast period objects from the TAF data
        target_time: The target time to find a forecast for
        
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
            logger.warning("Invalid timestamp in forecast period: %s", str(e))
            continue
            
    return None, None


def format_clouds_info(clouds: Optional[List[Dict[str, Any]]]) -> str:
    """Format cloud information into a readable string
    
    Args:
        clouds: List of cloud data objects, each containing 'cover' and 'base'
        
    Returns:
        str: Formatted string of cloud information (e.g., "BKN025 OVC080")
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


def format_wind(wdir: Optional[Union[str, int]], wspd: Optional[Union[str, int]]) -> str:
    """Format wind direction and speed into a standard format
    
    Args:
        wdir: Wind direction in degrees
        wspd: Wind speed in knots
        
    Returns:
        str: Formatted wind string (e.g., "27015")
    """
    try:
        # Try to format as integers with padding
        wdir_fmt = f"{int(wdir):03d}" if wdir is not None else "---"
        wspd_fmt = f"{int(wspd):02d}" if wspd is not None else "--"
        return f"{wdir_fmt}{wspd_fmt}"
    except (ValueError, TypeError):
        # If conversion fails, just concatenate the raw values
        return f"{wdir or '---'}{wspd or '--'}"


def determine_forecast_category(forecast_period: Dict[str, Any]) -> str:
    """Determine flight category based on forecast data
    
    Args:
        forecast_period: A forecast period object from the TAF data
        
    Returns:
        str: Flight category (VFR, MVFR, IFR, LIFR, or Unknown)
    """
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
    return determine_flight_category_from_values(visibility, ceiling)


def process_forecast_period(period: Optional[Dict[str, Any]], from_time: Optional[datetime], airport: str, runway_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """Process a single forecast period and return its information
    
    Args:
        period: A forecast period object from the TAF data
        from_time: The start time of this forecast period
        airport: The ICAO identifier of the airport
        runway_data: Optional runway data for crosswind calculations
        
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
    clouds_str = format_clouds_info(period.get("clouds", []))
    
    # Format wind and create summary
    wind_text = format_wind(wdir, wspd)
    taf_summary = f"{fcst_change} {from_time_str} {wind_text}KT {visib} {clouds_str}"
    
    # Determine flight category
    forecast_category = determine_forecast_category(period)
    
    return {
        "category": forecast_category,
        "taf_summary": taf_summary,
        "time_from": from_time,
        "time_to": datetime.fromtimestamp(period.get("timeTo")),
        "raw_data": period
    }


def process_taf_data(airport: str, taf_data_list: List[Dict[str, Any]], forecast_hours: List[int]) -> Dict[str, Any]:
    """Process TAF data for a specific airport
    
    Args:
        airport: The ICAO identifier of the airport
        taf_data_list: List of TAF data objects for the airport
        forecast_hours: List of hours ahead to forecast using TAF
        
    Returns:
        dict: Dictionary with forecast information for each requested hour
    """
    taf_result = {
        "forecast": None,
        "forecasts": {}
    }
    
    try:
        logger.debug("Processing TAF data for %s", airport)
        
        # Get the most recent TAF
        most_recent_taf = get_most_recent_taf(taf_data_list)
        if not most_recent_taf:
            logger.warning("No valid TAF found for %s", airport)
            return taf_result
        
        # Store the raw TAF
        raw_taf = most_recent_taf.get("rawTAF")
        taf_result["forecast"] = raw_taf
        
        # Ensure forecast_hours is a list
        if not isinstance(forecast_hours, list):
            forecast_hours = [forecast_hours]
        
        # Get all forecast periods from the TAF
        forecast_periods = most_recent_taf.get("fcsts", [])
        if not forecast_periods:
            logger.warning("No forecast periods in TAF for %s", airport)
            return taf_result
            
        # Process each forecast hour
        processed_hours = 0
        for hours in forecast_hours:
            # Calculate the target forecast time
            target_time = datetime.now() + timedelta(hours=hours)
            
            # Find the relevant forecast period
            relevant_period, from_time = find_relevant_forecast_period(
                forecast_periods, target_time
            )
            
            if not relevant_period:
                logger.debug("No forecast period found for %s at +%d hours", airport, hours)
                continue
            
            # Process the forecast period
            forecast_data = process_forecast_period(relevant_period, from_time, airport)
            if not forecast_data:
                logger.debug("Failed to process forecast period for %s at +%d hours", airport, hours)
                continue
                
            # Store the forecast information
            taf_result["forecasts"][hours] = forecast_data
            processed_hours += 1
            
            # For backward compatibility, store the 6-hour forecast (or first forecast if no 6-hour)
            if hours == 6 or "forecast_category" not in taf_result:
                taf_result["forecast_category"] = forecast_data["category"]
                taf_result["forecast_taf_summary"] = forecast_data["taf_summary"]
        
        logger.debug("Successfully processed %d forecast periods for %s", processed_hours, airport)
        
    except Exception as e:
        logger.exception("Error processing TAF data for %s: %s", airport, str(e))
        
    return taf_result
