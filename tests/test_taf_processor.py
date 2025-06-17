#!/usr/bin/env python3
"""
Unit tests for TAF Processor module
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import taf_processor

class TestTAFProcessor(unittest.TestCase):
    """Tests for TAF processor module"""
    
    def test_get_most_recent_taf(self):
        """Test getting the most recent TAF"""
        # Test with mostRecent flag
        taf_list = [
            {"icaoId": "KSEA", "rawTAF": "TAF1", "mostRecent": 0},
            {"icaoId": "KSEA", "rawTAF": "TAF2", "mostRecent": 1},
            {"icaoId": "KSEA", "rawTAF": "TAF3", "mostRecent": 0}
        ]
        most_recent = taf_processor.get_most_recent_taf(taf_list)
        self.assertEqual(most_recent["rawTAF"], "TAF2")
        
        # Test without mostRecent flag
        taf_list = [
            {"icaoId": "KSEA", "rawTAF": "TAF1"},
            {"icaoId": "KSEA", "rawTAF": "TAF2"},
            {"icaoId": "KSEA", "rawTAF": "TAF3"}
        ]
        most_recent = taf_processor.get_most_recent_taf(taf_list)
        self.assertEqual(most_recent["rawTAF"], "TAF1")  # Should return first entry
        
        # Test empty list
        self.assertIsNone(taf_processor.get_most_recent_taf([]))
    
    @patch('taf_processor.datetime')
    def test_find_relevant_forecast_period(self, mock_datetime):
        """Test finding the relevant forecast period"""
        # Mock the current time
        mock_now = datetime(2023, 6, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda x: datetime.fromtimestamp(x)
        
        # Create test target time
        target_time = mock_now + timedelta(hours=6)
        
        # Test with matching period
        forecast_periods = [
            {
                "timeFrom": int((mock_now - timedelta(hours=1)).timestamp()),
                "timeTo": int((mock_now + timedelta(hours=3)).timestamp())
            },
            {
                "timeFrom": int((mock_now + timedelta(hours=3)).timestamp()),
                "timeTo": int((mock_now + timedelta(hours=9)).timestamp())
            },
            {
                "timeFrom": int((mock_now + timedelta(hours=9)).timestamp()),
                "timeTo": int((mock_now + timedelta(hours=12)).timestamp())
            }
        ]
        
        period, from_time = taf_processor.find_relevant_forecast_period(forecast_periods, target_time)
        self.assertEqual(period, forecast_periods[1])
        
        # Test with no matching period
        target_time = mock_now + timedelta(hours=24)
        period, from_time = taf_processor.find_relevant_forecast_period(forecast_periods, target_time)
        self.assertIsNone(period)
        self.assertIsNone(from_time)
        
        # Test with missing or invalid times
        forecast_periods = [
            {"timeFrom": None, "timeTo": None}
        ]
        period, from_time = taf_processor.find_relevant_forecast_period(forecast_periods, target_time)
        self.assertIsNone(period)
        self.assertIsNone(from_time)

    def test_format_clouds_info(self):
        """Test formatting cloud information"""
        # Test normal case
        clouds = [
            {"cover": "BKN", "base": 3000},
            {"cover": "OVC", "base": 5000}
        ]
        self.assertEqual(
            taf_processor.format_clouds_info(clouds),
            "BKN3000 OVC5000"
        )
        
        # Test empty list
        self.assertEqual(taf_processor.format_clouds_info([]), "")
        
        # Test missing values
        clouds = [
            {"cover": "BKN"},
            {"base": 5000}
        ]
        self.assertEqual(taf_processor.format_clouds_info(clouds), "")
        
        # Test None input
        self.assertEqual(taf_processor.format_clouds_info(None), "")

    def test_format_wind(self):
        """Test wind formatting"""
        # Test normal case
        self.assertEqual(taf_processor.format_wind(270, 15), "27015")
        
        # Test padding
        self.assertEqual(taf_processor.format_wind(90, 5), "09005")
        
        # Test None values
        self.assertEqual(taf_processor.format_wind(None, None), "------")
        self.assertEqual(taf_processor.format_wind(None, 10), "---10")
        self.assertEqual(taf_processor.format_wind(270, None), "270--")
        
        # Test string values
        self.assertEqual(taf_processor.format_wind("270", "15"), "27015")
        
        # Test non-numeric strings
        self.assertEqual(taf_processor.format_wind("VRB", "15"), "VRB15")
        
        # Test conversion errors
        self.assertEqual(taf_processor.format_wind("xxx", "yyy"), "xxxyyy")

if __name__ == "__main__":
    unittest.main()
