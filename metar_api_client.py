#!/usr/bin/env python3
"""
API Client for METAR Status Monitor
Handles API requests with validation, timeout, and retry logic
"""

import urllib.request
import json
import time
import logging
import random
import socket
from urllib.error import URLError, HTTPError
from typing import Dict, List, Any, Optional, Union, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("metar_monitor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("metar_api_client")

class APIRequestFailed(Exception):
    """Exception raised when an API request fails after all retries."""
    pass

class METARAPIClient:
    """Client for making API requests to aviation weather services with retry logic"""
    
    def __init__(
        self, 
        base_metar_url: str = "https://aviationweather.gov/api/data/metar",
        base_taf_url: str = "https://aviationweather.gov/api/data/taf",
        max_retries: int = 3,
        base_delay: float = 2.0,
        timeout: float = 10.0,
        jitter: float = 0.5
    ):
        """Initialize the API client
        
        Args:
            base_metar_url: Base URL for METAR API
            base_taf_url: Base URL for TAF API
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            timeout: Timeout for API requests in seconds
            jitter: Random jitter factor to avoid thundering herd
        """
        self.base_metar_url = base_metar_url
        self.base_taf_url = base_taf_url
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout
        self.jitter = jitter
        
        logger.info("Initialized METAR API Client with base URLs: %s, %s", 
                   base_metar_url, base_taf_url)
    
    def _make_request(self, url: str) -> Any:
        """Make an API request with retry logic
        
        Args:
            url: Complete URL for the API request
            
        Returns:
            Parsed JSON response
            
        Raises:
            APIRequestFailed: If the request fails after all retries
        """
        retries = 0
        last_exception = None
        
        while retries <= self.max_retries:
            try:
                logger.debug("Making request to %s (Attempt %d/%d)", 
                            url, retries + 1, self.max_retries + 1)
                
                # Create request with timeout
                req = urllib.request.Request(url)
                response = urllib.request.urlopen(req, timeout=self.timeout)
                
                # Read and parse the response
                data = response.read()
                json_data = json.loads(data)
                
                # Validate the response
                if not isinstance(json_data, (list, dict)):
                    raise ValueError(f"Invalid response format: expected list or dict, got {type(json_data)}")
                
                logger.debug("Request successful, received %d bytes", len(data))
                return json_data
                
            except HTTPError as e:
                logger.warning("HTTP error occurred: %s - %s", e.code, e.reason)
                last_exception = e
            except URLError as e:
                logger.warning("URL error occurred: %s", e.reason)
                last_exception = e
            except socket.timeout:
                logger.warning("Socket timeout occurred")
                last_exception = socket.timeout("Request timed out")
            except json.JSONDecodeError as e:
                logger.warning("JSON decode error: %s", str(e))
                last_exception = e
            except ValueError as e:
                logger.warning("Validation error: %s", str(e))
                last_exception = e
            except Exception as e:
                logger.warning("Unexpected error: %s", str(e), exc_info=True)
                last_exception = e
                
            # If we get here, the request failed and we should retry
            retries += 1
            
            if retries <= self.max_retries:
                # Calculate backoff delay with jitter
                delay = self.base_delay * (2 ** (retries - 1))  # Exponential backoff
                jitter_amount = random.uniform(-self.jitter, self.jitter)
                final_delay = delay * (1 + jitter_amount)
                
                logger.info("Retrying in %.2f seconds...", final_delay)
                time.sleep(final_delay)
        
        # If we get here, all retries failed
        logger.error("All %d attempts failed for URL: %s", 
                    self.max_retries + 1, url)
        
        raise APIRequestFailed(f"API request failed after {self.max_retries + 1} attempts") from last_exception
    
    def fetch_metar_data(self, airport_ids: List[str], hours: int = 2) -> List[Dict]:
        """Fetch METAR data for the specified airports
        
        Args:
            airport_ids: List of airport ICAO identifiers
            hours: Number of hours of data to retrieve
            
        Returns:
            List of METAR data dictionaries
            
        Raises:
            APIRequestFailed: If the request fails after all retries
        """
        # Convert list to comma-separated string
        airport_ids_str = ",".join(airport_ids)
        
        # Build the URL
        url = f"{self.base_metar_url}?ids={airport_ids_str}&format=json&hours={hours}"
        
        logger.info("Fetching METAR data for %d airports: %s", 
                   len(airport_ids), ", ".join([x for x in airport_ids]))
        
        try:
            response = self._make_request(url)
            
            # Validate the response
            if not isinstance(response, list):
                logger.error("Invalid METAR response format: expected list, got %s", type(response))
                raise ValueError(f"Invalid METAR response format: expected list, got {type(response)}")
            
            logger.info("Successfully retrieved METAR data for %d observations", len(response))
            
            # Additional validation
            for item in response:
                if not isinstance(item, dict):
                    logger.warning("Invalid METAR item format: expected dict, got %s", type(item))
                if 'icaoId' not in item:
                    logger.warning("METAR item missing icaoId field")
                    
            return response
            
        except Exception as e:
            logger.error("Failed to fetch METAR data: %s", str(e))
            raise
    
    def fetch_taf_data(self, airport_ids: List[str], hours: int = 12) -> List[Dict]:
        """Fetch TAF data for the specified airports
        
        Args:
            airport_ids: List of airport ICAO identifiers
            hours: Number of hours of data to retrieve
            
        Returns:
            List of TAF data dictionaries
            
        Raises:
            APIRequestFailed: If the request fails after all retries
        """
        # Convert list to comma-separated string
        airport_ids_str = ",".join(airport_ids)
        
        # Build the URL
        url = f"{self.base_taf_url}?ids={airport_ids_str}&format=json&hours={hours}"
        
        logger.info("Fetching TAF data for %d airports: %s",
                   len(airport_ids), ", ".join([x for x in airport_ids]))
        
        try:
            response = self._make_request(url)
            
            # Validate the response
            if not isinstance(response, list):
                logger.error("Invalid TAF response format: expected list, got %s", type(response))
                raise ValueError(f"Invalid TAF response format: expected list, got {type(response)}")
            
            logger.info("Successfully retrieved TAF data for %d forecasts", len(response))
            
            # Additional validation
            for item in response:
                if not isinstance(item, dict):
                    logger.warning("Invalid TAF item format: expected dict, got %s", type(item))
                if 'icaoId' not in item:
                    logger.warning("TAF item missing icaoId field")
                    
            return response
            
        except Exception as e:
            logger.error("Failed to fetch TAF data: %s", str(e))
            raise
    
    def get_most_recent_metars(self, all_metar_data: List[Dict]) -> Dict[str, Dict]:
        """Process METAR data to get the most recent observation for each airport
        
        Args:
            all_metar_data: List of METAR data dictionaries
            
        Returns:
            Dictionary mapping airport IDs to their most recent METAR data
        """
        airport_metars = {}
        
        if not all_metar_data:
            logger.warning("No METAR data provided to process")
            return airport_metars
            
        for metar in all_metar_data:
            station_id = metar.get("icaoId")
            
            if not station_id:
                logger.warning("Skipping METAR record with missing icaoId")
                continue
                
            # Only keep the most recent observation for each airport
            if station_id in airport_metars:
                if metar.get("mostRecent") == 1:
                    airport_metars[station_id] = metar
                    logger.debug("Updated most recent METAR for %s", station_id)
            else:
                airport_metars[station_id] = metar
                logger.debug("Added first METAR for %s", station_id)
                
        logger.info("Processed METAR data for %d airports", len(airport_metars))
        return airport_metars

    def group_tafs_by_airport(self, all_taf_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Group TAF data by airport
        
        Args:
            all_taf_data: List of TAF data dictionaries
            
        Returns:
            Dictionary mapping airport IDs to their TAF data lists
        """
        airport_tafs = {}
        
        if not all_taf_data:
            logger.warning("No TAF data provided to process")
            return airport_tafs
            
        for taf in all_taf_data:
            station_id = taf.get("icaoId")
            
            if not station_id:
                logger.warning("Skipping TAF record with missing icaoId")
                continue
                
            # Group TAFs by airport
            if station_id not in airport_tafs:
                airport_tafs[station_id] = []
                
            airport_tafs[station_id].append(taf)
            logger.debug("Added TAF for %s", station_id)
                
        logger.info("Processed TAF data for %d airports", len(airport_tafs))
        return airport_tafs
