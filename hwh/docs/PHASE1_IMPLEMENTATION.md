# hwh TUI Phase 1 Implementation Summary

**Status:** Core infrastructure complete (4/6 tasks)
**Date:** January 20, 2026

## Overview

Phase 1 has successfully built the foundational architecture for multi-device coordination, intelligent UART automation, Bus Pirate wrapper, and workflow engine. This provides a solid base for the enhanced TUI implementation.

## Completed Components

### 1. Device Pool Architecture ✅

**File:** [hwh/tui/device_pool.py](tui/device_pool.py)

Multi-device management and coordination system:

- **DevicePool class** - Manages multiple hardware devices simultaneously
- **Device role assignment** - Assign roles (PRIMARY, MONITOR, GLITCHER, FLASHER, etc.)
- **Smart device selection** - Auto-recommend devices based on task requirements
- **Async coordination** - Device locks and coordinated workflows
- **Health tracking** - Connection status, error counts, activity timestamps
- **Auto-detection integration** - Scans and adds devices to pool

**Key Features:**
```python
pool = DevicePool()
await pool.scan_devices()

# Auto-select best device for task
device_id = await pool.auto_select("glitch STM32")

# Get recommendations
recommendations = pool.recommend_for_task("dump SPI flash")

# Coordinate workflow across devices
await pool.coordinate(workflow, {
    DeviceRole.GLITCHER: "bolt",
    DeviceRole.MONITOR: "buspirate"
})
```

### 2. UART Automation Module ✅

**File:** [hwh/automation/uart.py](automation/uart.py)

Intelligent UART interaction with pattern detection:

- **Environment detection** - Identifies shells, login prompts, bootloaders, custom protocols
- **Pattern library** - Common regex patterns for Linux shells, U-Boot, login prompts
- **Auto-interaction** - Automatically tries common credentials, runs enumeration
- **Shell enumeration** - Safe, read-only commands for system information gathering
- **Bootloader interaction** - Probes bootloader commands (help, printenv, etc.)
- **Comprehensive logging** - All interactions logged for analysis

**Key Features:**
```python
automation = UARTAutomation(backend)
await automation.configure(baudrate=115200)

# Detect what we're talking to
detected = await automation.detect_environment()

if detected.is_login:
    # Try common credentials
    success = await automation.handle_login()

if detected.is_shell:
    # Enumerate system
    results = await automation.enumerate_shell()

# Or just do everything automatically
results = await automation.auto_interact()
```

**Detected Patterns:**
- Linux shell prompts (root@host#, user$, etc.)
- Login prompts (login:, password:, etc.)
- Bootloaders (U-Boot, custom boot menus)
- Boot sequences
- Custom protocols

**Default Credentials Tried:**
- root / (empty)
- root / root
- admin / admin
- user / user
- And more...

**Shell Commands Run:**
- `uname -a` - System info
- `cat /proc/cpuinfo` - CPU details
- `id` - Current user
- `ls -la /` - Root directory
- `mount` - Mounted filesystems
- `ifconfig -a` - Network interfaces
- And more...

### 3. Bus Pirate Wrapper ✅

**File:** [hwh/wrappers/buspirate.py](wrappers/buspirate.py)

High-level wrapper for 20 most-used Bus Pirate commands:

**Implemented Commands:**

1. **Voltage Measurement** - `measure_voltage()` - ADC voltage reading
2. **Power Supply Control** - `power_on()`, `power_off()` - PSU control
3. **Set Voltage** - `set_voltage(3.3/5.0)` - Configure PSU voltage
4. **Pull-up Resistors** - `pullups_on()`, `pullups_off()` - Control pull-ups
5. **Frequency Measurement** - `measure_frequency()` - Input frequency
6. **PWM Generation** - `pwm_start()`, `pwm_stop()` - Generate PWM signals
7. **SPI Quick Transfer** - `spi_quick_transfer()` - Quick SPI with defaults
8. **I2C Quick Scan** - `i2c_quick_scan()` - Fast I2C bus scan
9. **UART Quick Setup** - `uart_quick_setup(baudrate)` - Configure UART
10. **GPIO Control** - `pin_set_high()`, `pin_set_low()`, `pin_read()` - Pin I/O
11. **LED Control** - `led_on()`, `led_off()`, `led_flash()` - LED control
12. **Device Info** - `get_info()` - Version and hardware info
13. **Aux Pin** - `aux_high()`, `aux_low()` - AUX pin control
14. **SPI Flash ID** - `spi_flash_id()` - Quick JEDEC ID read
15. **I2C Single Byte** - `i2c_write_byte()`, `i2c_read_byte()` - Quick I2C
16. **Self-test** - `self_test()` - Device self-test
17. **Factory Reset** - `factory_reset()` - Reset to defaults
18. **Native Terminal** - `native_terminal()` - Drop to native mode (placeholder)

**Design Philosophy:**
- Wrap the most common operations for easy TUI access
- Keep interface simple and intuitive
- Provide `native_terminal()` escape hatch for advanced features
- Log all operations

### 4. Workflow Engine ✅

**Files:**
- [hwh/workflows/base.py](workflows/base.py) - Base workflow classes
- [hwh/workflows/glitch_monitor.py](workflows/glitch_monitor.py) - Example workflow

Multi-device workflow coordination framework:

**Base Classes:**

- **Workflow** - Abstract base for all workflows
  - Progress tracking (0-100%)
  - Status management (PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED)
  - Setup / Execute / Cleanup lifecycle
  - Cancellation support
  - Progress callbacks

- **ParameterSweepWorkflow** - Base for parameter sweeps
  - Iteration tracking
  - Success recording
  - Progress calculation

- **MonitoringMixin** - Background monitoring support
  - Async monitoring tasks
  - Pattern detection in captured data
  - Buffer management

**Example Workflow: Glitch + Monitor**

Coordinates Curious Bolt (glitcher) with Bus Pirate (UART monitor):

```python
from hwh.workflows import GlitchMonitorWorkflow, GlitchParameters, SuccessCriteria

# Define parameters
glitch_params = GlitchParameters(
    width_min=50,
    width_max=500,
    width_step=25,
    offset_min=1000,
    offset_max=10000,
    offset_step=500,
    attempts_per_setting=3
)

success_criteria = SuccessCriteria(
    patterns=[b'# ', b'root@', b'shell>'],
    timeout_ms=1000
)

# Create workflow
workflow = GlitchMonitorWorkflow(glitch_params, success_criteria)

# Run it
result = await workflow.run(device_pool)

print(f"Found {len(workflow.successes)} successful glitches!")
for success in workflow.successes:
    print(f"  Width: {success['parameters']['width_ns']}ns, "
          f"Offset: {success['parameters']['offset_ns']}ns")
```

**Features:**
- Auto-assigns device roles (GLITCHER, MONITOR)
- Sweeps glitch parameters (width, offset)
- Monitors UART for success patterns
- Records all successful combinations
- Progress tracking and cancellation support
- Cleanup and error handling

## Architecture Overview

```
hwh/
├── tui/
│   ├── device_pool.py          # NEW: Multi-device coordination
│   └── app.py                  # Existing TUI (to be enhanced)
│
├── automation/                 # NEW: Protocol automation
│   ├── __init__.py
│   └── uart.py                 # UART intelligence
│
├── wrappers/                   # NEW: Device-specific wrappers
│   ├── __init__.py
│   └── buspirate.py           # Bus Pirate 20-command wrapper
│
├── workflows/                  # NEW: Multi-device workflows
│   ├── __init__.py
│   ├── base.py                # Workflow base classes
│   └── glitch_monitor.py      # Glitch + Monitor example
│
├── backends.py                # Existing backend abstraction
├── detect.py                  # Existing device detection
├── backend_*.py               # Existing device backends
└── ...
```

## Integration with Existing Code

The new components integrate seamlessly:

1. **DevicePool** uses existing `detect.py` for device discovery
2. **DevicePool** uses existing `backends.py` for device communication
3. **UARTAutomation** uses existing `BusBackend` interface
4. **BusPirateWrapper** wraps existing `BusPirateBackend`
5. **Workflows** coordinate existing backends through DevicePool

## Remaining Phase 1 Tasks

### 5. Enhanced Textual TUI (Pending)

Updates needed to [hwh/tui/app.py](tui/app.py):

- Integrate DevicePool for multi-device display
- Add workflow selection screen
- Multi-device status dashboard
- Real-time monitoring displays
- UART automation controls
- Bus Pirate wrapper integration

### 6. Session Persistence (Pending)

Needs implementation:

- SQLite database for device configurations
- Workflow history tracking
- Session state save/restore
- Export/import via JSON

## Usage Examples

### Example 1: Auto-detect and Interact with UART

```python
from hwh.tui.device_pool import DevicePool
from hwh.automation import UARTAutomation

# Setup
pool = DevicePool()
await pool.scan_devices()

# Find UART-capable device
device_id = await pool.auto_select("UART monitoring")
backend = pool.get_backend(device_id)

# Auto-interact
automation = UARTAutomation(backend)
results = await automation.auto_interact()

if results['login_success']:
    print("Logged in!")
    print("Enumeration results:", results['enumeration'])
```

### Example 2: Coordinate Glitch Attack

```python
from hwh.tui.device_pool import DevicePool
from hwh.workflows import create_glitch_monitor_workflow

# Setup device pool
pool = DevicePool()
await pool.scan_devices()

# Assign roles
pool.assign_role("bolt", DeviceRole.GLITCHER)
pool.assign_role("buspirate", DeviceRole.MONITOR)

# Create workflow
workflow = create_glitch_monitor_workflow(
    width_range=(50, 500, 25),
    offset_range=(1000, 10000, 500),
    success_patterns=[b'# ', b'root@'],
    attempts_per_setting=5
)

# Run it
result = await workflow.run(pool)

print(f"Success rate: {result.results['success_rate'] * 100:.2f}%")
for success in result.results['successes']:
    print(f"  {success['parameters']}")
```

### Example 3: Bus Pirate Quick Operations

```python
from hwh.wrappers import BusPirateWrapper

wrapper = BusPirateWrapper(backend)

# Quick voltage check
voltage = wrapper.measure_voltage()
print(f"Voltage: {voltage.voltage}V")

# Quick I2C scan
devices = wrapper.i2c_quick_scan()
print(f"I2C devices: {[hex(a) for a in devices]}")

# Quick SPI flash ID
flash_id = wrapper.spi_flash_id()
print(f"Flash ID: {flash_id.hex()}")

# Enable power
wrapper.power_on(voltage=3.3)
```

## Testing Status

Phase 1 components are code-complete but require:

1. **Unit tests** - Test individual components in isolation
2. **Integration tests** - Test device pool + workflows
3. **Hardware testing** - Test with real devices (Bus Pirate, Bolt, etc.)
4. **Documentation** - API docs and usage guides

## Next Steps

1. **Finish TUI integration** - Update app.py to use new components
2. **Add persistence layer** - SQLite database for configurations
3. **Testing** - Write tests and test with hardware
4. **Documentation** - Complete API docs

## Files Added

- `hwh/tui/device_pool.py` (418 lines)
- `hwh/automation/__init__.py`
- `hwh/automation/uart.py` (532 lines)
- `hwh/wrappers/__init__.py`
- `hwh/wrappers/buspirate.py` (430 lines)
- `hwh/workflows/__init__.py`
- `hwh/workflows/base.py` (367 lines)
- `hwh/workflows/glitch_monitor.py` (318 lines)
- `hwh/todo.md` (task tracking)
- `hwh/PHASE1_IMPLEMENTATION.md` (this document)

**Total:** ~2,065 lines of new code

## Design Decisions Made

1. **Async-first architecture** - All coordination uses asyncio
2. **Role-based device management** - Devices have roles in workflows
3. **Smart recommendations** - System suggests best devices for tasks
4. **Pattern-based automation** - UART automation uses regex patterns
5. **Mixin-based workflows** - Composable workflow capabilities
6. **Wrapper approach for Bus Pirate** - 20 commands + native fallback
7. **Progress tracking** - All workflows provide progress callbacks
8. **Cancellation support** - User can cancel long-running workflows

---

**Phase 1 Status:** 66% complete (4/6 tasks done)
**Ready for:** Hardware testing and TUI integration

*Last Updated: 2026-01-20*
