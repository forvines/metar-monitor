#!/usr/bin/env python3
"""
Light sensor module for METAR Monitor
Handles BH1750 I2C light sensor for automatic brightness adjustment
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import I2C library
I2C_AVAILABLE = False
try:
    import smbus2
    I2C_AVAILABLE = True
    logger.info("I2C library (smbus2) loaded successfully")
except ImportError:
    logger.warning("smbus2 library not found. Light sensor functionality disabled.")

# BH1750 I2C addresses and commands
BH1750_DEFAULT_ADDR = 0x23
BH1750_ALT_ADDR = 0x5C
BH1750_POWER_ON = 0x01
BH1750_RESET = 0x07
BH1750_CONTINUOUS_HIGH_RES = 0x10

class LightSensor:
    """BH1750 light sensor for automatic brightness control"""
    
    def __init__(self, i2c_bus=1, address=BH1750_DEFAULT_ADDR):
        """Initialize the light sensor
        
        Args:
            i2c_bus: I2C bus number (usually 1 on Raspberry Pi)
            address: I2C address of the BH1750 sensor
        """
        self.bus = None
        self.address = address
        self.available = False
        
        if not I2C_AVAILABLE:
            logger.warning("LightSensor initialized but I2C is not available")
            return
            
        try:
            self.bus = smbus2.SMBus(i2c_bus)
            self._initialize_sensor()
            self.available = True
            logger.info(f"Light sensor initialized on I2C address 0x{address:02x}")
        except Exception as e:
            logger.error(f"Failed to initialize light sensor: {e}")
            self.available = False
    
    def _initialize_sensor(self):
        """Initialize the BH1750 sensor"""
        if not self.bus:
            return
            
        # Power on the sensor
        self.bus.write_byte(self.address, BH1750_POWER_ON)
        time.sleep(0.01)
        
        # Reset the sensor
        self.bus.write_byte(self.address, BH1750_RESET)
        time.sleep(0.01)
        
        # Set continuous high resolution mode
        self.bus.write_byte(self.address, BH1750_CONTINUOUS_HIGH_RES)
        time.sleep(0.12)  # Wait for measurement
    
    def read_light_level(self) -> Optional[float]:
        """Read light level from sensor
        
        Returns:
            float: Light level in lux, or None if sensor unavailable
        """
        if not self.available or not self.bus:
            return None
            
        try:
            # Read 2 bytes from sensor
            data = self.bus.read_i2c_block_data(self.address, BH1750_CONTINUOUS_HIGH_RES, 2)
            
            # Convert to lux value
            light_level = (data[0] << 8) | data[1]
            lux = light_level / 1.2  # BH1750 conversion factor
            
            logger.debug(f"Light sensor reading: {lux:.1f} lux")
            return lux
            
        except Exception as e:
            logger.warning(f"Failed to read light sensor: {e}")
            return None
    
    def calculate_brightness(self, lux: Optional[float], min_brightness=10, max_brightness=100) -> int:
        """Calculate LED brightness based on light level
        
        Args:
            lux: Light level in lux
            min_brightness: Minimum brightness percentage (1-100)
            max_brightness: Maximum brightness percentage (1-100)
            
        Returns:
            int: Brightness percentage (1-100)
        """
        if lux is None:
            return max_brightness  # Default to max if no reading
            
        # Light level thresholds (lux)
        dark_threshold = 10      # Very dark (night)
        bright_threshold = 1000  # Very bright (daylight)
        
        # Calculate brightness based on light level
        if lux <= dark_threshold:
            brightness = min_brightness
        elif lux >= bright_threshold:
            brightness = max_brightness
        else:
            # Linear interpolation between thresholds
            ratio = (lux - dark_threshold) / (bright_threshold - dark_threshold)
            brightness = min_brightness + (max_brightness - min_brightness) * ratio
        
        # Ensure brightness is within bounds
        brightness = max(min_brightness, min(max_brightness, int(brightness)))
        
        logger.debug(f"Light level {lux:.1f} lux → brightness {brightness}%")
        return brightness
    
    def get_auto_brightness(self, min_brightness=10, max_brightness=100) -> int:
        """Get automatic brightness based on current light level
        
        Args:
            min_brightness: Minimum brightness percentage (1-100)
            max_brightness: Maximum brightness percentage (1-100)
            
        Returns:
            int: Brightness percentage (1-100)
        """
        lux = self.read_light_level()
        return self.calculate_brightness(lux, min_brightness, max_brightness)
    
    def close(self):
        """Close the I2C connection"""
        if self.bus:
            try:
                self.bus.close()
                logger.debug("Light sensor I2C connection closed")
            except Exception as e:
                logger.warning(f"Error closing light sensor: {e}")