#!/usr/bin/env python3
"""
Airport Data Manager

Handles fetching, processing, and storing airport weather data.
"""

import logging
from datetime import datetime
from metar_api_client import METARAPIClient, APIRequestFailed
from airport_utils import calculate_airport_crosswind
from metar_processor import determine_flight_category
from taf_processor import process_taf_data as process_taf_data_module
from weather_status import determine_status_color


class AirportDataManager:
    """Manages airport weather data fetching and processing"""
    
    def __init__(self, config):
        self.config = config
        self.airport_data = {}
        self.last_update = None
        self.logger = logging.getLogger("airport_data_manager")
        
        # Initialize API client
        self.api_client = METARAPIClient(
            base_metar_url=config["metar_url"],
            base_taf_url=config["taf_url"]
        )
        
        # Create airport name mapping
        self.airport_names = {airport["icao"]: airport["name"] for airport in config["airports"]}
    
    def fetch_and_process_data(self):
        """Fetch and process METAR and TAF data for all configured airports"""
        airports = [airport["icao"] for airport in self.config["airports"]]
        
        # Reset data
        self.airport_data = {}
        self.last_update = datetime.now()
        
        # Fetch METAR data
        airport_metars = self._fetch_raw_metar_data(airports)
        if not airport_metars:
            self.logger.error("No METAR data was retrieved.")
            return False
            
        # Fetch TAF data
        all_taf_data = self._fetch_all_taf_data(airports)
        
        # Process each airport's data
        for station_id, metar_data in airport_metars.items():
            if station_id in self.airport_names:
                taf_data = all_taf_data.get(station_id, None)
                self._process_airport_data(station_id, metar_data, taf_data, self.airport_names[station_id])
        
        return len(self.airport_data) > 0
    
    def _fetch_raw_metar_data(self, airports):
        """Fetch raw METAR data from the API"""
        try:
            self.logger.info("Fetching METAR data for %d airports", len(airports))
            all_metar_data = self.api_client.fetch_metar_data(airports)
            airport_metars = self.api_client.get_most_recent_metars(all_metar_data)
            self.logger.info("Successfully retrieved METAR data for %d airports", len(airport_metars))
            return airport_metars
        except APIRequestFailed as e:
            self.logger.error("API request failed: %s", str(e))
            return {}
        except Exception as e:
            self.logger.exception("Unexpected error fetching METAR data: %s", str(e))
            return {}
    
    def _fetch_all_taf_data(self, airports):
        """Fetch TAF data for all airports"""
        try:
            self.logger.info("Fetching TAF data for %d airports", len(airports))
            taf_data_list = self.api_client.fetch_taf_data(airports)
            all_taf_data = self.api_client.group_tafs_by_airport(taf_data_list)
            self.logger.info("Successfully retrieved TAF data for %d airports", len(all_taf_data))
            return all_taf_data
        except APIRequestFailed as e:
            self.logger.error("TAF API request failed: %s", str(e))
            return {}
        except Exception as e:
            self.logger.exception("Unexpected error fetching TAF data: %s", str(e))
            return {}
    
    def _process_airport_data(self, station_id, metar_data, taf_data, airport_name):
        """Process METAR and TAF data for a single airport"""
        raw_text = metar_data.get("rawOb")
        
        # Determine flight category
        flight_category = determine_flight_category(metar_data)
        
        # Calculate crosswind
        wind_data = calculate_airport_crosswind(self.config, station_id, raw_text)
        
        # Determine status color
        status_color = determine_status_color(raw_text, flight_category, wind_data)
        
        # Initialize airport data
        self.airport_data[station_id] = {
            "raw_metar": raw_text,
            "flight_category": flight_category,
            "status_color": status_color,
            "forecast": None,
            "forecast_category": None,
            "forecast_color": None,
            "name": airport_name,
            "wind_data": wind_data
        }
        
        # Process TAF data if available
        if taf_data:
            self._process_taf_data(station_id, taf_data)
    
    def _process_taf_data(self, airport, taf_data_list):
        """Process TAF data for a specific airport"""
        try:
            self.logger.debug("Processing TAF data for %s", airport)
            
            forecast_hours = self.config["forecast_hours"]
            if not isinstance(forecast_hours, list):
                forecast_hours = [forecast_hours]
                
            # Use the taf_processor module
            taf_data = process_taf_data_module(airport, taf_data_list, forecast_hours)
            
            # Store the results
            if taf_data["forecast"]:
                self.airport_data[airport]["forecast"] = taf_data["forecast"]
                self.airport_data[airport]["forecasts"] = {}
                
                for hours, forecast in taf_data["forecasts"].items():
                    # Apply status color
                    forecast_text = forecast.get("taf_summary", "")
                    forecast_category = forecast.get("category", "Unknown")
                    wind_data = forecast.get("wind_data", None)
                    
                    # Determine status color with crosswind information
                    forecast_color = determine_status_color(forecast_text, forecast_category, wind_data)
                    
                    # Store the forecast information with color
                    self.airport_data[airport]["forecasts"][hours] = forecast.copy()
                    self.airport_data[airport]["forecasts"][hours]["color"] = forecast_color
                    
                    # For backward compatibility
                    if hours == 6 or "forecast_category" not in self.airport_data[airport]:
                        self.airport_data[airport]["forecast_category"] = forecast_category
                        self.airport_data[airport]["forecast_color"] = forecast_color
                        self.airport_data[airport]["forecast_taf_summary"] = forecast.get("taf_summary", "")
                        
                self.logger.debug("Successfully processed forecast periods for %s", airport)
            else:
                self.logger.warning("No valid TAF data found for %s", airport)
            
        except Exception as e:
            self.logger.exception("Error processing TAF data for %s: %s", airport, str(e))