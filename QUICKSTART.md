# Quick Start Guide

Get up and running with the hwh toolkit in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- USB-connected hardware (Bus Pirate, Curious Bolt, ST-Link, etc.)
- macOS or Linux

## Installation

### Option 1: Automated Setup (Recommended)

```bash
cd hardware-hacking/hwh
./setup.sh
```

The script will:
- Check Python version
- Install hwh package
- Install dependencies
- Verify installation
- Scan for connected devices

### Option 2: Manual Setup

```bash
cd hardware-hacking/hwh

# Install package
pip3 install -e .

# Install optional dependencies
pip3 install cobs flatbuffers textual

# Verify
python3 -c "from hwh import detect; print('OK')"
```

## First Steps

### 1. Detect Your Hardware

```bash
cd hardware-hacking
python3 hwh/examples/01_device_discovery.py
```

Expected output:
```
=== Hardware Device Discovery ===

Scanning for devices...

✓ Found 2 device(s):

  bolt:
    Type: bolt
    Port: /dev/cu.usbmodem11401
    Capabilities: voltage_glitch, logic_analyzer, power_analysis

  buspirate:
    Type: buspirate
    Port: /dev/cu.usbmodem6buspirate1
    Capabilities: spi, i2c, uart, 1wire, jtag, psu

✓ bolt: Connected
✓ buspirate: Connected

Device Pool Status:
...
```

If you see your devices, you're ready to go! 🎉

### 2. Test UART Automation (Optional)

If you have a target device with UART output:

```bash
python3 hwh/examples/02_uart_auto_interact.py
```

This will:
- Auto-detect shell/login/bootloader
- Try common credentials
- Run enumeration commands
- Display captured data

### 3. Run a Glitch Attack (Advanced)

If you have Curious Bolt + target device:

```bash
python3 hwh/examples/03_stm32_rdp_bypass.py
```

**⚠️ Only test on devices you own!**

## Troubleshooting

### No devices found

**macOS**:
```bash
ls /dev/cu.usb*
```

**Linux**:
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Add user to dialout group if needed
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Import errors

```bash
# Reinstall from hwh directory
cd hwh
pip3 uninstall hwh
pip3 install -e .
pip3 install cobs flatbuffers textual
```

### Connection failures

- Try unplugging/replugging device
- Check USB cable (must be data-capable)
- Close other software accessing the device
- Try different USB port

### Examples fail with ModuleNotFoundError

Run from the **hardware-hacking** directory (parent of hwh):

```bash
cd hardware-hacking  # ← Parent directory
python3 hwh/examples/01_device_discovery.py
```

## Next Steps

### Learn the Components

- **Device Pool** - Multi-device coordination ([hwh/tui/device_pool.py](hwh/tui/device_pool.py))
- **UART Automation** - Smart protocol interaction ([hwh/automation/uart.py](hwh/automation/uart.py))
- **Workflows** - Pre-built attack scenarios ([hwh/workflows/](hwh/workflows/))
- **Glitch Profiles** - Chip-specific parameters ([hwh/glitch_profiles.py](hwh/glitch_profiles.py))

### Read the Documentation

- **Main README**: [hwh/README.md](hwh/README.md) - Complete toolkit documentation
- **Examples Guide**: [hwh/examples/README.md](hwh/examples/README.md) - Example usage
- **Glitch Profiles**: [hwh/GLITCH_PROFILES_GUIDE.md](hwh/GLITCH_PROFILES_GUIDE.md) - Profile database
- **Hardware Setup**: [docs/guides/setup.md](docs/guides/setup.md) - Lab hardware setup
- **Target Guide**: [docs/guides/targets-guide.md](docs/guides/targets-guide.md) - Choosing practice devices

### Try Real Attacks

1. **SPI Flash Dumping**:
   ```python
   from hwh import detect, get_backend
   devices = detect()
   bp = get_backend(devices['buspirate'])
   bp.connect()
   bp.configure_spi(...)
   flash_id = bp.spi_transfer(b'\x9f', read_len=3)
   ```

2. **UART Shell Access**:
   ```python
   from hwh.automation import UARTAutomation
   automation = UARTAutomation(uart_backend)
   results = await automation.auto_interact()
   ```

3. **Voltage Glitching**:
   ```python
   from hwh.workflows import create_adaptive_glitch_workflow
   workflow = create_adaptive_glitch_workflow(
       target_chip="STM32F103C8",
       success_patterns=[b'>>>']
   )
   result = await workflow.run(device_pool)
   ```

### Build Your Own

Check out the [Phase 1 Implementation](hwh/PHASE1_IMPLEMENTATION.md) to understand the architecture and build custom workflows.

## Quick Reference Card

```python
# Device detection
from hwh.detect import detect
devices = detect()

# Device pool (multi-device)
from hwh.tui.device_pool import DevicePool
pool = DevicePool()
await pool.scan_devices()
pool.display_status()

# UART automation
from hwh.automation import UARTAutomation
automation = UARTAutomation(backend)
results = await automation.auto_interact()

# Glitch profiles
from hwh.glitch_profiles import find_profiles_for_chip
profiles = find_profiles_for_chip("STM32F103")

# Workflows
from hwh.workflows import create_adaptive_glitch_workflow
workflow = create_adaptive_glitch_workflow(...)
result = await workflow.run(pool)
```

## Getting Help

- **Examples not working?** Check [hwh/examples/README.md](hwh/examples/README.md)
- **Device not detected?** See [Troubleshooting](#troubleshooting) above
- **Want to contribute?** Read [CONTRIBUTING.md](CONTRIBUTING.md)
- **Found a bug?** Open an issue on GitHub

---

**Ready to hack hardware?** Start with `python3 hwh/examples/01_device_discovery.py` 🚀

*For educational and authorized testing only.*
