# METAR Monitor for Raspberry Pi

This application monitors METAR (Meteorological Aerodrome Reports) for specified airports and displays weather conditions via terminal and optional LED indicators.

## Features

- **Color-coded status display** for flight conditions:
  - Green: VFR (Visual Flight Rules)
  - Blue: MVFR (Marginal Visual Flight Rules)
  - Red: IFR (Instrument Flight Rules)
  - Purple: LIFR (Low Instrument Flight Rules)
  - Yellow: Strong winds (>30kts), gusts (>20kts), or thunderstorms

- **LED support** for Raspberry Pi with WS2811 LED strips
- **Forecast data** based on TAF (Terminal Aerodrome Forecast)
- **Display mode toggle button** to switch between current conditions and forecast
- **Robust API client** with retry logic, error handling, and comprehensive logging

## Requirements

- Python 3.6 or higher
- Raspberry Pi (optional for LED functionality)
- Internet connection to access Aviation Weather API
- WS2811 LED strip (optional for visual display)

## Installation

### 1. Clone or download this repository

```bash
mkdir -p ~/metar_monitor
cd ~/metar_monitor
# Copy all files to this directory
```

### 2. Run the installation script

```bash
chmod +x install.sh
./install.sh
```

The installation script will:
- Check Python version requirements
- Install required dependencies
- Set up optional LED support if running on a Raspberry Pi

### 3. Configure airports and settings

Edit the `metar_config.json` file with your airport settings:

```json
{
  "airports": [
    {"icao": "KSEA", "name": "Seattle-Tacoma Intl", "led": 0},
    {"icao": "KBFI", "name": "Boeing Field", "led": 1}
  ],
  "update_interval": 900,
  "metar_url": "https://aviationweather.gov/api/data/metar",
  "taf_url": "https://aviationweather.gov/api/data/taf",
  "forecast_hours": [4, 6, 12],
  "led_pin": 18,
  "led_count": 50,
  "led_brightness": 50
}
```

## Running the Application

### Manual Execution

```bash
python3 metar_monitor.py
```

For LED support on a Raspberry Pi, you'll need to run with sudo:

```bash
sudo python3 metar_monitor.py
```

### Setup as a Service on Raspberry Pi

1. Ensure the startup script is executable:

```bash
chmod +x metar_monitor_startup.sh
```

2. Copy the service file to the systemd directory:

```bash
sudo cp metar-monitor.service /etc/systemd/system/
```

3. Reload systemd to recognize the new service:

```bash
sudo systemctl daemon-reload
```

4. Enable the service to start on boot:

```bash
sudo systemctl enable metar-monitor.service
```

5. Start the service:

```bash
sudo systemctl start metar-monitor.service
```

6. Check service status:

```bash
sudo systemctl status metar-monitor.service
```

## LED and Button Setup

For LED functionality on a Raspberry Pi:

1. Connect your WS2811 LED strip to the Raspberry Pi:
   - Data pin to GPIO 18 (default, configurable in config.json)
   - Power and ground appropriately

2. Connect a momentary push button for mode switching:
   - One terminal to GPIO 17 (default, configurable in config.json as `button_pin`)
   - Other terminal to GND
   - The button uses the internal pull-up resistor, so no external resistor is needed

3. Install required libraries if not already installed:

```bash
sudo pip3 install rpi_ws281x RPi.GPIO
```

4. Ensure the `led_count` in your configuration matches the number of LEDs in your strip

5. Map airports to specific LED indices in the configuration file

6. The last LED in the strip (LED 49 by default, configurable as `mode_indicator_led` in config.json) will display the current mode:
   - White: METAR mode (current conditions)
   - Cyan: TAF mode with forecast ≤ 6 hours ahead
   - Orange: TAF mode with forecast ≤ 12 hours ahead
   - Pink: TAF mode with forecast > 12 hours ahead

7. When the system is running, press the button to cycle through the modes:
   - First press changes from METAR to TAF mode showing the first forecast period (e.g., 4 hours)
   - Additional presses cycle through available forecast periods (e.g., 6h, 12h, 18h, 24h)
   - After cycling through all forecast periods, returns to METAR mode

## Troubleshooting

### Service won't start

Check logs:
```bash
sudo journalctl -u metar-monitor.service -f
```

Common issues:
- Incorrect paths in the service file
- Python version issues
- Missing dependencies
- Permission problems

### LEDs not working

- Check if running with sudo
- Verify GPIO pin configuration
- Check LED strip connections
- Test LED strip with a simple test script

### API connection issues

- Check internet connection
- Verify API URLs in configuration
- Review logs for specific error messages: `cat metar_monitor.log`

## Development

### Running tests

```bash
python -m pytest test_metar_monitor.py
```

### Modifying the code

The codebase is organized as follows:

- `metar_monitor.py` - Main application
- `metar_api_client.py` - API client for data fetching
- `metar_config.json` - Configuration file
- `test_metar_monitor.py` - Unit tests
- `metar-monitor.service` - Systemd service file
- `metar_monitor_startup.sh` - Startup script for service

## License

This project is open source and available for personal use.
