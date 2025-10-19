#!/usr/bin/env python3
"""
I2C and Light Sensor Diagnostic Script
Run this to check I2C status and light sensor connectivity
"""

import subprocess
import sys

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def check_i2c_enabled():
    """Check if I2C is enabled"""
    print("=== Checking I2C Configuration ===")
    
    # Check if I2C modules are loaded
    ret, out, err = run_command("lsmod | grep i2c")
    if ret == 0 and out:
        print("✓ I2C modules loaded:")
        print(out)
    else:
        print("✗ I2C modules not loaded")
    
    # Check boot config
    ret, out, err = run_command("grep -i i2c /boot/config.txt")
    if ret == 0 and "dtparam=i2c_arm=on" in out:
        print("✓ I2C enabled in /boot/config.txt")
    else:
        print("✗ I2C not enabled in /boot/config.txt")
        print("Run: echo 'dtparam=i2c_arm=on' | sudo tee -a /boot/config.txt")

def check_i2c_devices():
    """Check for I2C devices"""
    print("\n=== Checking I2C Devices ===")
    
    # Check if i2c-tools is installed
    ret, out, err = run_command("which i2cdetect")
    if ret != 0:
        print("✗ i2c-tools not installed")
        print("Run: sudo apt-get install i2c-tools")
        return
    
    # Scan I2C bus
    ret, out, err = run_command("i2cdetect -y 1")
    if ret == 0:
        print("✓ I2C bus scan (bus 1):")
        print(out)
        
        # Check for BH1750 addresses
        if "23" in out or "5c" in out:
            print("✓ BH1750 light sensor detected!")
        else:
            print("✗ No BH1750 sensor found at addresses 0x23 or 0x5C")
    else:
        print("✗ Cannot scan I2C bus")
        print(f"Error: {err}")

def check_python_libraries():
    """Check Python I2C libraries"""
    print("\n=== Checking Python Libraries ===")
    
    try:
        import smbus2
        print("✓ smbus2 library available")
    except ImportError:
        print("✗ smbus2 library not found")
        print("Run: pip3 install smbus2")
    
    try:
        import RPi.GPIO
        print("✓ RPi.GPIO library available")
    except ImportError:
        print("✗ RPi.GPIO library not found")
        print("Run: pip3 install RPi.GPIO")

def test_light_sensor():
    """Test light sensor directly"""
    print("\n=== Testing Light Sensor ===")
    
    try:
        import smbus2
        bus = smbus2.SMBus(1)
        
        # Try both common BH1750 addresses
        for addr in [0x23, 0x5C]:
            try:
                # Try to read from the sensor
                bus.write_byte(addr, 0x01)  # Power on
                print(f"✓ Successfully communicated with device at 0x{addr:02x}")
                bus.close()
                return
            except Exception as e:
                print(f"✗ Cannot communicate with device at 0x{addr:02x}: {e}")
        
        bus.close()
        print("✗ No BH1750 sensor responding")
        
    except ImportError:
        print("✗ Cannot test - smbus2 not available")
    except Exception as e:
        print(f"✗ Error testing sensor: {e}")

if __name__ == "__main__":
    print("METAR Monitor I2C Diagnostic Tool")
    print("=" * 40)
    
    check_i2c_enabled()
    check_i2c_devices()
    check_python_libraries()
    test_light_sensor()
    
    print("\n=== Summary ===")
    print("If you see errors above:")
    print("1. Enable I2C: sudo raspi-config → Interface Options → I2C → Enable")
    print("2. Install tools: sudo apt-get install i2c-tools")
    print("3. Install Python library: pip3 install smbus2")
    print("4. Connect BH1750 sensor to I2C pins (SDA=GPIO2, SCL=GPIO3)")
    print("5. Reboot after changes: sudo reboot")