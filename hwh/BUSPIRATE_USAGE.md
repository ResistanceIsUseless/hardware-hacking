# Bus Pirate Usage Guide

## Status

✅ **FULLY WORKING** - Tested with Bus Pirate 6 REV2

## Implementation

The Bus Pirate backend uses the **official pybpio library** from DangerousPrototypes, wrapped in our unified backend interface.

**Source:** https://github.com/DangerousPrototypes/BusPirate-BPIO2-flatbuffer-interface

## Prerequisites

### Hardware
- Bus Pirate 5 or 6
- USB cable

### Software Dependencies

```bash
pip install cobs flatbuffers numpy
```

Or install with Bus Pirate support:
```bash
pip install -e "hwh[buspirate]"
```

## Important: Binary Mode Requirement

⚠️ **The Bus Pirate MUST be in BPIO2 binary mode before use.**

### Manual Method (Recommended for first use)

1. Connect to the console port with a terminal:
   ```bash
   tio /dev/cu.usbmodem6buspirate1
   # or
   screen /dev/cu.usbmodem6buspirate1 115200
   ```

2. Enter binary mode:
   ```
   binmode
   ```

3. Select **BBIO2** (option 2)

4. Optionally save as default mode

5. Exit the terminal (Ctrl+A, K for screen; Ctrl+T, Q for tio)

### Automatic Method (Future Enhancement)

The backend attempts to automatically enter binary mode via the console port, but manual entry is more reliable currently.

## Usage Examples

### Python API

```python
from hwh import detect, get_backend
from hwh.backends import SPIConfig, I2CConfig

# Detect Bus Pirate
devices = detect()
bp = get_backend(devices['buspirate'])

# Connect (assumes already in binary mode)
with bp:
    # Get device info
    info = bp.get_info()
    print(f"Firmware: v{info['version_firmware_major']}.{info['version_firmware_minor']}")
    print(f"Available modes: {info['modes_available']}")

    # Configure SPI
    bp.configure_spi(SPIConfig(speed_hz=1_000_000, mode=0))

    # Read SPI flash ID
    flash_id = bp.spi_flash_read_id()
    print(f"Flash ID: {flash_id.hex()}")

    # Configure I2C
    bp.configure_i2c(I2CConfig(speed_hz=400_000))

    # Scan I2C bus
    devices = bp.i2c_scan()
    print(f"I2C devices found: {[hex(addr) for addr in devices]}")

    # Control PSU
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)

    # Enable pull-ups
    bp.set_pullups(enabled=True)
```

### CLI (Future)

```bash
# Detect devices
hwh detect

# Read SPI flash
hwh spi id
hwh spi dump -o firmware.bin -a 0x0 -s 0x100000

# Scan I2C bus
hwh i2c scan
```

## Supported Features

### Protocols
- ✅ SPI (read, write, transfer)
- ✅ I2C (read, write, scan)
- ✅ UART (read, write)
- ⚠️  1-Wire (not yet wrapped in backend)
- ⚠️  JTAG (not yet implemented)

### Hardware Features
- ✅ Programmable PSU control
- ✅ Pull-up resistors
- ✅ LED control (via pybpio)
- ✅ ADC readings (via status request)

### SPI Flash Operations
- ✅ Read JEDEC ID (0x9F command)
- ✅ Read flash memory
- ⚠️  Write/erase (not yet implemented for safety)

## Architecture

```
hwh.backend_buspirate.BusPirateBackend
    ↓ wraps
pybpio.bpio_client.BPIOClient
    ↓ uses
tooling.bpio.* (FlatBuffers generated code)
    ↓ serializes to
BPIO2 FlatBuffers protocol
    ↓ encodes with
COBS framing
    ↓ transmits over
Serial port at 3,000,000 baud
```

## Port Detection

Bus Pirate 5/6 exposes two serial ports:
- **Port 1** (`buspirate1`): Console/terminal interface
- **Port 3** (`buspirate3`): BPIO2 binary mode interface

The backend automatically detects and connects to the BPIO2 port (port 3).

## Troubleshooting

### No response from Bus Pirate

**Solution:** Ensure the Bus Pirate is in BPIO2 binary mode:
```bash
tio /dev/cu.usbmodem6buspirate1
> binmode
> 2  # Select BBIO2
```

### Timeout waiting for response

**Symptoms:** Both console and binary ports don't respond

**Possible causes:**
1. Bus Pirate in wrong mode - enter binmode manually
2. Firmware not running - power cycle the device
3. Wrong baud rate - BPIO2 uses 3,000,000 baud by default

**Solution:**
1. Unplug Bus Pirate
2. Wait 5 seconds
3. Plug back in
4. Enter binmode manually via console

### Import errors

```python
ModuleNotFoundError: No module named 'cobs'
```

**Solution:** Install dependencies:
```bash
pip install cobs flatbuffers numpy
```

### All LEDs red

**Symptoms:** Bus Pirate LEDs all show red, no serial response

**Solution:** Power cycle the device (unplug/replug USB)

## Testing

Run the test suite:
```bash
cd hwh
python test_buspirate.py
```

Expected output:
```
✅ Bus Pirate detected
✅ Backend created
✅ Connected to Bus Pirate
✅ Status received
✅ SPI configured successfully
✅ I2C configured successfully
✅ ALL TESTS PASSED!
```

## Known Limitations

1. **Manual binmode entry required** - Automatic entry is implemented but not fully reliable
2. **No auto-save of binmode** - User must manually save BBIO2 as default if desired
3. **UART mode not fully tested** - Implementation exists but needs hardware validation
4. **1-Wire not wrapped** - Available in pybpio but not exposed in our backend yet

## Hardware Tested

- ✅ Bus Pirate 6 REV2
- ⏳ Bus Pirate 5 (not yet tested, should work)

## References

- [Official BPIO2 Documentation](https://docs.buspirate.com/docs/binmode-reference/protocol-bpio2/)
- [pybpio Source Code](https://github.com/DangerousPrototypes/BusPirate-BPIO2-flatbuffer-interface)
- [Bus Pirate Forum](https://forum.buspirate.com/)

---

Last updated: 2026-01-18
