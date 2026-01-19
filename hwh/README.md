# hwh - Unified Hardware Hacking Tool

A single interface for hardware hacking tools: **ST-Link**, **Black Magic Probe**, **Bus Pirate**, **Tigard**, **Curious Bolt**, and **FaultyCat**.

## Features

- **Device auto-detection** - Enumerate connected tools
- **Unified bus protocols** - SPI, I2C, UART across devices
- **Debug interface** - SWD/JTAG via ST-Link or Black Magic Probe
- **Glitch campaigns** - Voltage fault injection with Bolt
- **Extensible backends** - Add new tools easily

## Installation

```bash
# Basic install
pip install hwh

# With all hardware support
pip install hwh[all]

# Or specific backends
pip install hwh[stlink,blackmagic,buspirate,tigard]
```

### Dependencies by Backend

| Backend | Extra | Libraries |
|---------|-------|-----------|
| Bus Pirate 5/6 | `buspirate` | pyserial, cobs |
| Tigard | `tigard` | pyftdi |
| ST-Link | `stlink` | pyocd |
| Black Magic Probe | `blackmagic` | pygdbmi |
| USB detection | `usb` | pyusb |

## Quick Start

### Detect Connected Devices

```bash
hwh detect
```

Output:
```
Name                      Type            Port                 VID:PID      Capabilities
------------------------------------------------------------------------------------------
ST-Link V2-1              stlink          /dev/ttyACM0         0483:374b    swd, jtag, debug
Bus Pirate 5              buspirate       /dev/ttyACM1         2047:0900    spi, i2c, uart...
Curious Bolt              bolt            /dev/ttyACM2         2e8a:000a    glitch, logic, dpa
```

### Dump SPI Flash

```bash
# Auto-select first SPI device
hwh spi dump -o firmware.bin -a 0x0 -s 0x100000

# Specify device
hwh spi dump -d tigard -o firmware.bin -a 0x0 -s 0x100000
```

### Scan I2C Bus

```bash
hwh i2c scan
```

### Dump Firmware via SWD

```bash
hwh debug dump -o firmware.bin -a 0x08000000 -s 0x10000
```

### Trigger Glitch

```bash
# Single glitch
hwh glitch single -w 100 -o 500

# Parameter sweep
hwh glitch sweep --width-min 50 --width-max 500 --offset-min 0 --offset-max 1000 -o results.json
```

### Interactive Shell

```bash
hwh shell
```

```python
# In the shell
devices = detect()
bp = get_backend(devices['buspirate'])
bp.connect()
bp.configure_spi(SPIConfig(speed_hz=1000000))
data = bp.spi_transfer(b'\x9f', read_len=3)  # Read JEDEC ID
print(f"Flash ID: {data.hex()}")
```

## Python API

```python
from hwh import detect, get_backend
from hwh.backends import SPIConfig, I2CConfig, GlitchConfig

# Detect devices
devices = detect()

# SPI flash dump with Bus Pirate
bp = get_backend(devices['buspirate'])
with bp:
    bp.configure_spi(SPIConfig(speed_hz=1_000_000))
    flash_id = bp.spi_transfer(b'\x9f', read_len=3)
    data = bp.spi_flash_read(0x0, 0x1000)

# Debug with ST-Link
stlink = get_backend(devices['stlink'])
with stlink:
    stlink.connect_target("stm32f103c8")
    stlink.halt()
    firmware = stlink.dump_firmware(0x08000000, 0x10000)
    regs = stlink.read_registers()

# Glitching with Bolt
bolt = get_backend(devices['bolt'])
with bolt:
    bolt.configure_glitch(GlitchConfig(width_ns=100, offset_ns=500))
    bolt.trigger()
    
    # Parameter sweep
    results = bolt.run_glitch_sweep(
        width_range=(50, 500),
        width_step=10,
        offset_range=(0, 1000),
        offset_step=50,
        attempts_per_setting=5
    )
```

## Coordinated Attack Example

```python
from hwh import detect, get_backend
from hwh.backends import GlitchConfig, TriggerEdge

devices = detect()
stlink = get_backend(devices['stlink'])
bolt = get_backend(devices['bolt'])

with stlink, bolt:
    # Setup debug
    stlink.connect_target("auto")
    stlink.reset(halt=True)
    
    # Set breakpoint at security check
    bp_id = stlink.set_breakpoint(0x08001234)
    
    # Configure glitch on external trigger
    bolt.configure_glitch(GlitchConfig(
        width_ns=100,
        offset_ns=500,
        trigger_channel=0,
        trigger_edge=TriggerEdge.FALLING
    ))
    bolt.arm()
    
    # Resume - when breakpoint hits, GPIO triggers, Bolt glitches
    stlink.resume()
```

## Supported Hardware

| Device | SPI | I2C | UART | JTAG | SWD | Glitch | Status |
|--------|-----|-----|------|------|-----|--------|--------|
| ST-Link | - | - | - | ✅ | ✅ | - | Working |
| Black Magic Probe | - | - | ✅* | ✅ | ✅ | - | Working |
| Bus Pirate 5/6 | ✅ | ✅ | ✅ | ✅ | - | - | Needs BPIO2 tooling |
| Tigard | ✅ | ✅ | ✅ | ✅ | ✅ | - | Working |
| Curious Bolt | - | - | - | - | - | ✅ | Needs scope lib |
| FaultyCat | - | - | - | Scan | Scan | ✅ | Planned |

*BMP has UART passthrough on second serial port

## Architecture

```
hwh/
├── __init__.py       # Package exports
├── detect.py         # USB/serial device detection
├── backends.py       # Base classes + registry
├── backend_buspirate.py
├── backend_bolt.py
├── backend_stlink.py
├── backend_tigard.py
├── backend_blackmagic.py
└── cli.py            # Click CLI
```

## Adding a Backend

```python
from hwh.backends import Backend, register_backend

class MyBackend(Backend):
    def connect(self) -> bool:
        # Implementation
        pass
    
    def disconnect(self):
        pass
    
    def get_info(self) -> dict:
        return {"name": "My Device"}

register_backend("mydevice", MyBackend)
```

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/yourusername/hwh
cd hwh
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check hwh/
```

## TODO

- [ ] Full BPIO2 FlatBuffers implementation for Bus Pirate
- [ ] FaultyCat backend
- [ ] TUI with textual
- [ ] Protocol auto-detection
- [ ] JTAG/SWD pin finder

## License

MIT
