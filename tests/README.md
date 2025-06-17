# METAR Monitor Tests

This directory contains all the unit tests for the METAR Monitor project. The tests are organized to mirror the module structure of the main project.

## Test Files

- `test_metar_processor.py`: Tests for the METAR data processing functions
- `test_taf_processor.py`: Tests for the TAF (forecast) data processing functions
- `test_weather_status.py`: Tests for the status color determination and warning text generation
- `test_metar_monitor.py`: Tests for the main application functionality

## Running Tests

From the project root directory, you can run all tests using:

```bash
python -m unittest discover -s metar_monitor/tests
```

Or run a specific test file with:

```bash
python -m unittest metar_monitor.tests.test_metar_processor
```

## Test Structure

The tests are designed to verify the behavior of the refactored modules:

1. METAR processing tests verify flight category determination from raw weather data
2. TAF processing tests verify forecast period handling and forecast category determination
3. Weather status tests verify status color determination based on weather conditions
4. Main application tests verify config loading and integration between components
