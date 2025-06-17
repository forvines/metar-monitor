#!/bin/bash
# Installation script for METAR Monitor

echo "METAR Monitor Installation Script"
echo "================================="

# Detect if running on a Raspberry Pi
IS_RASPBERRY_PI=false
if [ -f /proc/device-tree/model ]; then
    if grep -q "Raspberry Pi" /proc/device-tree/model; then
        IS_RASPBERRY_PI=true
        echo "Raspberry Pi detected!"
    fi
fi

# Create a Python virtual environment (optional)
echo -n "Create a Python virtual environment? (y/n): "
read create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    
    # Activate the virtual environment
    source venv/bin/activate
    echo "Virtual environment activated."
fi

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 6 ]); then
    echo "Error: Python 3.6 or higher is required. You have Python $PYTHON_VERSION"
    exit 1
fi

echo "Python $PYTHON_VERSION detected. Continuing installation..."

# Install base requirements
echo "Installing base requirements..."
pip3 install -r requirements.txt

# Install Raspberry Pi specific requirements
if [ "$IS_RASPBERRY_PI" = true ]; then
    echo "Installing Raspberry Pi specific requirements..."
    
    # Uncomment the Raspberry Pi specific lines in requirements.txt
    sed -i 's/# rpi_ws281x/rpi_ws281x/g' requirements.txt
    sed -i 's/# RPi.GPIO/RPi.GPIO/g' requirements.txt
    
    # Install the required libraries
    pip3 install rpi_ws281x RPi.GPIO
    
    echo "Note: To control LEDs and use the button, you may need to run the script with sudo:"
    echo "sudo python3 metar_monitor.py"
    
    # Check if config file already has button_pin setting
    if grep -q "button_pin" metar_config.json; then
        echo "Button pin configuration already exists in config."
    else
        echo "Adding button_pin configuration to config file..."
        # Add button_pin before led_pin if config file exists
        if [ -f metar_config.json ]; then
            # Use python to modify the JSON properly
            python3 -c "
import json
with open('metar_config.json', 'r') as f:
    config = json.load(f)
config['button_pin'] = 17
with open('metar_config.json', 'w') as f:
    json.dump(config, f, indent=4)
"
        fi
    fi
else
    echo "Not running on a Raspberry Pi. LED and button functionality will be disabled."
fi

# Make the main script executable
chmod +x metar_monitor.py

echo ""
echo "Installation complete!"
echo "To run the METAR monitor:"
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "1. Activate the virtual environment: source venv/bin/activate"
fi

if [ "$IS_RASPBERRY_PI" = true ]; then
    echo "Run with: sudo python3 metar_monitor.py"
else
    echo "Run with: python3 metar_monitor.py"
fi
