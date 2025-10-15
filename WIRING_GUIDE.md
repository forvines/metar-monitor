# METAR Monitor Wiring Guide

## Components Required

### Main Components
- Raspberry Pi (any model with GPIO pins)
- WS2811/WS2812B LED Strip
- Momentary Push Button
- BH1750 Light Sensor Module (I2C)

### Additional Components
- Jumper wires (male-to-female and male-to-male)
- Breadboard (optional, for prototyping)
- 5V Power Supply for LED strip (if using many LEDs)
- 10kΩ resistor (built into most button modules)

## GPIO Pin Assignments

| Component | GPIO Pin (BCM) | Physical Pin | Wire Color | Notes |
|-----------|----------------|--------------|------------|-------|
| **LED Strip Data** | GPIO 18 | Pin 12 | Green/White | PWM capable pin |
| **Button Input** | GPIO 17 | Pin 11 | Yellow | Pull-up enabled in software |
| **Light Sensor SDA** | GPIO 2 | Pin 3 | Blue | I2C Data |
| **Light Sensor SCL** | GPIO 3 | Pin 5 | Purple | I2C Clock |

## Power Connections

| Component | Power Requirements | Connection |
|-----------|-------------------|------------|
| **Raspberry Pi** | 5V 3A | USB-C or GPIO pins 2,4 (+5V) |
| **LED Strip** | 5V (60mA per LED) | External 5V supply recommended for >20 LEDs |
| **Button** | 3.3V | Pin 1 (+3.3V) |
| **Light Sensor** | 3.3V | Pin 1 (+3.3V) |

## Detailed Wiring Instructions

### 1. LED Strip (WS2811/WS2812B)
```
LED Strip    →    Raspberry Pi
VCC (Red)    →    Pin 2 (+5V) or External 5V Supply
GND (Black)  →    Pin 6 (GND)
DIN (Green)  →    Pin 12 (GPIO 18)
```

### 2. Push Button (Mode Toggle)
```
Button       →    Raspberry Pi
VCC          →    Pin 1 (+3.3V)
GND          →    Pin 9 (GND)
Signal       →    Pin 11 (GPIO 17)
```

### 3. BH1750 Light Sensor (I2C)
```
BH1750       →    Raspberry Pi
VCC          →    Pin 1 (+3.3V)
GND          →    Pin 6 (GND)
SDA          →    Pin 3 (GPIO 2 - SDA)
SCL          →    Pin 5 (GPIO 3 - SCL)
ADDR         →    GND (for 0x23 address) or VCC (for 0x5C address)
```

## Raspberry Pi Pinout Reference

```
     3.3V  1 ● ● 2   5V
GPIO  2  3 ● ● 4   5V
GPIO  3  5 ● ● 6   GND
GPIO  4  7 ● ● 8   GPIO 14
      GND 9 ● ● 10  GPIO 15
GPIO 17 11 ● ● 12  GPIO 18  ← LED Strip
GPIO 27 13 ● ● 14  GND
GPIO 22 15 ● ● 16  GPIO 23
     3.3V 17 ● ● 18  GPIO 24
GPIO 10 19 ● ● 20  GND
GPIO  9 21 ● ● 22  GPIO 25
GPIO 11 23 ● ● 24  GPIO 8
      GND 25 ● ● 26  GPIO 7
GPIO  0 27 ● ● 28  GPIO 1
GPIO  5 29 ● ● 30  GND
GPIO  6 31 ● ● 32  GPIO 12
GPIO 13 33 ● ● 34  GND
GPIO 19 35 ● ● 36  GPIO 16
GPIO 26 37 ● ● 38  GPIO 20
      GND 39 ● ● 40  GPIO 21
```

## I2C Configuration

### Enable I2C on Raspberry Pi
```bash
# Edit the config file
sudo nano /boot/config.txt

# Add or uncomment this line:
dtparam=i2c_arm=on

# Reboot
sudo reboot
```

### Install I2C Tools
```bash
sudo apt-get update
sudo apt-get install i2c-tools python3-smbus

# Test I2C connection (should show device at 0x23 or 0x5C)
i2cdetect -y 1
```

## Power Considerations

### LED Strip Power Requirements
- Each LED consumes ~60mA at full brightness
- For 100 LEDs: 100 × 60mA = 6A at 5V
- Raspberry Pi can only supply 1.2A total on GPIO pins
- **Use external 5V power supply for >20 LEDs**

### Power Supply Recommendations
- **Small setup (<20 LEDs)**: Raspberry Pi power only
- **Medium setup (20-50 LEDs)**: 5V 5A power supply
- **Large setup (50+ LEDs)**: 5V 10A+ power supply

### Ground Connections
**CRITICAL**: All components must share a common ground
```
External 5V Supply GND → LED Strip GND → Raspberry Pi GND
```

## Safety Notes

1. **Never exceed 5V on GPIO pins** - Can damage Raspberry Pi
2. **Connect grounds first** - Prevents voltage spikes
3. **Use appropriate wire gauge** - 18-20 AWG for LED power
4. **Add fuses** - 5A fuse on LED power supply recommended
5. **Check polarity** - Reverse polarity can damage components

## Troubleshooting

### LED Strip Issues
- **No LEDs light up**: Check power supply, ground connections
- **Wrong colors**: Check data pin connection (GPIO 18)
- **Flickering**: Insufficient power supply or loose connections

### Button Issues
- **No response**: Check GPIO 17 connection and pull-up configuration
- **Multiple triggers**: Increase debounce time in software

### Light Sensor Issues
- **Not detected**: Run `i2cdetect -y 1` to verify I2C connection
- **Wrong readings**: Check VCC (should be 3.3V) and address pin

### I2C Issues
- **Device not found**: Check SDA/SCL connections and I2C enable
- **Multiple devices**: Ensure different I2C addresses

## Wire Management Tips

1. **Use different colored wires** for easy identification
2. **Label connections** with tape or markers
3. **Secure connections** with heat shrink or electrical tape
4. **Route power separately** from data lines to reduce interference
5. **Use breadboard** for prototyping before permanent installation

## Testing Procedure

1. **Power on Raspberry Pi** without LED strip connected
2. **Test I2C sensor**: `i2cdetect -y 1`
3. **Test button**: Monitor GPIO 17 with software
4. **Connect LED strip** with external power
5. **Test light sensor** readings
6. **Run full application** with all components