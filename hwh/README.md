# hwh - Hardware Hacking Toolkit

A unified interface for hardware security tools with multi-device coordination, intelligent automation, and profile-guided attacks.

**Supported Hardware**: ST-Link, Black Magic Probe, Bus Pirate, Tigard, Curious Bolt, FaultyCat

## Features

### Core Capabilities
- **Device auto-detection** - Enumerate and identify connected tools
- **Multi-device coordination** - Orchestrate attacks using multiple tools simultaneously
- **Unified bus protocols** - SPI, I2C, UART with consistent API across devices
- **Debug interface** - SWD/JTAG via ST-Link, Black Magic Probe, or Tigard
- **Voltage glitching** - Fault injection campaigns with Curious Bolt
- **UART automation** - Intelligent interaction with shells, bootloaders, and custom protocols

### Advanced Features
- **Glitch profile database** - Chip-specific attack parameters from research and CTFs
- **Adaptive workflows** - Multi-phase attacks that learn and optimize
- **Pattern detection** - Automatic environment recognition for UART targets
- **Success mapping** - Build device-specific parameter maps
- **Time optimization** - 5 minutes vs 30-60 minutes for documented attacks

## Installation

### Prerequisites

- Python 3.10 or higher
- USB access to hardware devices
- macOS or Linux (ARM/x86)

### Install from Source

```bash
git clone https://github.com/yourusername/hardware-hacking
cd hardware-hacking/hwh

# Install package
pip install -e .

# Install optional dependencies for full functionality
pip install cobs flatbuffers textual
```

### Verify Installation

```bash
# Check that devices are detected
python3 -c "from hwh.detect import detect; devices = detect(); print(f'Found {len(devices)} device(s)')"
```

If you see your connected hardware listed, you're ready to go!

## Quick Start

### 1. Detect Connected Devices

```bash
python3 -c "
from hwh.detect import detect
devices = detect(identify_unknown=True)
for dev_id, info in devices.items():
    print(f'{dev_id}: {info.device_type} on {info.port}')
    print(f'  Capabilities: {info.capabilities}')
"
```

Expected output:
```
bolt: bolt on /dev/cu.usbmodem11401
  Capabilities: ['voltage_glitch', 'logic_analyzer', 'power_analysis']
buspirate: buspirate on /dev/cu.usbmodem6buspirate1
  Capabilities: ['spi', 'i2c', 'uart', '1wire', 'jtag', 'psu']
```

### 2. Test Device Connection

```python
import asyncio
from hwh.tui.device_pool import DevicePool

async def test_connection():
    pool = DevicePool()
    devices = await pool.scan_devices()
    print(f"Found {len(devices)} device(s)")

    for dev_id in devices:
        if await pool.connect(dev_id):
            print(f"✓ Connected to {dev_id}")
        else:
            print(f"✗ Failed to connect to {dev_id}")

    pool.display_status()

asyncio.run(test_connection())
```

### 3. Run Your First Workflow

Once devices connect successfully, you can run coordinated attacks:

```python
import asyncio
from hwh.tui.device_pool import DevicePool, DeviceRole
from hwh.workflows import create_adaptive_glitch_workflow
from hwh.glitch_profiles import TargetType

async def main():
    pool = DevicePool()
    await pool.scan_devices()

    # Assign roles
    glitchers = pool.get_devices_by_capability("voltage_glitch")
    monitors = pool.get_devices_by_capability("uart")

    pool.assign_role(glitchers[0], DeviceRole.GLITCHER)
    pool.assign_role(monitors[0], DeviceRole.MONITOR)

    await pool.connect(glitchers[0])
    await pool.connect(monitors[0])

    # Create workflow
    workflow = create_adaptive_glitch_workflow(
        target_chip="STM32F103C8",
        attack_target=TargetType.RDP_BYPASS,
        success_patterns=[b'>>>', b'target halted']
    )

    # Run attack
    result = await workflow.run(pool)
    print(f"Success rate: {result.results['success_rate'] * 100:.2f}%")

asyncio.run(main())
```

## Usage Modes

### 1. Python API (Programmatic)

Direct access to backends and workflows:

```python
from hwh import detect, get_backend
from hwh.backends import SPIConfig, GlitchConfig

# Low-level device access
devices = detect()
bolt = get_backend(devices['bolt'])
bolt.connect()
bolt.configure_glitch(GlitchConfig(width_ns=100, offset_ns=500))
bolt.trigger()
```

### 2. Device Pool (Multi-Device Coordination)

For coordinating multiple devices:

```python
from hwh.tui.device_pool import DevicePool, DeviceRole

pool = DevicePool()
await pool.scan_devices()

# Smart device selection
device_id = await pool.auto_select("glitch STM32 with UART monitoring")

# Or manual assignment
pool.assign_role("bolt", DeviceRole.GLITCHER)
pool.assign_role("buspirate", DeviceRole.MONITOR)

# Get recommendations
recommendations = pool.recommend_for_task("dump SPI flash")
```

### 3. Workflows (Pre-Built Attack Scenarios)

Use pre-configured attack workflows:

```python
from hwh.workflows import create_adaptive_glitch_workflow, GlitchMonitorWorkflow
from hwh.glitch_profiles import TargetType

# Adaptive workflow (uses glitch profiles)
workflow = create_adaptive_glitch_workflow(
    target_chip="STM32F103C8",
    attack_target=TargetType.RDP_BYPASS,
    success_patterns=[b'>>>', b'target halted']
)

result = await workflow.run(pool)
```

### 4. TUI (Interactive Terminal UI) - Coming Soon

```bash
python3 -m hwh.tui.app
```

## Key Components

### Device Pool (`hwh/tui/device_pool.py`)

Manages multiple hardware devices with role assignment and coordination:

- **Role-based management**: Assign devices as GLITCHER, MONITOR, FLASHER, DEBUGGER
- **Smart recommendations**: System suggests best devices for tasks
- **Health tracking**: Monitor connection status, errors, activity
- **Async coordination**: Device locks and coordinated workflows

```python
from hwh.tui.device_pool import DevicePool, DeviceRole

pool = DevicePool()
await pool.scan_devices()
pool.assign_role("bolt", DeviceRole.GLITCHER)
pool.display_status()
```

### UART Automation (`hwh/automation/uart.py`)

Intelligent UART interaction with pattern detection:

- **Environment detection**: Identifies shells, logins, bootloaders, custom protocols
- **Auto-interaction**: Tries common credentials, runs enumeration
- **Pattern library**: Regex patterns for Linux shells, U-Boot, etc.
- **Shell enumeration**: Safe read-only commands for system information

```python
from hwh.automation import UARTAutomation

automation = UARTAutomation(uart_backend)
await automation.configure(baudrate=115200)

# Auto-detect and interact
results = await automation.auto_interact()

if results['login_success']:
    print("Logged in!")
    print(results['enumeration'])
```

### Bus Pirate Wrapper (`hwh/wrappers/buspirate.py`)

High-level wrapper for 20 most-used Bus Pirate commands:

- Voltage measurement, PSU control, pull-ups
- Frequency measurement, PWM generation
- Quick SPI/I2C/UART operations
- GPIO control, LED control, device info
- Native terminal escape hatch

```python
from hwh.wrappers import BusPirateWrapper

wrapper = BusPirateWrapper(buspirate_backend)

# Quick operations
voltage = wrapper.measure_voltage()
devices = wrapper.i2c_quick_scan()
flash_id = wrapper.spi_flash_id()

wrapper.power_on(voltage=3.3)
```

### Glitch Profile Database (`hwh/glitch_profiles.py`)

Chip-specific attack parameters from research, CTFs, and community:

- **8 pre-loaded profiles**: STM32F1/F4, ATmega328P, ESP32, Kinetis, PIC18F
- **Query functions**: Search by chip, attack type, keyword
- **Success tracking**: Document known-good parameters
- **Time savings**: 5 minutes vs 30-60 minutes for blind search

```python
from hwh.glitch_profiles import find_profiles_for_chip, get_profile

# Find profiles for your chip
profiles = find_profiles_for_chip("STM32F103C8")

# Get specific profile
profile = get_profile("STM32F1_RDP_BYPASS")
print(f"Known params: {profile.successful_params}")
print(f"Success rate: {profile.success_rate}")
```

See [GLITCH_PROFILES_GUIDE.md](GLITCH_PROFILES_GUIDE.md) for complete usage.

### Workflow Engine (`hwh/workflows/`)

Multi-device workflow coordination:

- **Base classes**: `Workflow`, `ParameterSweepWorkflow`, `MonitoringMixin`
- **Progress tracking**: Real-time progress updates (0-100%)
- **Cancellation support**: User can cancel long-running workflows
- **Success recording**: Track successful parameter combinations
- **Adaptive search**: Three-phase optimization (known params → coarse → fine)

```python
from hwh.workflows import create_adaptive_glitch_workflow

workflow = create_adaptive_glitch_workflow(
    target_chip="STM32F103C8",
    attack_target=TargetType.RDP_BYPASS,
    success_patterns=[b'>>>']
)

result = await workflow.run(device_pool)
print(f"Found {result.results['success_count']} successes")
```

## Examples

### Example 1: Device Discovery and Connection Test

**File**: `examples/01_device_discovery.py`

```python
#!/usr/bin/env python3
"""Test device discovery and connection."""
import asyncio
from hwh.tui.device_pool import DevicePool

async def main():
    pool = DevicePool()
    print("Scanning for devices...")
    devices = await pool.scan_devices()

    print(f"\nFound {len(devices)} device(s):")
    for dev_id in devices:
        device = pool.get_device(dev_id)
        print(f"  {dev_id}: {device.device_info.device_type}")
        print(f"    Port: {device.device_info.port}")
        print(f"    Capabilities: {device.device_info.capabilities}")

    print("\nTesting connections...")
    for dev_id in devices:
        if await pool.connect(dev_id):
            print(f"  ✓ {dev_id}")
        else:
            print(f"  ✗ {dev_id}")

    print("\nDevice Pool Status:")
    pool.display_status()

    await pool.disconnect_all()

if __name__ == '__main__':
    asyncio.run(main())
```

### Example 2: UART Auto-Interaction

**File**: `examples/02_uart_auto_interact.py`

```python
#!/usr/bin/env python3
"""Auto-interact with UART target."""
import asyncio
from hwh.tui.device_pool import DevicePool
from hwh.automation import UARTAutomation

async def main():
    pool = DevicePool()
    await pool.scan_devices()

    # Find UART device
    uart_devices = pool.get_devices_by_capability("uart")
    if not uart_devices:
        print("No UART device found")
        return

    device_id = uart_devices[0]
    await pool.connect(device_id)
    backend = pool.get_backend(device_id)

    # Auto-interact
    automation = UARTAutomation(backend)
    await automation.configure(baudrate=115200)

    print("Auto-interacting with target...")
    results = await automation.auto_interact()

    print(f"\nEnvironment: {results['detected_environment'].environment_type.name}")

    if results['login_success']:
        print("✓ Login successful")
        print("\nEnumeration results:")
        for cmd, output in results['enumeration'].items():
            print(f"  {cmd}: {output[:100]}...")

if __name__ == '__main__':
    asyncio.run(main())
```

### Example 3: STM32 RDP Bypass with Adaptive Workflow

**File**: `examples/03_stm32_rdp_bypass.py`

```python
#!/usr/bin/env python3
"""STM32 RDP bypass using adaptive glitch workflow."""
import asyncio
from hwh.tui.device_pool import DevicePool, DeviceRole
from hwh.workflows import create_adaptive_glitch_workflow
from hwh.glitch_profiles import TargetType

async def main():
    pool = DevicePool()
    await pool.scan_devices()

    # Setup devices
    glitchers = pool.get_devices_by_capability("voltage_glitch")
    monitors = pool.get_devices_by_capability("uart")

    if not glitchers or not monitors:
        print("ERROR: Need glitcher and UART monitor")
        return

    pool.assign_role(glitchers[0], DeviceRole.GLITCHER)
    pool.assign_role(monitors[0], DeviceRole.MONITOR)

    await pool.connect(glitchers[0])
    await pool.connect(monitors[0])

    print("Device pool ready:")
    pool.display_status()

    # Create adaptive workflow
    print("\nCreating adaptive glitch workflow...")
    workflow = create_adaptive_glitch_workflow(
        target_chip="STM32F103C8",
        attack_target=TargetType.RDP_BYPASS,
        success_patterns=[b'>>>', b'target halted'],
        try_known_params_first=True,
        coarse_sweep_enabled=True,
        fine_tune_enabled=True
    )

    print("Starting attack...")
    result = await workflow.run(pool)

    print(f"\n=== Attack Complete ===")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Successes: {result.results['success_count']}")
    print(f"Success rate: {result.results['success_rate'] * 100:.2f}%")

    if result.results['successes']:
        best = result.results['successes'][0]
        print(f"\nBest parameters:")
        print(f"  Width: {best['parameters']['width_ns']}ns")
        print(f"  Offset: {best['parameters']['offset_ns']}ns")

    await pool.disconnect_all()

if __name__ == '__main__':
    asyncio.run(main())
```

## Directory Structure

```
hwh/
├── __init__.py                    # Package exports
├── detect.py                      # USB/serial device detection
├── backends.py                    # Base classes + registry
├── backend_*.py                   # Device backends (buspirate, bolt, stlink, etc.)
│
├── tui/                          # Terminal UI and device management
│   ├── device_pool.py            # Multi-device coordination
│   └── app.py                    # Textual TUI (WIP)
│
├── automation/                   # Protocol automation
│   └── uart.py                   # UART intelligence
│
├── wrappers/                     # Device-specific high-level APIs
│   └── buspirate.py             # Bus Pirate 20-command wrapper
│
├── workflows/                    # Multi-device workflows
│   ├── base.py                  # Workflow base classes
│   ├── glitch_monitor.py        # Glitch + Monitor workflow
│   └── adaptive_glitch.py       # Profile-guided adaptive workflow
│
├── glitch_profiles.py           # Chip-specific attack database
├── GLITCH_PROFILES_GUIDE.md     # Profile usage guide
└── README.md                    # This file
```

## Troubleshooting

### Devices Not Detected

```bash
# Check USB permissions (Linux)
sudo usermod -a -G dialout $USER
# Log out and back in

# Check devices are visible
ls -la /dev/tty* | grep -i usb

# On macOS, devices appear as /dev/cu.usbmodem*
ls -la /dev/cu.usb*
```

### Import Errors

```bash
# Reinstall with dependencies
pip uninstall hwh
cd hwh && pip install -e .
pip install cobs flatbuffers textual

# Verify imports
python3 -c "from hwh import detect; print('OK')"
```

### Connection Failures

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Then run your script
```

### Bus Pirate Not Responding

- Try power cycling (unplug/replug USB)
- Check firmware version (`i` command in native terminal)
- Try different USB cable (data-capable, not charge-only)
- On Bus Pirate v6, BPIO2 port may differ from CDC port

## Development

### Running Tests

```bash
# Run basic connection tests
python3 examples/01_device_discovery.py

# Test UART automation
python3 examples/02_uart_auto_interact.py

# Test workflow (requires target hardware)
python3 examples/03_stm32_rdp_bypass.py
```

### Adding New Features

1. **New backend**: Extend `Backend` class in `backends.py`
2. **New workflow**: Extend `Workflow` class in `workflows/base.py`
3. **New profile**: Add to `glitch_profiles.py` with `register_profile()`
4. **New automation**: Add to `automation/` directory

## Documentation

- **Setup Guide**: [setup.md](../setup.md) - Hardware lab setup
- **Target Selection**: [targets-guide.md](../targets-guide.md) - Choosing practice devices
- **Glitch Profiles**: [GLITCH_PROFILES_GUIDE.md](GLITCH_PROFILES_GUIDE.md) - Profile database usage
- **Phase 1 Summary**: [PHASE1_IMPLEMENTATION.md](PHASE1_IMPLEMENTATION.md) - Implementation details
- **Attack Patterns**: [attack-patterns/](../attack-patterns/) - Vulnerability patterns

## Supported Hardware

| Device | SPI | I2C | UART | JTAG | SWD | Glitch | Power Analysis | Status |
|--------|-----|-----|------|------|-----|--------|---------------|--------|
| ST-Link V2/V3 | - | - | - | ✅ | ✅ | - | - | Working |
| Black Magic Probe | - | - | ✅ | ✅ | ✅ | - | - | Working |
| Bus Pirate v5/v6 | ✅ | ✅ | ✅ | ✅ | - | - | - | Working |
| Tigard | ✅ | ✅ | ✅ | ✅ | ✅ | - | - | Working |
| Curious Bolt | - | - | - | - | - | ✅ | ✅ | Working |
| FaultyCat v2.1 | - | - | - | Detect | Detect | ✅ | - | Partial |

## Contributing

Contributions welcome! Areas of interest:

- New glitch profiles from your research/CTFs
- Additional device backends
- Workflow improvements
- TUI completion
- Documentation and examples

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Credits

- **Glitch profiles**: From ECSC23, Riscure, ChipWhisperer, LimitedResults, and community
- **Hardware tools**: Bus Pirate (DangerousPrototypes), Curious Bolt (Bolt-Labs), ST-Link (STMicroelectronics)
- **Research**: Multiple security researchers and CTF writeups

---

**Status**: Phase 1 complete (66%) - Device pool, UART automation, workflows, and glitch profiles working. TUI and persistence pending.

*For educational and authorized security testing only.*
