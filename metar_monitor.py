#!/usr/bin/env python3
"""
METAR Status Monitor for airports near KSEA
Displays color-coded status for flight conditions:
- Green: VFR (Visual Flight Rules)
- Blue: MVFR (Marginal Visual Flight Rules)
- Red: IFR (Instrument Flight Rules)
- Purple: LIFR (Low Instrument Flight Rules)
- Yellow: Strong winds (>30kts), gusts (>20kts), thunderstorms, or crosswind (>10kts)

This version supports WS2811 LED output on a Raspberry Pi
"""

import signal
import json
import time
import os
import sys
import logging
import math
import threading
import select
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
from airport_data_manager import AirportDataManager
from metar_display import DisplayManager
from metar_modes import ModeManager
from constants import DisplayMode
from constants import (
    COLORS, CATEGORY_COLOR_MAP, FLIGHT_CATEGORIES, 
    THRESHOLDS, DEFAULT_BUTTON_PIN,
    DEFAULT_LIGHT_SENSOR_UPDATE_INTERVAL, DEFAULT_MIN_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS,
    CONFIG_FILE, DISPLAY_FORMATTING, MODE_INDICATOR_COLOR, MODE_NAMES
)
from light_sensor import LightSensor



# Try to import the rpi_ws281x library for LED control
LED_ENABLED = False
LED_COLORS = {}
try:
    from rpi_ws281x import PixelStrip, Color
    # LED RGB color values - only define if the library is available
    LED_COLORS = {
        "GREEN": Color(255, 0, 0),    # VFR
        "BLUE": Color(0, 0, 255),     # MVFR
        "RED": Color(0, 255, 0),      # IFR
        "PURPLE": Color(0, 128, 128), # LIFR
        "YELLOW": Color(255, 255, 0), # Wind/Storm warnings
        "WHITE": Color(255, 255, 255), # Mode indicator - METAR
        "OFF": Color(0, 0, 0)         # Off
    }
    LED_ENABLED = True
    logging.info("LED support enabled")
except ImportError:
    logging.info("rpi_ws281x library not found. Running in console-only mode.")

class KeyboardHandler:
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._input_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        self.running = False
    
    def _input_loop(self):
        while self.running:
            try:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    if key.lower() == 'm':
                        self.callback()
            except:
                pass

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logging.error(f"Error loading config file: {e}")
            print(f"Error loading configuration file: {e}")
            sys.exit(1)
    else:
        logging.error(f"Configuration file '{CONFIG_FILE}' not found")
        print(f"Error: Configuration file '{CONFIG_FILE}' not found. Please create it before running.")
        sys.exit(1)

class LEDController:
    def __init__(self, config, light_sensor=None):
        self.strip = None
        self.config = config
        self.initialized = False
        self.light_sensor = light_sensor
        self.current_brightness = config["led_brightness"]
        self.last_brightness_update = 0
        
        if LED_ENABLED:
            try:
                # Create NeoPixel object with appropriate configuration
                self.strip = PixelStrip(
                    config["led_count"],
                    config["led_pin"],
                    config["led_freq_hz"],
                    config["led_dma"],
                    config["led_invert"],
                    config["led_brightness"],
                    config["led_channel"]
                )
                
                # Initialize the library (must be called once before other functions)
                self.strip.begin()
                self.initialized = True
                logging.info("LED strip initialized successfully")
                
                # Turn off all LEDs initially
                self.clear()
            except Exception as e:
                logging.error(f"Error initializing LED strip: {e}")
                self.initialized = False
    
    def update_brightness(self):
        """Update LED brightness based on light sensor"""
        if not self.light_sensor or not self.initialized:
            return
            
        current_time = time.time()
        update_interval = self.config.get("light_sensor_update_interval", DEFAULT_LIGHT_SENSOR_UPDATE_INTERVAL)
        
        # Only update brightness periodically
        if current_time - self.last_brightness_update < update_interval:
            return
            
        min_brightness = self.config.get("min_brightness", DEFAULT_MIN_BRIGHTNESS)
        max_brightness = self.config.get("max_brightness", DEFAULT_MAX_BRIGHTNESS)
        
        new_brightness = self.light_sensor.get_auto_brightness(min_brightness, max_brightness)
        
        if new_brightness != self.current_brightness:
            self.current_brightness = new_brightness
            self.strip.setBrightness(new_brightness)
            self.strip.show()
            logging.info(f"LED brightness adjusted to {new_brightness}%")
            
        self.last_brightness_update = current_time
    
    def set_led(self, index, color_name):
        """Set an LED to a specific color"""
        if not self.initialized or index >= self.config["led_count"]:
            logging.warning(f"LED index {index} out of range or LED strip not initialized.")
            return
            
        # Update brightness before setting LED
        self.update_brightness()
            
        if color_name in LED_COLORS:
            color = LED_COLORS[color_name]
            self.strip.setPixelColor(index, color)
            self.strip.show()
        else:
            logging.warning(f"Unknown color name: {color_name}. Using default OFF color.")
            self.strip.setPixelColor(index, LED_COLORS["OFF"])
            self.strip.show()
    
    def clear(self):
        """Turn off all LEDs"""
        if not self.initialized:
            return
            
        for i in range(self.config["led_count"]):
            self.strip.setPixelColor(i, LED_COLORS["OFF"])
        self.strip.show()

class METARStatus:
    """Main METAR Status class - now simplified using manager classes"""
    
    def __init__(self, config, led_controller=None):
        self.config = config
        self.logger = logging.getLogger("metar_status")
        
        # Initialize managers
        self.data_manager = AirportDataManager(config)
        self.display_manager = DisplayManager(config, led_controller)
        self.mode_manager = ModeManager(config, led_controller)
        
        # Set up legend LEDs if we have an LED controller
        if led_controller:
            self.mode_manager._set_legend_leds()
        
        self.logger.info("Initialized METAR Status with manager classes")
    
    
    def toggle_display_mode(self):
        """Toggle display mode using the mode manager"""
        mode = self.mode_manager.toggle_display_mode()
        self.mode_manager.update_led_display(self.data_manager.airport_data)
        
        # Print status message
        print("\n" + DISPLAY_FORMATTING["HEADER_LINE"])
        if self.mode_manager.display_mode == DisplayMode.METAR:
            print(f"Display mode changed to: {DisplayMode.get_name(self.mode_manager.display_mode)}")
        elif self.mode_manager.display_mode == DisplayMode.TAF:
            print(f"Display mode changed to: {DisplayMode.get_name(self.mode_manager.display_mode, self.mode_manager.current_forecast_hour)}")
        else:
            print(f"Display mode changed to: {DisplayMode.get_name(self.mode_manager.display_mode)}")
        print(DISPLAY_FORMATTING["HEADER_LINE"])
        
        return mode
    
    def update_led_display(self):
        """Update LEDs using the mode manager"""
        self.mode_manager.update_led_display(self.data_manager.airport_data)

    def print_color_legend(self):
        """Print color legend using display manager"""
        self.display_manager.print_color_legend()
    
    def print_led_mapping(self):
        """Print LED mapping using display manager"""
        self.display_manager.print_led_mapping()
    
    def print_led_summary(self):
        """Print LED summary using display manager"""
        self.display_manager.print_led_summary(
            self.data_manager.airport_data, 
            self.mode_manager.display_mode, 
            self.mode_manager.current_forecast_hour
        )
    
    def fetch_metar_data(self):
        """Fetch and process METAR data using data manager"""
        # Print legends and headers
        self.print_color_legend()
        self.print_led_mapping()
        print("\nFetching METAR data for airports...")
        print(DISPLAY_FORMATTING["HEADER_LINE"])
        
        # Fetch and process data using data manager
        success = self.data_manager.fetch_and_process_data()
        if not success:
            return False
        
        # Display results for each airport
        for station_id, airport_data in self.data_manager.airport_data.items():
            self.display_manager.display_airport_data(station_id, airport_data)
        
        # Print LED summary
        self.print_led_summary()
        
        return True
    


def main():
    # Configure logging with log rotation
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Set up file handler with rotation - 7 days of logs, rotating at midnight
    file_handler = TimedRotatingFileHandler(
        filename="metar_monitor.log",
        when="midnight",
        interval=1,
        backupCount=7,  # Keep 7 days of logs
        encoding="utf-8",
        delay=False
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.suffix = "%Y-%m-%d"  # Use YYYY-MM-DD date format in rotated log filenames
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Get application logger
    logger = logging.getLogger("metar_monitor")
    logger.info("Starting METAR Monitor with log rotation (7 days retention)")
    
    # Try to import ButtonHandler
    try:
        from button_handler import ButtonHandler
        button_available = True
        logger.info("Button handler module available")
    except ImportError:
        button_available = False
        logger.warning("Button handler module not available. Button functionality disabled.")
    
    # Load configuration
    config = load_config()
    
    logger.info("Starting METAR Monitor")
    logger.info("Monitoring %d airports: %s", 
               len(config['airports']), 
               ", ".join([airport["icao"] for airport in config['airports']]))
    logger.info("Update interval: %d seconds", config['update_interval'])
    logger.info("Forecast hours: %s", str(config['forecast_hours']))
    
    # Initialize light sensor
    light_sensor = None
    try:
        light_sensor = LightSensor()
        if light_sensor.available:
            logger.info("Light sensor initialized successfully")
        else:
            logger.info("Light sensor not available, using fixed brightness")
    except Exception as e:
        logger.warning(f"Failed to initialize light sensor: {e}")
    
    # Initialize LED controller if possible
    led_controller = None
    if LED_ENABLED:
        logger.info("LED support is enabled, initializing controller")
        led_controller = LEDController(config, light_sensor)
    else:
        logger.info("LED support is disabled, running in console-only mode")
    
    # Initialize METAR status with LED controller
    metar_status = METARStatus(config, led_controller)
    
    # Set up button handler if available
    button_handler = None
    if button_available:
        # Configure the button handler with the toggle display mode callback
        button_pin = config.get("button_pin", DEFAULT_BUTTON_PIN)
        logger.info("Setting up button handler on GPIO pin %d", button_pin)
        
        def toggle_mode_callback():
            mode = metar_status.toggle_display_mode()
            logger.info("Button pressed: Display mode toggled to %s", 
                       DisplayMode.get_name(mode))
        
        button_handler = ButtonHandler(button_pin, toggle_mode_callback)
        button_success = button_handler.start()
        
        if button_success:
            logger.info("Button handler started successfully")
            print(f"Button on GPIO {button_pin} enabled. Press button to toggle between METAR and TAF display.")
        else:
            logger.warning("Failed to start button handler")
    
    # Set up keyboard handler if button is not available
    keyboard_handler = None
    if not button_handler or not button_success:
        logger.info("Setting up keyboard handler for mode switching")
        
        def keyboard_toggle_callback():
            mode = metar_status.toggle_display_mode()
            logger.info("Key pressed: Display mode toggled to %s", 
                       DisplayMode.get_name(mode))
            # Print LED status summary when switching modes
            metar_status.print_led_summary()
        
        keyboard_handler = KeyboardHandler(keyboard_toggle_callback)
        keyboard_handler.start()
        logger.info("Keyboard handler started successfully")
        print("Press 'm' key to toggle between display modes.")
    
    try:
        # Initial data fetch
        if metar_status.fetch_metar_data():
            print("\nCompleted fetching all airport data.")
            
            # Update LED display based on initial mode
            metar_status.update_led_display()
        
        while True:
            # Wait for the configured update interval
            print(f"\nNext update in {config['update_interval'] // 60} minutes. Press Ctrl+C to exit.")
            if metar_status.mode_manager.display_mode == DisplayMode.METAR:
                print(f"Current display mode: {DisplayMode.get_name(metar_status.mode_manager.display_mode)}")
            elif metar_status.mode_manager.display_mode == DisplayMode.TAF:
                print(f"Current display mode: {DisplayMode.get_name(metar_status.mode_manager.display_mode, metar_status.mode_manager.current_forecast_hour)}")
            else:
                print(f"Current display mode: {DisplayMode.get_name(metar_status.mode_manager.display_mode)}")
            
            if button_handler and button_success:
                print("Press button to toggle between METAR, TAF, Airports Visited, and Test display modes.")
            elif keyboard_handler:
                print("Press 'm' key to toggle between METAR, TAF, Airports Visited, and Test display modes.")
                
            time.sleep(config['update_interval'])
            
            # Fetch updated data
            if metar_status.fetch_metar_data():
                print("\nCompleted updating airport data.")
                
                # Update LED display based on current mode
                metar_status.update_led_display()
    
    #except KeyboardInterrupt:
    finally:
        logger.info("KeyboardInterrupt received, shutting down")
        # Clean up resources
        if button_handler:
            button_handler.stop()
            logger.info("Button handler stopped")
            
        if keyboard_handler:
            keyboard_handler.stop()
            logger.info("Keyboard handler stopped")
            
        if led_controller:
            led_controller.clear()
            logger.info("LED controller cleared")
            
        if light_sensor:
            light_sensor.close()
            logger.info("Light sensor closed")
            
        logger.info("METAR Monitor shut down cleanly")

if __name__ == "__main__":
    main()
