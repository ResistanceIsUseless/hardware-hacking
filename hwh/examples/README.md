# hwh Examples

Practical examples demonstrating hwh toolkit usage.

## Running Examples

Examples must be run from the parent directory (hardware-hacking/):

```bash
cd /path/to/hardware-hacking
python3 hwh/examples/01_device_discovery.py
```

Or add the parent to PYTHONPATH:

```bash
export PYTHONPATH=/path/to/hardware-hacking:$PYTHONPATH
python3 hwh/examples/01_device_discovery.py
```

## Example 1: Device Discovery

**File**: `01_device_discovery.py`

Tests basic device detection and connection.

```bash
python3 hwh/examples/01_device_discovery.py
```

**What it does**:
- Scans for connected hardware
- Tests connection to each device
- Displays device pool status

**Requirements**: Any supported hardware device connected

## Example 2: UART Auto-Interaction

**File**: `02_uart_auto_interact.py`

Demonstrates intelligent UART automation.

```bash
python3 hwh/examples/02_uart_auto_interact.py
```

**What it does**:
- Finds UART-capable device
- Auto-detects environment (shell/login/bootloader)
- Tries common credentials
- Runs enumeration commands
- Captures and displays results

**Requirements**:
- UART-capable device (Bus Pirate, Tigard, etc.)
- Target device with UART output
- Target powered on

**Wiring**:
```
Bus Pirate → Target:
    MISO → TX (target's UART TX)
    GND  → GND
```

## Example 3: STM32 RDP Bypass

**File**: `03_stm32_rdp_bypass.py`

Full adaptive glitch attack workflow.

```bash
python3 hwh/examples/03_stm32_rdp_bypass.py
```

**What it does**:
- Coordinates glitcher + UART monitor
- Uses glitch profile database
- Three-phase adaptive search
- Records successful parameters
- Builds success map

**Requirements**:
- Curious Bolt (glitcher)
- Bus Pirate or Tigard (monitor)
- STM32F103 target device
- Proper wiring

**Wiring**:
```
Bolt → Target:
    VCC     → VCC (power injection)
    TRIGGER → RESET
    GND     → GND

Bus Pirate → Target:
    MISO → TX (UART TX)
    GND  → GND
```

**⚠️ WARNING**: Only test on devices you own. Unauthorized testing is illegal.

## Troubleshooting

### ModuleNotFoundError: No module named 'hwh'

Run from parent directory:
```bash
cd /path/to/hardware-hacking
python3 hwh/examples/01_device_discovery.py
```

### No devices found

- Check USB connections
- Verify devices are powered
- Check USB permissions (Linux: `sudo usermod -a -G dialout $USER`)
- Check device visibility: `ls /dev/cu.usb*` (macOS) or `ls /dev/ttyUSB*` (Linux)

### Connection failures

- Try unplugging/replugging device
- Check USB cable (must be data-capable, not charge-only)
- Enable debug logging in the script
- Check for other software accessing the device

### UART no output

- Verify baudrate (try 9600, 19200, 38400, 57600, 115200)
- Check wiring (TX→RX connection)
- Verify target is outputting data
- Try pressing reset on target while monitoring

## Next Steps

After running these examples:

1. **Modify for your hardware**: Adjust chip names, success patterns
2. **Add custom profiles**: Document parameters you discover
3. **Build workflows**: Combine components for your attacks
4. **Contribute back**: Submit profiles and improvements

See [../README.md](../README.md) for full documentation.
