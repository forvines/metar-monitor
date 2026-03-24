#!/usr/bin/env python3
"""
Button handler for METAR Monitor
Provides GPIO button interface for Raspberry Pi to toggle display modes
"""

import time
import threading
import logging

# Configure logger
logger = logging.getLogger("button_handler")

# Try to import RPi.GPIO, but continue if not available
GPIO_AVAILABLE = False
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    logger.info("RPi.GPIO library loaded successfully")
except ImportError:
    logger.warning("RPi.GPIO library not found. Button functionality disabled.")
    
# Constants
DEFAULT_BUTTON_PIN = 17  # GPIO pin for the button (BCM numbering)
DEBOUNCE_TIME = 0.5      # Debounce time in seconds

class ButtonHandler:
    """Handler for GPIO button to toggle display modes"""
    
    def __init__(self, button_pin=DEFAULT_BUTTON_PIN, callback=None):
        """Initialize the button handler
        
        Args:
            button_pin: GPIO pin number for the button (BCM numbering)
            callback: Function to call when button is pressed
        """
        self.button_pin = button_pin
        self.callback = callback
        self.is_running = False
        self.thread = None
        
        # Early exit if GPIO is not available
        if not GPIO_AVAILABLE:
            logger.warning("ButtonHandler initialized but GPIO is not available")
            return
            
        try:
            # Set up GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info(f"Button configured on GPIO pin {self.button_pin} with pull-up resistor")
            # Test initial GPIO state
            initial_state = GPIO.input(self.button_pin)
            logger.info(f"Initial button state: {'HIGH' if initial_state else 'LOW'}")
        except Exception as e:
            logger.error(f"Error setting up GPIO: {str(e)}")
            return
    
    def start(self):
        """Start the button monitoring thread"""
        if not GPIO_AVAILABLE:
            logger.warning("Button monitoring not started: GPIO not available")
            return False
            
        if self.is_running:
            logger.warning("Button monitoring already running")
            return False
            
        try:
            self.is_running = True
            self.thread = threading.Thread(target=self._monitor_button, daemon=True)
            self.thread.start()
            logger.info("Button monitoring thread started")
            return True
        except Exception as e:
            logger.error(f"Error starting button monitoring: {str(e)}")
            self.is_running = False
            return False
    
    def stop(self):
        """Stop the button monitoring thread"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        
        # Clean up GPIO if we're stopping
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup(self.button_pin)
            except Exception as e:
                logger.error(f"Error cleaning up GPIO: {str(e)}")
                
        logger.info("Button monitoring stopped")
    
    def _monitor_button(self):
        """Monitor the button for presses using edge detection"""
        logger.info(f"Button monitoring started on GPIO pin {self.button_pin}")
        
        try:
            while self.is_running:
                # Wait for falling edge (button press) with timeout so we can check is_running
                channel = GPIO.wait_for_edge(self.button_pin, GPIO.FALLING, timeout=500)
                if channel is None:
                    continue  # Timeout, loop back to check is_running
                
                # Debounce: wait for signal to stabilize then confirm still LOW
                time.sleep(0.05)
                if GPIO.input(self.button_pin) != GPIO.LOW:
                    continue  # Was just noise
                
                logger.info("Button pressed - executing callback")
                if self.callback:
                    try:
                        self.callback()
                    except Exception as e:
                        logger.error(f"Error in button callback: {str(e)}")
                
                # Wait for full release before accepting another press
                while GPIO.input(self.button_pin) == GPIO.LOW and self.is_running:
                    time.sleep(0.05)
                
                # Post-release cooldown to ignore bounce
                time.sleep(DEBOUNCE_TIME)
                
        except Exception as e:
            logger.exception(f"Error in button monitoring thread: {str(e)}")
            self.is_running = False

# Function to simulate button press (useful for testing without actual hardware)
def simulate_button_press(handler):
    """Simulate a button press by directly calling the handler's callback"""
    if handler.callback:
        handler.callback()
        return True
    return False
