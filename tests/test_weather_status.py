#!/usr/bin/env python3
"""
Unit tests for Weather Status module
"""

import unittest
import sys
import os
from unittest.mock import patch
import re

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from weather_status import determine_status_color, get_warning_text

class TestWeatherStatus(unittest.TestCase):
    """Tests for weather status module"""
    
    def test_determine_status_color_flight_category(self):
        """Test status color based on flight category"""
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26005KT 10SM FEW100", "VFR"),
            "GREEN"
        )
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26005KT 4SM FEW100", "MVFR"),
            "BLUE"
        )
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26005KT 2SM FEW100", "IFR"),
            "RED"
        )
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26005KT 1/2SM FEW100", "LIFR"),
            "PURPLE"
        )
        
    def test_determine_status_color_winds(self):
        """Test status color based on wind conditions"""
        # Test strong winds
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26035KT 10SM FEW100", "VFR"),
            "YELLOW"
        )
        
        # Test gusts
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26010G25KT 10SM FEW100", "VFR"),
            "YELLOW"
        )
        
        # Test thunderstorms
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26010KT 10SM TSRA FEW100", "VFR"),
            "YELLOW"
        )
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26010KT 10SM TS FEW100", "VFR"),
            "YELLOW"
        )
    
    def test_determine_status_color_crosswind(self):
        """Test status color based on crosswind threshold"""
        # Test crosswind exceeding threshold
        wind_data = {
            "crosswind": 15.0,
            "active_runway": {"name": "16L", "direction": 160}
        }
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26010KT 10SM FEW100", "VFR", wind_data),
            "YELLOW"
        )
        
        # Test crosswind below threshold
        wind_data = {
            "crosswind": 5.0,
            "active_runway": {"name": "16L", "direction": 160}
        }
        self.assertEqual(
            determine_status_color("KSEA 010000Z 26010KT 10SM FEW100", "VFR", wind_data),
            "GREEN"
        )
    
    def test_get_warning_text(self):
        """Test warning text generation"""
        # Test gusts
        warning_text = get_warning_text(
            "YELLOW", 
            "KSEA 010000Z 26010G25KT 10SM FEW100"
        )
        self.assertEqual(warning_text, " - Gusts 25KT")
        
        # Test strong winds
        warning_text = get_warning_text(
            "YELLOW", 
            "KSEA 010000Z 26035KT 10SM FEW100"
        )
        self.assertEqual(warning_text, " - Winds 35KT")
        
        # Test thunderstorms
        warning_text = get_warning_text(
            "YELLOW", 
            "KSEA 010000Z 26010KT 10SM TSRA FEW100"
        )
        self.assertEqual(warning_text, " - Thunderstorm")
        
        warning_text = get_warning_text(
            "YELLOW", 
            "KSEA 010000Z 26010KT 10SM TS FEW100"
        )
        self.assertEqual(warning_text, " - Thunderstorm")
        
        # Test crosswind
        wind_data = {
            "crosswind": 15.0,
            "active_runway": {"name": "16L", "direction": 160},
            "direction": 260
        }
        warning_text = get_warning_text(
            "YELLOW", 
            "KSEA 010000Z 26010KT 10SM FEW100",
            "KSEA",
            wind_data
        )
        self.assertEqual(warning_text, " - Crosswind 15.0KT from 260° on RWY 16L")
        
        # Test no warning for non-yellow status
        warning_text = get_warning_text(
            "GREEN", 
            "KSEA 010000Z 26010G25KT 10SM FEW100"
        )
        self.assertEqual(warning_text, "")


if __name__ == "__main__":
    unittest.main()
