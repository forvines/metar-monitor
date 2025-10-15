#!/usr/bin/env python3
"""
Unit tests for Light Sensor module
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestLightSensor(unittest.TestCase):
    """Tests for LightSensor class"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock smbus2 to avoid hardware dependency
        self.mock_smbus = MagicMock()
        self.patcher = patch.dict('sys.modules', {'smbus2': self.mock_smbus})
        self.patcher.start()
        
        # Now import after mocking
        from light_sensor import LightSensor
        self.LightSensor = LightSensor
    
    def tearDown(self):
        """Clean up test environment"""
        self.patcher.stop()
    
    def test_init_with_i2c_available(self):
        """Test initialization when I2C is available"""
        mock_bus = MagicMock()
        self.mock_smbus.SMBus.return_value = mock_bus
        
        sensor = self.LightSensor()
        
        self.assertTrue(sensor.available)
        self.assertEqual(sensor.address, 0x23)
        self.mock_smbus.SMBus.assert_called_once_with(1)
    
    def test_init_with_i2c_unavailable(self):
        """Test initialization when I2C is unavailable"""
        self.mock_smbus.SMBus.side_effect = Exception("I2C not available")
        
        sensor = self.LightSensor()
        
        self.assertFalse(sensor.available)
        self.assertIsNone(sensor.bus)
    
    def test_read_light_level_success(self):
        """Test successful light level reading"""
        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.return_value = [0x04, 0xB0]  # 1200 raw value
        self.mock_smbus.SMBus.return_value = mock_bus
        
        sensor = self.LightSensor()
        lux = sensor.read_light_level()
        
        self.assertAlmostEqual(lux, 1000.0, places=1)  # 1200 / 1.2 = 1000
    
    def test_read_light_level_unavailable(self):
        """Test light level reading when sensor unavailable"""
        sensor = self.LightSensor()
        sensor.available = False
        
        lux = sensor.read_light_level()
        
        self.assertIsNone(lux)
    
    def test_read_light_level_error(self):
        """Test light level reading with I2C error"""
        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.side_effect = Exception("I2C error")
        self.mock_smbus.SMBus.return_value = mock_bus
        
        sensor = self.LightSensor()
        lux = sensor.read_light_level()
        
        self.assertIsNone(lux)
    
    def test_calculate_brightness_dark(self):
        """Test brightness calculation in dark conditions"""
        sensor = self.LightSensor()
        
        brightness = sensor.calculate_brightness(5.0, 10, 100)  # Very dark
        
        self.assertEqual(brightness, 10)  # Should be minimum
    
    def test_calculate_brightness_bright(self):
        """Test brightness calculation in bright conditions"""
        sensor = self.LightSensor()
        
        brightness = sensor.calculate_brightness(2000.0, 10, 100)  # Very bright
        
        self.assertEqual(brightness, 100)  # Should be maximum
    
    def test_calculate_brightness_medium(self):
        """Test brightness calculation in medium conditions"""
        sensor = self.LightSensor()
        
        brightness = sensor.calculate_brightness(500.0, 10, 100)  # Medium light
        
        self.assertGreater(brightness, 10)
        self.assertLess(brightness, 100)
        self.assertAlmostEqual(brightness, 54, delta=5)  # Approximately middle
    
    def test_calculate_brightness_none_input(self):
        """Test brightness calculation with None input"""
        sensor = self.LightSensor()
        
        brightness = sensor.calculate_brightness(None, 10, 100)
        
        self.assertEqual(brightness, 100)  # Should default to max
    
    def test_get_auto_brightness(self):
        """Test automatic brightness calculation"""
        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.return_value = [0x01, 0x2C]  # 300 raw value
        self.mock_smbus.SMBus.return_value = mock_bus
        
        sensor = self.LightSensor()
        brightness = sensor.get_auto_brightness(20, 80)
        
        self.assertGreaterEqual(brightness, 20)
        self.assertLessEqual(brightness, 80)


class TestLightSensorIntegration(unittest.TestCase):
    """Integration tests for light sensor with LED controller"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock all hardware dependencies
        self.mock_smbus = MagicMock()
        self.mock_rpi_ws281x = MagicMock()
        
        self.patchers = [
            patch.dict('sys.modules', {'smbus2': self.mock_smbus}),
            patch.dict('sys.modules', {'rpi_ws281x': self.mock_rpi_ws281x})
        ]
        
        for patcher in self.patchers:
            patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        for patcher in self.patchers:
            patcher.stop()
    
    def test_led_controller_with_light_sensor(self):
        """Test LED controller integration with light sensor"""
        from light_sensor import LightSensor
        from metar_monitor import LEDController
        
        # Mock successful sensor initialization
        mock_bus = MagicMock()
        self.mock_smbus.SMBus.return_value = mock_bus
        
        # Mock LED strip
        mock_strip = MagicMock()
        self.mock_rpi_ws281x.PixelStrip.return_value = mock_strip
        
        config = {
            "led_count": 10,
            "led_pin": 18,
            "led_freq_hz": 800000,
            "led_dma": 10,
            "led_invert": False,
            "led_brightness": 50,
            "led_channel": 0,
            "light_sensor_update_interval": 1,
            "min_brightness": 20,
            "max_brightness": 80
        }
        
        light_sensor = LightSensor()
        led_controller = LEDController(config, light_sensor)
        
        self.assertTrue(led_controller.initialized)
        self.assertEqual(led_controller.light_sensor, light_sensor)
    
    def test_brightness_update_timing(self):
        """Test that brightness updates respect timing intervals"""
        from light_sensor import LightSensor
        from metar_monitor import LEDController
        import time
        
        # Mock successful sensor initialization
        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.return_value = [0x02, 0x58]  # 600 raw value
        self.mock_smbus.SMBus.return_value = mock_bus
        
        # Mock LED strip
        mock_strip = MagicMock()
        self.mock_rpi_ws281x.PixelStrip.return_value = mock_strip
        
        config = {
            "led_count": 10,
            "led_pin": 18,
            "led_freq_hz": 800000,
            "led_dma": 10,
            "led_invert": False,
            "led_brightness": 50,
            "led_channel": 0,
            "light_sensor_update_interval": 60,  # Long interval
            "min_brightness": 20,
            "max_brightness": 80
        }
        
        light_sensor = LightSensor()
        led_controller = LEDController(config, light_sensor)
        
        # First update should work
        led_controller.update_brightness()
        first_call_count = mock_strip.setBrightness.call_count
        
        # Immediate second update should be skipped
        led_controller.update_brightness()
        second_call_count = mock_strip.setBrightness.call_count
        
        self.assertEqual(first_call_count, second_call_count)


if __name__ == "__main__":
    unittest.main()