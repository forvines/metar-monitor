#!/bin/bash
# /home/pi/metar_monitor_startup.sh
# Startup script for METAR Monitor

# Directory where the METAR monitor is installed
METAR_DIR="/home/pi/metar_monitor"
# Log file location
LOG_FILE="/home/pi/metar_monitor/metar_monitor.log"

# Change to the METAR monitor directory
cd $METAR_DIR

# Check if we should run in logging mode
if [ "$1" == "--log" ]; then
    echo "Starting METAR Monitor in logging mode..."
    # Run with logging to file
    sudo python3 metar_monitor.py --log >> $LOG_FILE 2>&1
else
    echo "Starting METAR Monitor in console mode..."
    # Run in console mode
    sudo python3 metar_monitor.py
fi
