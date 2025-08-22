#!/usr/bin/env python3
"""
Unit tests for METAR Status Monitor
"""

import unittest
import json
import sys
import os
import re
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import metar_monitor
from metar_monitor import METARStatus, LEDController
import constants


class TestFlightCategoryDetermination(unittest.TestCase):
    """Tests for flight category determination methods"""
    
    def setUp(self):
        """Set up test environment"""
        mock_config = {
            "airports": [
                {"icao": "KSEA", "name": "Seattle-Tacoma Intl", "led": 0},
                {"icao": "KBFI", "name": "Boeing Field", "led": 1}
            ],
            "led_count": 10,
            "forecast_hours": [6, 12, 24],
            "metar_url": "https://aviationweather.gov/api/data/metar",
            "taf_url": "https://aviationweather.gov/api/data/taf"
        }
        
        # Mock the logger and API client
        with patch('logging.getLogger') as mock_logger:
            with patch('metar_monitor.METARAPIClient') as mock_api_client:
                self.metar_status = METARStatus(mock_config)
                # Replace the real API client with a mock
                self.metar_status.api_client = mock_api_client.return_value


class TestStatusColorDetermination(unittest.TestCase):
    """Tests for status color determination"""
    
    def setUp(self):
        """Set up test environment"""
        mock_config = {
            "airports": [
                {"icao": "KSEA", "name": "Seattle-Tacoma Intl", "led": 0},
                {"icao": "KBFI", "name": "Boeing Field", "led": 1}
            ],
            "led_count": 10,
            "metar_url": "https://aviationweather.gov/api/data/metar",
            "taf_url": "https://aviationweather.gov/api/data/taf"
        }
        
        # Mock the logger and API client
        with patch('logging.getLogger') as mock_logger:
            with patch('metar_monitor.METARAPIClient') as mock_api_client:
                self.metar_status = METARStatus(mock_config)
                # Replace the real API client with a mock
                self.metar_status.api_client = mock_api_client.return_value
    
    def test_determine_status_color_flight_category(self):
        """Test status color based on flight category"""
        self.assertEqual(
            self.metar_status.determine_status_color("KSEA 010000Z 26005KT 10SM FEW100", "VFR"),
            "GREEN"
        )
        self.assertEqual(
            self.metar_status.determine_status_color("KSEA 010000Z 26005KT 4SM FEW100", "MVFR"),
            "BLUE"
        )
        self.assertEqual(
            self.metar_status.determine_status_color("KSEA 010000Z 26005KT 2SM FEW100", "IFR"),
            "RED"
        )
        self.assertEqual(
            self.metar_status.determine_status_color("KSEA 010000Z 26005KT 1/2SM FEW100", "LIFR"),
            "PURPLE"
        )


class TestHelperMethods(unittest.TestCase):
    """Tests for helper methods"""
    
    def setUp(self):
        """Set up test environment"""
        mock_config = {
            "airports": [
                {"icao": "KSEA", "name": "Seattle-Tacoma Intl", "led": 0},
                {"icao": "KBFI", "name": "Boeing Field", "led": 1}
            ],
            "led_count": 10,
            "metar_url": "https://aviationweather.gov/api/data/metar",
            "taf_url": "https://aviationweather.gov/api/data/taf"
        }
        
        # Mock the logger and API client
        with patch('logging.getLogger') as mock_logger:
            with patch('metar_monitor.METARAPIClient') as mock_api_client:
                self.metar_status = METARStatus(mock_config)
                # Replace the real API client with a mock
                self.metar_status.api_client = mock_api_client.return_value


class TestTAFProcessing(unittest.TestCase):
    """Tests for TAF processing"""
    
    def setUp(self):
        """Set up test environment"""
        mock_config = {
            "airports": [
                {"icao": "KSEA", "name": "Seattle-Tacoma Intl", "led": 0},
            ],
            "led_count": 10,
            "forecast_hours": [6, 12],
            "metar_url": "https://aviationweather.gov/api/data/metar",
            "taf_url": "https://aviationweather.gov/api/data/taf"
        }
        
        # Mock the logger and API client
        with patch('logging.getLogger') as mock_logger:
            with patch('metar_monitor.METARAPIClient') as mock_api_client:
                self.metar_status = METARStatus(mock_config)
                # Replace the real API client with a mock
                self.metar_status.api_client = mock_api_client.return_value
                
        # Initialize airport data
        self.metar_status.airport_data = {
            "KSEA": {
                "raw_metar": "KSEA 010000Z 26005KT 10SM FEW100",
                "flight_category": "VFR",
                "status_color": "GREEN",
                "name": "Seattle-Tacoma Intl"
            }
        }
    
    def test_get_most_recent_taf(self):
        """Test getting the most recent TAF"""
        # Test with mostRecent flag
        taf_list = [
            {"icaoId": "KSEA", "rawTAF": "TAF1", "mostRecent": 0},
            {"icaoId": "KSEA", "rawTAF": "TAF2", "mostRecent": 1},
            {"icaoId": "KSEA", "rawTAF": "TAF3", "mostRecent": 0}
        ]
        most_recent = self.metar_status._get_most_recent_taf(taf_list)
        self.assertEqual(most_recent["rawTAF"], "TAF2")
        
        # Test without mostRecent flag
        taf_list = [
            {"icaoId": "KSEA", "rawTAF": "TAF1"},
            {"icaoId": "KSEA", "rawTAF": "TAF2"},
            {"icaoId": "KSEA", "rawTAF": "TAF3"}
        ]
        most_recent = self.metar_status._get_most_recent_taf(taf_list)
        self.assertEqual(most_recent["rawTAF"], "TAF1")  # Should return first entry
        
        # Test empty list
        self.assertIsNone(self.metar_status._get_most_recent_taf([]))


class TestConfigLoading(unittest.TestCase):
    """Tests for configuration loading"""
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"airports": [{"icao": "KTEST", "name": "Test Airport", "led": 0}], "led_count": 5}')
    @patch('json.load')
    def test_load_config_existing_file(self, mock_json_load, mock_file_open, mock_exists):
        """Test loading an existing config file"""
        # Set up the test
        mock_exists.return_value = True
        mock_config = {
            "airports": [{"icao": "KTEST", "name": "Test Airport", "led": 0}],
            "led_count": 5
        }
        mock_json_load.return_value = mock_config
        
        # Call the function
        config = metar_monitor.load_config()
        
        # Verify the result
        mock_exists.assert_called_once_with(metar_monitor.CONFIG_FILE)
        mock_file_open.assert_called_once_with(metar_monitor.CONFIG_FILE, 'r')
        mock_json_load.assert_called_once()
        
        # Should have exactly what's in the config file
        self.assertEqual(config["airports"], [{"icao": "KTEST", "name": "Test Airport", "led": 0}])
        self.assertEqual(config["led_count"], 5)
        self.assertEqual(config, mock_config)
    
    @patch('os.path.exists')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_load_config_nonexistent_file(self, mock_exit, mock_print, mock_exists):
        """Test that the application exits when config file doesn't exist"""
        # Set up the test
        mock_exists.return_value = False
        
        # Call the function - should exit
        metar_monitor.load_config()
        
        # Verify the result
        mock_exists.assert_called_once_with(metar_monitor.CONFIG_FILE)
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()  # Should print an error message
        
    @patch('os.path.exists')
    @patch('builtins.open', mock_open(read_data="invalid json"))
    @patch('json.load')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_load_config_invalid_json(self, mock_exit, mock_print, mock_json_load, mock_exists):
        """Test that the application exits when config file contains invalid JSON"""
        # Set up the test
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        # Call the function - should exit
        metar_monitor.load_config()
        
        # Verify the result
        mock_exists.assert_called_once_with(metar_monitor.CONFIG_FILE)
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()  # Should print an error message


if __name__ == "__main__":
    unittest.main()
