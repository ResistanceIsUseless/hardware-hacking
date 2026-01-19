# Hardware Hacking Tool - Quick Reference

## TL;DR - What Works Right Now

```bash
# Use Python 3.12 (Python 3.14 has numpy issues)
PYTHON=~/.pyenv/versions/3.12.10/bin/python3

# Run comprehensive test
$PYTHON test_all_functionality.py

# Launch interactive mode
$PYTHON -m hwh.interactive

# Quick device detection
$PYTHON -c "from hwh import detect; [print(f'{k}: {v.name}') for k,v in detect().items()]"
```

---

## Current Hardware Status

### ✅ Bus Pirate 6 REV2
- **Working:** SPI, I2C, PSU control, pin monitoring
- **Not Working:** UART (firmware v0.0 limitation)
- **Port:** `/dev/cu.usbmodem6buspirate3`

### ⚠️ Bolt CTF (Target Device)
- **Powered:** Yes (3.3V @ 19mA via Bus Pirate)
- **I2C:** SDA stuck LOW (needs SWD programming)
- **SPI:** No flash detected
- **UART:** Not tested (Bus Pirate UART not working yet)

### ❓ Bolt / Bolt CTF USB
- **Status:** Not appearing in USB detection
- **Action:** Verify USB connection or check VID:PID

---

## Interactive Mode Usage

```bash
$PYTHON -m hwh.interactive
```

### Menu Options:
- **[1]** Configure SPI → Auto-detects flash, reads ID
- **[2]** Configure I2C → Scans bus, shows devices
- **[3]** Configure UART → (Not working in firmware v0.0)
- **[4]** Scan target → **⭐ Best option for quick testing**
- **[5]** PSU control → Power on/off, set voltage/current
- **[6]** Read pin voltages → Real-time monitoring
- **[7]** Device info → Firmware version, modes available

---

## Python API Examples

### Detect All Devices
```python
from hwh import detect

devices = detect()
for name, info in devices.items():
    print(f"{name}: {info.device_type} at {info.port}")
```

### Read SPI Flash ID
```python
from hwh import detect, get_backend
from hwh.backends import SPIConfig

bp = get_backend(list(detect().values())[0])
with bp:
    bp.configure_spi(SPIConfig(speed_hz=1_000_000, mode=0))
    flash_id = bp.spi_flash_read_id()
    print(f"Flash ID: {flash_id.hex()}")
```

### Scan I2C Bus
```python
from hwh import detect, get_backend
from hwh.backends import I2CConfig

bp = get_backend(list(detect().values())[0])
with bp:
    bp.set_pullups(enabled=True)
    bp.configure_i2c(I2CConfig(speed_hz=100_000))
    devices = bp.i2c_scan(start_addr=0x08, end_addr=0x77)
    print(f"I2C devices: {[hex(addr) for addr in devices]}")
```

### Automated Target Scan
```python
from hwh import detect, get_backend

bp = get_backend(list(detect().values())[0])
with bp:
    results = bp.scan_target(power_voltage_mv=3300, power_current_ma=300)

    print(f"PSU: {results['psu']['measured_voltage_mv']}mV @ "
          f"{results['psu']['measured_current_ma']}mA")

    if results['i2c_devices']:
        print(f"I2C: {[hex(addr) for addr in results['i2c_devices']]}")

    if results['spi_flash']['detected']:
        print(f"SPI Flash: {results['spi_flash']['id']}")

    for pin, voltage in results['pin_voltages'].items():
        if pin:
            print(f"{pin}: {voltage}mV")
```

### Control PSU
```python
from hwh import detect, get_backend

bp = get_backend(list(detect().values())[0])
with bp:
    # Enable PSU
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)

    # Check current draw
    info = bp.get_info()
    print(f"Current: {info['psu_measured_ma']}mA")

    # Disable PSU
    bp.set_psu(enabled=False)
```

---

## Known Issues & Workarounds

### Issue: I2C SDA Stuck LOW on Bolt CTF
**Symptom:** I2C scan finds no devices, SDA at 17mV

**Cause:** Bolt CTF STM32 needs initial programming via SWD

**Solution:**
1. Connect ST-Link to Bolt CTF (SWDIO, SWCLK, GND, VCC)
2. Program firmware via openocd or ST-Link utility
3. Re-test I2C communication

### Issue: UART Configuration Fails
**Symptom:** "Invalid mode name" error

**Cause:** Firmware v0.0 (development build) doesn't support UART yet

**Workaround:**
- Use I2C or SPI for now
- Wait for firmware update
- Check Bus Pirate forum for beta firmware with UART support

### Issue: Bolt Not Detected via USB
**Possible causes:**
1. USB cable not data-capable (charge-only cable)
2. Bolt not in right mode
3. VID:PID not in detection list

**Check:**
```bash
system_profiler SPUSBDataType | grep -A10 -i bolt
```

---

## Wiring Guide

### Bus Pirate → Bolt CTF (Current Setup)

```
Bus Pirate Pin    →    Bolt CTF Pin
────────────────────────────────────
1 (SDA)           →    PA10 (I2C1_SDA) - STUCK LOW
2 (SCL)           →    PA9  (I2C1_SCL) - OK
3 (MOSI/TX)       →    RX (for future UART)
5 (MISO/RX)       →    TX (for future UART)
GND               →    GND
PSU (3.3V)        →    3V3 (19mA confirmed)
```

### For SWD Programming (ST-Link → Bolt CTF)

```
ST-Link    →    Bolt CTF
──────────────────────────
SWDIO      →    SWDIO
SWCLK      →    SWCLK
GND        →    GND
3.3V       →    3V3
```

---

## File Locations

```
hwh/                                    # Main package
├── __init__.py                         # Package exports
├── detect.py                           # Device detection
├── backends.py                         # Abstract base classes
├── backend_buspirate.py                # Bus Pirate implementation
├── interactive.py                      # Interactive CLI tool
└── pybpio/                             # Official BPIO2 library
    ├── bpio_client.py
    ├── bpio_spi.py
    ├── bpio_i2c.py
    └── bpio_uart.py                    # ✨ NEW - UART wrapper

test_all_functionality.py               # Comprehensive test
test_uart_quick.py                      # UART-specific test
TEST_RESULTS.md                         # This file
QUICK_REFERENCE.md                      # Command cheat sheet

/tmp/latest_scan_results.json           # Most recent scan
/tmp/bolt_scan_results.json             # Previous Bolt scan
/tmp/scan_results.json                  # Earlier scan
```

---

## What's Next?

### To Test Immediately:
1. **Run interactive mode** - See the menu system in action
2. **Try automated scan** - Option [4] gives comprehensive results
3. **Test SPI/I2C** - Verify protocol switching

### To Fix Hardware Issues:
1. **Program Bolt CTF** - Use ST-Link to fix I2C SDA issue
2. **Check Bolt USB** - Verify if Bolt/Bolt CTF appears in USB

### To Build Next:
1. **Multi-device scenarios** - Coordinate Bus Pirate + Bolt
2. **Bolt backend** - Glitching and logic analyzer support
3. **TUI interface** - Better visualization

---

## Getting Help

### Check Device Info
```python
from hwh import detect, get_backend

bp = get_backend(list(detect().values())[0])
bp.connect()
info = bp.get_info()

print(f"Firmware: v{info['version_firmware_major']}.{info['version_firmware_minor']}")
print(f"Date: {info['version_firmware_date']}")
print(f"Git: {info['version_firmware_git_hash']}")
print(f"Modes: {info['modes_available']}")

bp.disconnect()
```

### Save Scan Results
```python
import json
from hwh import detect, get_backend

bp = get_backend(list(detect().values())[0])
bp.connect()

results = bp.scan_target()

with open('my_scan.json', 'w') as f:
    json.dump(results, f, indent=2)

bp.disconnect()
```

---

## Resources

- **Bus Pirate Docs:** https://docs.buspirate.com/
- **BPIO2 Protocol:** https://docs.buspirate.com/docs/binmode-reference/protocol-bpio2/
- **pybpio Source:** https://github.com/DangerousPrototypes/BusPirate-BPIO2-flatbuffer-interface
- **Bus Pirate Forum:** https://forum.buspirate.com/

---

**Last Updated:** 2026-01-19
**Tested With:** Bus Pirate 6 REV2, Firmware v0.0
