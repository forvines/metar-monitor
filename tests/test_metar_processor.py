#!/usr/bin/env python3
"""
Unit tests for METAR Processor module
"""

import unittest
import sys
import os
# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from metar_processor import determine_flight_category, determine_flight_category_from_values

class TestMetarProcessor(unittest.TestCase):
    """Tests for METAR processor module"""
    
    def test_determine_flight_category_from_values(self):
        """Test the helper method that determines flight categories from visibility and ceiling"""
        # Test LIFR conditions
        self.assertEqual(
            determine_flight_category_from_values(0.5, 400),
            "LIFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(0.5, 1000),
            "LIFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(3.0, 300),
            "LIFR"
        )
        
        # Test IFR conditions
        self.assertEqual(
            determine_flight_category_from_values(2.0, 800),
            "IFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(1.5, 1200),
            "IFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(5.0, 600),
            "IFR"
        )
        
        # Test MVFR conditions
        self.assertEqual(
            determine_flight_category_from_values(4.0, 2000),
            "MVFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(3.5, 3500),
            "MVFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(6.0, 2500),
            "MVFR"
        )
        
        # Test VFR conditions
        self.assertEqual(
            determine_flight_category_from_values(6.0, 3500),
            "VFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(10.0, 5000),
            "VFR"
        )
        
        # Test with missing values
        self.assertEqual(
            determine_flight_category_from_values(None, None),
            "Unknown"
        )
        self.assertEqual(
            determine_flight_category_from_values(None, 4000),
            "VFR"
        )
        self.assertEqual(
            determine_flight_category_from_values(6.0, None),
            "VFR"
        )
    
    def test_determine_flight_category(self):
        """Test the method that extracts flight category from METAR data"""
        # Test VFR conditions
        metar_vfr = {
            "visib": "10.0",
            "clouds": [
                {"cover": "FEW", "base": 5000},
                {"cover": "SCT", "base": 8000}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_vfr),
            "VFR"
        )
        
        # Test MVFR conditions with ceiling
        metar_mvfr_ceiling = {
            "visib": "6.0",
            "clouds": [
                {"cover": "BKN", "base": 2500},
                {"cover": "SCT", "base": 5000}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_mvfr_ceiling),
            "MVFR"
        )
        
        # Test MVFR conditions with visibility
        metar_mvfr_vis = {
            "visib": "4.0",
            "clouds": [
                {"cover": "FEW", "base": 5000}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_mvfr_vis),
            "MVFR"
        )
        
        # Test IFR conditions with ceiling
        metar_ifr_ceiling = {
            "visib": "5.0",
            "clouds": [
                {"cover": "OVC", "base": 800}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_ifr_ceiling),
            "IFR"
        )
        
        # Test IFR conditions with visibility
        metar_ifr_vis = {
            "visib": "2.0",
            "clouds": [
                {"cover": "SCT", "base": 5000}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_ifr_vis),
            "IFR"
        )
        
        # Test LIFR conditions with ceiling
        metar_lifr_ceiling = {
            "visib": "5.0",
            "clouds": [
                {"cover": "OVC", "base": 300}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_lifr_ceiling),
            "LIFR"
        )
        
        # Test LIFR conditions with visibility
        metar_lifr_vis = {
            "visib": "0.5",
            "clouds": [
                {"cover": "SCT", "base": 5000}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_lifr_vis),
            "LIFR"
        )
        
        # Test 10+ visibility parsing
        metar_10plus = {
            "visib": "10+",
            "clouds": [
                {"cover": "FEW", "base": 5000}
            ]
        }
        self.assertEqual(
            determine_flight_category(metar_10plus),
            "VFR"
        )
        
        # Test empty clouds
        metar_no_clouds = {
            "visib": "10.0",
            "clouds": []
        }
        self.assertEqual(
            determine_flight_category(metar_no_clouds),
            "VFR"
        )


if __name__ == "__main__":
    unittest.main()
