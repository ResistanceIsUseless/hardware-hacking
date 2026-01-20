# Quick Start - hwh TUI

## What We Built

A **universal TUI** that works with Bus Pirate, Curious Bolt, FaultyCat, ST-Link, Tigard - all in one interface.

Based on excellent patterns from **glitch-o-bolt**, but generalized for ALL hardware tools.

## Launch the TUI

```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/hardware-hacking

# Using Python directly:
~/.pyenv/versions/3.12.10/bin/python3 -m hwh.cli tui

# Or if installed:
hwh tui
```

## What You'll See

```
┌─────────────────────────────────────────────────────┐
│  hwh - Universal Hardware Hacking Tool              │
├─────────────────────────────────────────────────────┤
│ Device: [Bus Pirate 6] [Curious Bolt] [ST-Link]    │
├───────────────┬─────────────────────────────────────┤
│ Device Info   │ ┌─────────────────────────────────┐ │
│               │ │ Console | SPI | I2C | Glitch    │ │
│ Name: Bolt    │ ├─────────────────────────────────┤ │
│ Port: /dev... │ │                                 │ │
│ Type: bolt    │ │  [Selected tab shows controls]  │ │
│               │ │                                 │ │
│ [Connect]     │ │                                 │ │
│ [Disconnect]  │ │                                 │ │
└───────────────┴─────────────────────────────────────┘
```

## Available Tabs (Adapts to Your Hardware)

### Console Tab (Always Available)
- Serial output monitoring
- Command input
- Real-time logging

### SPI Tab (Bus Pirate, Tigard, Shikra)
```
┌─ SPI Configuration ─────────┐
│ Speed: [1000000] Hz         │
│ Mode: [0] (0-3)             │
│ Bits/Word: [8]              │
│ [Configure SPI]             │
├─ Operations ────────────────┤
│ [Read Flash ID]             │
│ [Dump Flash]                │
│ [Erase Sector]              │
│ [Write Flash]               │
└─────────────────────────────┘
```

### I2C Tab (Bus Pirate, Tigard)
```
┌─ I2C Configuration ─────────┐
│ Speed: [100000] Hz          │
│ Address Bits: [7] (7/10)    │
│ [Configure I2C]             │
├─ Operations ────────────────┤
│ [Scan Bus]                  │
│ Address: [0x50]             │
│ [Read Byte]                 │
│ [Write Byte]                │
└─────────────────────────────┘
```

### UART Tab (Bus Pirate, Bolt, FaultyCat)
```
┌─ UART Configuration ────────┐
│ Baud: [115200]              │
│ Data Bits: [8]              │
│ Parity: [N] (N/E/O)         │
│ Stop Bits: [1]              │
│ [Configure UART]            │
├─ Operations ────────────────┤
│ [Enable RX Monitor]         │
│ TX: [Data to send...]       │
│ [Send]                      │
└─────────────────────────────┘
```

### Glitch Tab (Curious Bolt, FaultyCat)
```
┌─ Glitch Parameters ─────────┐
│ Width: [350] ns             │
│ Offset: [0] ns              │
│ Repeat: [1] times           │
│ [Configure Glitch]          │
├─ Operations ────────────────┤
│ [Single Glitch]             │
│ [ ] Continuous Glitching    │
├─ Parameter Sweep ───────────┤
│ Width Min: [50] ns          │
│ Width Max: [1000] ns        │
│ Width Step: [50] ns         │
│ [Start Sweep]               │
└─────────────────────────────┘
```

### Debug Tab (ST-Link, Black Magic Probe)
```
┌─ Debug Configuration ───────┐
│ [Connect Target]            │
│ [Reset Target]              │
│ [Halt Target]               │
│ [Resume Target]             │
├─ Memory Operations ─────────┤
│ Address: [0x08000000]       │
│ Size: [0x1000] bytes        │
│ [Read Memory]               │
│ [Write Memory]              │
│ [Dump Firmware]             │
└─────────────────────────────┘
```

## Key Features

### 1. Device Switching
Click device buttons at top to switch between connected tools **without restarting**.

### 2. Adaptive Interface
Only shows tabs your current device supports. No clutter!

### 3. Real-Time Monitoring
Console tab shows serial output in real-time.

### 4. Interactive Controls
- Click buttons to execute operations
- Type in inputs to set parameters
- Toggle switches for continuous operations

## CLI Commands (Without TUI)

```bash
# Detect devices
hwh detect

# Single glitch
hwh glitch single -w 350 -o 0

# Parameter sweep
hwh glitch sweep --width-min 50 --width-max 1000 --width-step 50

# Run automated campaign
hwh glitch campaign configs/challenge2.py

# SPI operations
hwh spi dump -o firmware.bin -a 0x0 -s 0x100000

# I2C scan
hwh i2c scan

# Interactive Python shell
hwh shell
```

## Condition-Based Automation

Create a config file:

```python
# my_campaign.py
SERIAL_PORT = '/dev/cu.usbserial-110'
BAUD_RATE = 115200

REPEAT = 42  # ~350ns glitch
DELAY = 0

triggers = [['-', False]] * 8

conditions = [
    ["Flag", True, "ctf{", "stop_on_flag"],
    ["Start", True, "Hold one", "start_glitch"],
]

def stop_on_flag():
    print("Flag captured!")
    # Stop glitching

def start_glitch():
    print("Starting glitch campaign")
    # Trigger glitcher
```

Run it:
```bash
hwh glitch campaign my_campaign.py
```

**What happens:**
1. Monitors serial output
2. When "Hold one" appears → calls `start_glitch()`
3. When "ctf{" appears → calls `stop_on_flag()`
4. Fully automated. Walk away. Get flag. ✨

## Module Usage (Python)

```python
from hwh import detect, get_backend
from hwh.tui import ConditionMonitor, GlitchCampaign, load_config_file

# Detect hardware
devices = detect()
bolt = get_backend(devices['bolt'])

# Load config
config = load_config_file('my_campaign.py')

# Run campaign
campaign = GlitchCampaign(bolt, config, log_callback=print)
stats = await campaign.run()

print(f"Sent {stats.glitches_sent} glitches")
```

## Directory Structure

```
hwh/
├── tui/
│   ├── app.py           # Universal TUI ✅
│   ├── conditions.py    # Pattern matching ✅
│   ├── config.py        # Config system ✅
│   └── campaign.py      # Campaign engine ✅
├── cli.py               # Commands ✅
├── backends.py          # Backend registry
├── backend_bolt.py      # Curious Bolt
├── backend_buspirate.py # Bus Pirate
└── detect.py            # Device detection
```

## Testing Checklist

### ✅ Software Ready
- [x] TUI module loads
- [x] CLI commands work
- [x] Condition engine implemented
- [x] Config system works
- [x] Campaign engine ready

### ⏳ Hardware Testing Needed
- [ ] Connect Bus Pirate → Test SPI/I2C tabs
- [ ] Connect Curious Bolt → Test Glitch tab
- [ ] Connect ST-Link → Test Debug tab
- [ ] Test device switching in TUI
- [ ] Test config file loading
- [ ] Test automated campaigns

## Current Status

**Software:** ✅ Fully implemented and ready
**Hardware Testing:** ⏳ Waiting for device connection
**Documentation:** ✅ Complete

## What Makes This Awesome

### Before (Multiple Tools):
```bash
# Bus Pirate
screen /dev/ttyUSB0 115200
# (remember cryptic commands)
m      # Mode selection
4      # SPI
...

# Curious Bolt
python3
>>> from scope import Scope
>>> s = Scope()
>>> s.glitch.repeat = 42
>>> s.trigger()

# ST-Link
openocd -f stlink.cfg
# (remember OpenOCD commands)
```

### After (One Tool):
```bash
hwh tui

# Click device
# Click tab
# Click operation
# Done!
```

### Learning Curve:
- **Before:** Memorize commands for 5+ tools
- **After:** Learn one TUI interface

### Automation:
- **Before:** Write custom scripts for each tool
- **After:** Write one config file, works everywhere

## Next Steps

1. **Connect hardware**
2. **Test TUI:** `hwh tui`
3. **Try each tab** based on device capabilities
4. **Create first config** for your target
5. **Run automated campaign**
6. **Report what works/needs improvement**

## Credits

Design inspired by **glitch-o-bolt** by 0xRoM
Implemented as universal tool for all hardware

---

**Status:** Ready for hardware testing! 🚀

When you connect devices, just run `hwh tui` and start clicking! The interface adapts automatically.
