# METAR Monitor for Raspberry Pi

This application monitors METAR (Meteorological Aerodrome Reports) for specified airports and displays weather conditions via terminal and optional LED indicators.

## Features

- **Color-coded status display** for flight conditions:
  - Green: VFR (Visual Flight Rules)
  - Blue: MVFR (Marginal Visual Flight Rules)
  - Red: IFR (Instrument Flight Rules)
  - Purple: LIFR (Low Instrument Flight Rules)
  - Yellow: Strong winds (>30kts), gusts (>20kts), thunderstorms, or crosswinds (>10kts)

- **LED support** for Raspberry Pi with WS2811 LED strips
- **Forecast data** based on TAF (Terminal Aerodrome Forecast)
- **Multiple forecast periods** (4h, 8h, 12h, 18h, 24h)
- **Display mode toggle button** to cycle through current conditions and forecasts
- **Robust API client** with retry logic, error handling, and comprehensive logging
- **Crosswind calculation** for airports with runway information
- **Configurable LED legend** for easy status interpretation
- **Structured logging system** with log rotation and 7-day retention

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

**Light Sensor Configuration:**
- `light_sensor_update_interval`: How often to check light level (seconds)
- `min_brightness`: Minimum LED brightness percentage (1-100)
- `max_brightness`: Maximum LED brightness percentage (1-100)

```json
{
  "crosswind_threshold": 10,
  "legend": [
    {"name": "VFR - Visual Flight Rules", "color": "GREEN", "led": 0},
    {"name": "MVFR - Marginal Visual Flight Rules", "color": "BLUE", "led": 1},
    {"name": "IFR - Instrument Flight Rules", "color": "RED", "led": 2},
    {"name": "LIFR - Low Instrument Flight Rules", "color": "PURPLE", "led": 3},
    {"name": "Weather Warning (Wind/Storm/Crosswind)", "color": "YELLOW", "led": 4}
  ],
  "airports": [
    {"icao": "KSEA", "name": "Seattle-Tacoma Intl", "led": 17, "runways": [
      {"name": "16L/34R", "direction": 160},
      {"name": "16C/34C", "direction": 160},
      {"name": "16R/34L", "direction": 160}
    ]},
    {"icao": "KBFI", "name": "Boeing Field", "led": 18, "runways": [
      {"name": "14R/32L", "direction": 140},
      {"name": "14L/32R", "direction": 140}
    ]}
  ],
  "update_interval": 600,
  "metar_url": "https://aviationweather.gov/api/data/metar",
  "taf_url": "https://aviationweather.gov/api/data/taf",
  "forecast_hours": [4, 8, 12, 18, 24],
  "led_pin": 18,
  "led_count": 56,
  "led_brightness": 50,
  "led_freq_hz": 800000,
  "led_dma": 10,
  "led_invert": false,
  "led_channel": 0,
  "mode_indicator_led": 55
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

6. The mode indicator LED (LED 55 by default, configurable as `mode_indicator_led` in config.json) will display the current mode:
   - White: METAR mode (current conditions)
   - Cyan: TAF mode with forecast ≤ 8 hours ahead
   - Orange: TAF mode with forecast ≤ 12 hours ahead
   - Pink: TAF mode with forecast > 12 hours ahead

7. When the system is running, press the button to cycle through the modes:
   - First press changes from METAR to TAF mode showing the first forecast period (4 hours)
   - Additional presses cycle through available forecast periods (8h, 12h, 18h, 24h)
   - After cycling through all forecast periods, returns to METAR mode

## Keyboard Mode Switching

If no button is configured or available, you can use keyboard input to switch display modes:

- Press 'm' key to toggle between METAR, TAF, Airports Visited, and Test display modes
- Each mode switch displays an LED status summary showing:
  - LED index and color indicator (■)
  - Airport ICAO code and current status
  - Airport name
  - All configured airports are shown, including those with LEDs off

### Display Modes

- **METAR Mode**: Shows current weather conditions
- **TAF Mode**: Shows forecast data for configured time periods (4h, 8h, 12h, 18h, 24h)
- **Airports Visited Mode**: Shows green for visited airports, red for unvisited (based on `visited_airports` config)
- **Test Mode**: Shows green for airports with valid METAR data, red for those without

## LED Status Display

The application provides a comprehensive LED status summary that shows:

- **LED Index**: The physical LED position on the strip
- **Color Indicator**: Visual representation (■) with the actual LED color
- **Airport Code**: ICAO identifier (e.g., KSEA, KBFI)
- **Status**: Current flight category or mode-specific status
- **Airport Name**: Full airport name for reference

The LED summary is displayed:
- After each data update
- When switching display modes via keyboard ('m' key)
- Shows all configured airports, even those with LEDs currently off

## Wiring

See [WIRING_GUIDE.md](WIRING_GUIDE.md) for detailed wiring diagrams, GPIO pin assignments, power requirements, and safety notes for the LED strip, button, and light sensor.

## Diagnostic and Debug Tools

The project includes several scripts for testing and debugging hardware. All LED/GPIO scripts must be run with `sudo` on the Raspberry Pi.

### LED Strip Test (`led_test.py`)

Full hardware test for the WS2811 LED strip:

```bash
sudo python3 led_test.py
```

Runs three tests in sequence:
1. **White power test** — All LEDs white for 3 seconds (verifies power supply)
2. **Red chase** — Single red dot traverses the strip (verifies data line integrity)
3. **Color cycle** — Cycles through green, blue, yellow, purple, cyan (verifies color output)

If the white test is dim or flickering, you likely have a power supply issue. If the chase skips LEDs, check data wiring or look for a dead LED chip in the chain.

### Airport LED Walk Test (`walk_airpots_test.py`)

Lights each airport's configured LED one at a time, printing the ICAO code and LED index:

```bash
sudo python3 walk_airpots_test.py
```

Use this to verify that each airport in `metar_config.json` maps to the correct physical LED on your map. At the end, all mapped airport LEDs light up together.

### LED Map Validator (`validate_led_map.py`)

Config-only validation — no hardware or sudo required:

```bash
python3 validate_led_map.py
```

Checks for:
- Duplicate LED index assignments
- Unmapped LED indices
- Status of known problem indices

Update the `LED_COUNT` variable in the script to match your strip length.

### I2C / Light Sensor Diagnostic (`diagnose_i2c.py`)

Comprehensive diagnostic for the BH1750 light sensor and I2C bus:

```bash
sudo python3 diagnose_i2c.py
```

Checks:
- I2C kernel modules loaded
- I2C enabled in `/boot/config.txt`
- I2C bus scan for devices
- Python library availability (`smbus2`, `RPi.GPIO`)
- Direct sensor communication at addresses `0x23` and `0x5C`

### Light Sensor Test (`test_light_sensor.py`)

Quick test for light sensor readings:

```bash
sudo python3 test_light_sensor.py
```

### Quick GPIO Button Check

Test the button wiring without running the full application:

```bash
sudo python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(17, GPIO.IN, GPIO.PUD_UP); print('HIGH (not pressed)' if GPIO.input(17) else 'LOW (pressed)'); GPIO.cleanup()"
```

Should read HIGH when not pressed, LOW when pressed. If it's always LOW, the button is stuck or miswired.

## Auto-Update from Git

The included `update.sh` script lets the Pi automatically pull changes and restart the service.

### Setup

1. Make the script executable:

```bash
chmod +x ~/metar_monitor/update.sh
```

2. Allow passwordless service restart. Run `sudo visudo` and add:

```
pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart metar-monitor.service
```

3. Add a cron job to check every 5 minutes:

```bash
crontab -e
```

Add this line:

```
*/5 * * * * /home/pi/metar_monitor/update.sh
```

Push to `origin/main` and the Pi will pull changes and restart within 5 minutes. Check `~/metar_monitor/update.log` for update history.

## Automatic Airport Visit Tracking

The `visit_tracker.py` script automatically marks airports as visited when tracked aircraft land at them, using the free OpenSky Network API.

### How it works

- Polls OpenSky every 10 minutes for live ADS-B positions of configured aircraft
- When an aircraft is on the ground within 3nm of a configured airport, sets `visited: true` in `metar_config.json`
- Logs each visit with timestamp and aircraft to `visited_log.json`
- Once visited, always visited — the script only updates unvisited airports

### Tracked aircraft

Edit `TRACKED_AIRCRAFT` in `visit_tracker.py` to configure tail numbers, ICAO24 hex codes, and earliest visit dates:

```python
TRACKED_AIRCRAFT = {
    "N8279Z": {"icao24": "ab4e87", "since": "2024-09-01"},
    "N7331A": {"icao24": "a9d8ac", "since": "2026-01-01"},
}
```

You can look up ICAO24 hex codes at [adsbdb.com](https://api.adsbdb.com/v0/aircraft/N8279Z).

### Setup

Add a cron job to run every 10 minutes:

```bash
crontab -e
```

Add this line:

```
*/10 * * * * /usr/bin/python3 /home/pi/metar_monitor/visit_tracker.py >> /home/pi/metar_monitor/visit_tracker.log 2>&1
```

## Remote Access (SSH)

### Enable SSH on the Pi

```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

### Copy your SSH key from your development machine

```bash
ssh-copy-id pi@raspberrypi.local
```

If `raspberrypi.local` doesn't resolve, use the Pi's IP address (run `hostname -I` on the Pi to find it).

### Test the connection

```bash
ssh pi@raspberrypi.local
```

### Lock down to key-only authentication

Once key auth is working, disable password login on the Pi:

```bash
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

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
- Verify GPIO pin configuration and wiring (see [WIRING_GUIDE.md](WIRING_GUIDE.md))
- Check LED strip connections — all components must share a common ground
- Run `sudo python3 led_test.py` to isolate the issue
- If colors are wrong (red/green swapped), your strip may use GRB ordering

### Button not responding

- Run the quick GPIO button check above
- Verify GPIO 17 wiring (see [WIRING_GUIDE.md](WIRING_GUIDE.md))
- Check debounce — multiple triggers may need increased `DEBOUNCE_TIME` in `button_handler.py`

### Light sensor not detected

- Run `sudo python3 diagnose_i2c.py` for a full diagnostic
- Run `i2cdetect -y 1` to check if the sensor appears on the I2C bus
- Verify SDA/SCL wiring and that I2C is enabled (`sudo raspi-config` → Interface Options → I2C)

### API connection issues

- Check internet connection
- Verify API URLs in configuration
- Review logs for specific error messages: `cat metar_monitor.log`

### Logging

The application uses a structured logging system with the following features:
- Log rotation at midnight
- 7-day log retention
- Combined console and file logging
- Different log levels for debugging (INFO level by default)
- Logs stored in `metar_monitor.log` in the application directory

## Development

### Running tests

```bash
python -m pytest tests/test_metar_monitor.py
```

### Modifying the code

The codebase is organized as follows:

- `metar_monitor.py` - Main application
- `metar_api_client.py` - API client for data fetching
- `metar_processor.py` - METAR data parsing and processing
- `taf_processor.py` - TAF forecast data processing
- `airport_utils.py` - Utility functions for runway data and crosswind calculations
- `airport_data_manager.py` - Airport data storage and management
- `weather_status.py` - Weather status determination and flight category logic
- `led_status_calculator.py` - LED color calculation from weather status
- `metar_display.py` - Terminal display formatting and output
- `metar_modes.py` - Display mode management (METAR, TAF, Visited, Test)
- `button_handler.py` - GPIO button handling for mode toggle
- `light_sensor.py` - BH1750 I2C light sensor for auto-brightness
- `constants.py` - Constants, defaults, and configuration settings
- `metar_config.json` - Configuration file
- `metar-monitor.service` - Systemd service file
- `metar_monitor_startup.sh` - Startup script for service
- `WIRING_GUIDE.md` - Hardware wiring diagrams and pin assignments

### Logging guidelines

When modifying or extending this application:

- Use the established logging system instead of print statements
- Import the logger in your module: `logger = logging.getLogger("your_module_name")`
- Use appropriate log levels:
  - `logger.debug()` for detailed debugging information
  - `logger.info()` for general information
  - `logger.warning()` for warning conditions
  - `logger.error()` for error conditions
  - `logger.critical()` for critical errors
- Include contextual information in log messages
- For user-facing information that needs to appear in the terminal, still use the logger

## License

This project is open source and available for personal use.
