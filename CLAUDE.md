# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is an educational hardware hacking repository containing:
1. Attack pattern guides - Educational documentation on vulnerability classes
2. Practical setup instructions - Lab configuration for hardware tools
3. **hwh** - A Python package providing unified interface to hardware hacking tools

## Repository Structure

### 1. hwh Python Package (`hwh/`)

A unified Python interface for multiple hardware hacking tools. Located in the main repository directory (not in this worktree).

**Architecture:**
- `__init__.py` - Package exports (detect, list_devices, get_backend)
- `detect.py` - USB/serial device auto-detection
- `backends.py` - Abstract base classes and backend registry
- `backend_*.py` - Concrete implementations for each tool
- `cli.py` - Click-based command-line interface

**Supported Hardware:**
- ST-Link (SWD/JTAG debug)
- Black Magic Probe (SWD/JTAG/UART)
- Bus Pirate 5/6 (SPI/I2C/UART/JTAG)
- Tigard (SPI/I2C/UART/JTAG/SWD)
- Curious Bolt (voltage glitching, logic analyzer)
- FaultyCat (EMFI, glitching) - planned

**Key Design Patterns:**
- Backend registry pattern for extensibility
- Abstract base classes (Backend, BusBackend, DebugBackend, GlitchBackend)
- Context managers for resource management
- Device auto-detection via USB VID:PID enumeration
- Dataclass configs for protocol parameters (SPIConfig, I2CConfig, GlitchConfig)

### 2. Attack Pattern Guides

Educational guides on vulnerability classes:
   - `memory-disclosure.md` - Buffer overreads caused by attacker-controlled length fields
   - `parser-differential.md` - Security gaps from different interpretations of the same input
   - `deserialization.md` - Code execution via untrusted serialized data
   - `type-confusion.md` - Memory/logic corruption from incompatible type access
   - `toctou.md` - Time-of-check to time-of-use race conditions
   - `canonicalization.md` - Security bypasses via data transformation after validation
   - `gadget-chains.md` - Chaining existing code for malicious execution
   - `state-confusion.md` - Logic bugs from state machine manipulation
   - `truncation.md` - Semantic changes from data truncation
   - `reference-confusion.md` - Resource identity/ownership confusion
   - `semantic-gap.md` - Different layer interpretations of same data

### 3. Practical Guides

- `setup.md` - Comprehensive hardware lab setup (Bus Pirate, GreatFET, Curious Bolt, Faulty Cat, Shikra)
- `targets-guide.md` - Target device selection and exploitation methodology
- `CBECSC23.md` - Additional reference material

### Hardware Environment

The setup.md guide covers a complete hardware hacking lab built around:
- **Bus Pirate v5/v6** - Protocol interface (UART, SPI, I2C, JTAG)
- **GreatFET One** - USB security (emulation, MITM, fuzzing)
- **Curious Bolt** - Voltage glitching, power analysis, logic analyzer
- **Faulty Cat v2.1** - EMFI, voltage glitch, SWD/JTAG detection
- **Shikra** - Fast SPI flash dumps, JTAG, UART

Primary platform: macOS (ARM64 M-series) with Linux compatibility notes.

## Common Commands

### hwh Package Development

The hwh package is located in the main repository at `../hwh/` (relative to this worktree).

```bash
# Install in development mode from main repo
cd "/Users/matthew/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking"
pip install -e "hwh[dev]"

# Or install with specific backends
pip install -e "hwh[stlink,buspirate,tigard]"

# Run tests
cd hwh && pytest

# Lint code
ruff check hwh/

# Type checking
mypy hwh/
```

**CLI Usage:**
```bash
# Detect connected devices
hwh detect

# Dump SPI flash
hwh spi dump -o firmware.bin -a 0x0 -s 0x100000

# Read flash ID
hwh spi id

# Scan I2C bus
hwh i2c scan

# Dump firmware via SWD
hwh debug dump -o firmware.bin -a 0x08000000 -s 0x10000

# Trigger single glitch
hwh glitch single -w 100 -o 500

# Glitch parameter sweep
hwh glitch sweep --width-min 50 --width-max 500 --offset-min 0 --offset-max 1000

# Interactive shell
hwh shell
```

**Python API Example:**
```python
from hwh import detect, get_backend
from hwh.backends import SPIConfig

# Detect devices
devices = detect()

# Use Bus Pirate for SPI flash dump
bp = get_backend(devices['buspirate'])
with bp:
    bp.configure_spi(SPIConfig(speed_hz=1_000_000))
    flash_id = bp.spi_transfer(b'\x9f', read_len=3)
    data = bp.spi_flash_read(0x0, 0x1000)
```

### Firmware Analysis
```bash
# Extract firmware filesystem
binwalk -Me firmware.bin

# Entropy analysis (detect encryption)
binwalk -E firmware.bin

# Search for secrets
strings firmware.bin | grep -iE "password|key|token|api"

# Comprehensive firmware scan (requires EMBA)
sudo ./emba -l ./logs -f firmware.bin
```

### Flash Memory Operations
```bash
# Read SPI flash with Shikra (fastest)
flashrom -p ft2232_spi:type=232H -r dump.bin

# Read SPI flash with Bus Pirate
flashrom -p buspirate_spi:dev=/dev/ttyACM0,spispeed=1M -r dump.bin

# ESP32/ESP8266 flash dump
esptool.py --port /dev/ttyUSB0 read_flash 0 0x400000 esp_dump.bin

# Identify chip only
flashrom -p ft2232_spi:type=232H -V
```

### Serial/UART Access
```bash
# Connect with tio (recommended - auto-reconnect)
tio /dev/ttyACM0

# Common baud rates for embedded devices:
# 115200 - Most common
# 74880 - ESP boot messages
# 9600 - Older devices
```

### Network Reconnaissance (IoT Targets)
```bash
# Find devices on network
nmap -sn 192.168.1.0/24

# Full port scan
nmap -sV -sC -p- <target_ip>

# Check for ONVIF (cameras)
onvifscan http://<target_ip>

# Test RTSP stream
ffplay rtsp://<ip>:554/cam/realmonitor?channel=1&subtype=0
```

### Device Detection
```bash
# macOS - Find USB devices
system_profiler SPUSBDataType | grep -A5 -E "Bus Pirate|GreatFET|FTDI"

# Linux - List USB devices
lsusb | grep -E "1209|1d50|0403|2e8a"
dmesg | tail -20  # After connecting device

# Find serial ports
# macOS:
ls /dev/tty.usbmodem* /dev/cu.usbmodem*
# Linux:
ls /dev/ttyACM* /dev/ttyUSB*
```

## Architecture Notes

### hwh Package Architecture

**Backend System:**
- All backends inherit from abstract base classes in `backends.py`
- Three main backend types:
  - `BusBackend` - For SPI/I2C/UART protocols (Bus Pirate, Tigard)
  - `DebugBackend` - For SWD/JTAG debug (ST-Link, Black Magic Probe)
  - `GlitchBackend` - For fault injection (Curious Bolt, FaultyCat)
- Backends register themselves via `register_backend()` decorator/function
- `get_backend()` returns appropriate backend instance for a DeviceInfo

**Device Detection:**
- Two-phase detection: USB enumeration + serial port scanning
- USB VID:PID mappings in `KNOWN_USB_DEVICES` dict
- Deduplication to handle same device appearing via multiple methods
- RP2040 devices require probing to distinguish Bolt from FaultyCat

**Configuration Objects:**
- Dataclasses for type-safe protocol configuration
- `SPIConfig(speed_hz, mode, bits_per_word, cs_active_low)`
- `I2CConfig(speed_hz, address_bits)`
- `UARTConfig(baudrate, data_bits, parity, stop_bits)`
- `GlitchConfig(width_ns, offset_ns, repeat, trigger_channel, trigger_edge)`

**Adding New Backends:**
1. Create `backend_newdevice.py`
2. Inherit from appropriate base class
3. Implement abstract methods
4. Register via `register_backend("devicetype", BackendClass)`
5. Import in `backends.py` to trigger registration
6. Add USB VID:PID to `KNOWN_USB_DEVICES` in `detect.py`

**TODO Items (from README):**
- Full BPIO2 FlatBuffers implementation for Bus Pirate
- FaultyCat backend implementation
- TUI with textual library
- Protocol auto-detection
- JTAG/SWD pin finder

### Educational Philosophy

The guides teach **transferable patterns** rather than specific exploits. Each vulnerability class document follows a structure:
- Overview with real-world CVE examples
- Deep dive into the fundamental pattern
- Attack surface identification across technologies
- Pattern recognition for finding similar bugs
- Practical methodology and tools

### Target Hardware Categories

From `targets-guide.md`, practice targets are organized by difficulty:

**Tier 1 (Easiest)**: ESP32/ESP8266 devices, Sonoff, Tuya smart plugs
- UART almost always exposed
- Easy SPI flash dumps
- Well-documented attack paths

**Tier 2 (Medium)**: Amcrest/Reolink cameras, TP-Link routers
- Network + hardware attack surfaces
- Known CVEs to research
- Good firmware RE practice

**Tier 3 (Advanced)**: UniFi cameras, enterprise gear
- Signed firmware
- Secure boot
- Professional security implementations

### Safety Considerations

**Critical**: When working with mains-powered devices (smart plugs, bulbs, some cameras):
- ALWAYS unplug from mains voltage before opening
- 120V/240V can be lethal
- Document in any new guides involving such devices

**Legal**: Only test devices you own. Follow responsible disclosure for vulnerabilities.

## Platform-Specific Notes

### ARM64 macOS Considerations

When building tools or Docker containers for external systems:
- Always specify `--platform` argument for cross-platform builds
- Example: `docker build --platform linux/amd64 .`
- Many firmware analysis tools expect x86_64 Linux

### Tool Installation Paths

Standard directory structure (from setup.md):
```
~/hardware_hacking/
├── projects/{active,archive}
├── tools/{buspirate,greatfet,curious_bolt,faulty_cat,shikra}
├── firmware/{extracted,modified,backups}
├── scripts/
├── docs/
├── dumps/
└── mcp_servers/
```

## AI-Powered Analysis Tools

The setup includes integration with:
- **GhidraMCP** - AI-assisted reverse engineering via Ghidra
- **pyghidra-mcp** - Headless multi-binary analysis
- **Radare2 MCP** - Alternative RE framework
- **IoTHackBot** - Claude Code skills for IoT pentesting

Configuration for these is in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

## Content Guidelines

When creating new guides or modifying existing ones:

1. **Focus on patterns**, not just specific CVEs
2. **Real-world examples** - Include actual CVE numbers and affected products
3. **Cross-technology applicability** - Show how the same pattern appears in different contexts
4. **Practical methodology** - Include hands-on commands and tool usage
5. **Safety warnings** - Especially for mains voltage, legal considerations
6. **Update dates** - Mark guides with last update timestamp

## Testing and Development

### hwh Package Tests

The hwh package uses pytest for testing. Tests should be added in a `tests/` directory:

```bash
# Run all tests
cd hwh && pytest

# Run with coverage
pytest --cov=hwh

# Run specific test file
pytest tests/test_detect.py

# Run with verbose output
pytest -v
```

**Test Structure:**
- Unit tests for device detection logic
- Mock backends for testing without hardware
- Integration tests with actual hardware (when available)
- CLI command tests using Click's testing utilities

### Code Quality

```bash
# Linting with ruff
ruff check hwh/

# Auto-fix issues
ruff check --fix hwh/

# Type checking
mypy hwh/

# Format check (line length, etc)
ruff format hwh/
```

**Standards:**
- Python 3.10+ required
- Type hints on all public APIs
- Docstrings for modules and public functions
- Line length: 100 characters (configured in pyproject.toml)

## Vulnerability Research Ethics

All content in this repository is for:
- Authorized security testing
- Defensive security research
- CTF challenges and competitions
- Educational purposes
- Testing on personally-owned devices only

Never assist with:
- Unauthorized access to systems
- Attacks on production systems not owned by the researcher
- Malicious use of disclosed vulnerabilities

## Package Publishing

The hwh package is configured for PyPI publishing via pyproject.toml:

```bash
# Build package
python -m build

# Upload to PyPI (when ready)
python -m twine upload dist/*
```

**Project metadata is in pyproject.toml:**
- Version: 0.1.0 (update before release)
- License: MIT
- Python requirement: >=3.10
- Homepage/Repository URLs need updating from placeholder
