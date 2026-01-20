# Bolt CTF Wiring Guide

## Quick Reference

**Connected Devices:**
- **Curious Bolt**: /dev/cu.usbmodem2103 (Glitcher + GPIO)
- **Bolt CTF**: /dev/cu.usbserial-110 (Serial output)
- **Bus Pirate**: /dev/cu.usbmodem6buspirate3 (Protocol testing - optional)

## Bolt CTF Pinout

The Bolt CTF board exposes these interfaces:

```
┌─────────────────────────────────┐
│  Curious Supplies Bolt CTF      │
├─────────────────────────────────┤
│                                 │
│  [GND] [TX ] [RX ]  ← UART      │
│  [GND] [SDA] [SCL]  ← I2C       │
│  [GND] [VMCU] [GND] ← Power     │
│  [SWCLK] [GND] [SWDIO] ← Debug  │
│                                 │
│  [BTN1] [BTN2] [BTN3] [BTN4]    │
│     ↑ Challenge Buttons         │
└─────────────────────────────────┘
```

**Button Functions:**
- BTN1: Challenge 1 (RAM Dump - no glitching)
- BTN2: Challenge 2 (Boolean Glitching)
- BTN3: Challenge 3 (I2C Corruption)
- BTN4: Challenge 4 (Code Execution)

## Challenge 1 Setup (RAM Dumping - Start Here!)

**Tools Needed:**
- ST-Link V2 (or any SWD debugger)
- PyOCD installed (`pip install pyocd`)

**Wiring:**
```
ST-Link → Bolt CTF:
  SWDIO  → SWDIO
  SWCLK  → SWCLK
  GND    → GND
  3.3V   → VMCU
```

**Visual Diagram:**
```
┌──────────┐              ┌─────────────┐
│ ST-Link  │              │  Bolt CTF   │
│          │              │             │
│  SWDIO ──┼──────────────┼─→ SWDIO    │
│  SWCLK ──┼──────────────┼─→ SWCLK    │
│  GND   ──┼──────────────┼─→ GND      │
│  3.3V  ──┼──────────────┼─→ VMCU     │
│          │              │             │
│          │              │  [Press    │
│          │              │   BTN1]    │
└──────────┘              └─────────────┘
```

**No glitching needed for Challenge 1!** This is a pure memory dump.

## Challenge 2 Setup (Power Glitching)

**Tools Needed:**
- Curious Bolt (for glitching)
- USB-to-serial adapter (for monitoring)

**Wiring Option 1 (Using glitch-o-bolt GPIO auto-trigger):**
```
Curious Bolt → Bolt CTF:
  GLITCH_OUT → VMCU (cut trace, insert glitcher!)
  GPIO 0     → BTN2 (auto-press button)
  GND        → GND

USB-Serial → Bolt CTF:
  RX → TX
  GND → GND
```

**Visual Diagram (Power Path):**
```
┌──────────────┐         ┌─────────────┐
│ Curious Bolt │         │  Bolt CTF   │
│              │         │             │
│ GLITCH_OUT ──┼────┬────┼─→ VMCU     │
│              │    │    │             │
│              │   [X]   │ ← Insert    │
│              │    │    │   glitcher  │
│              │    └────┼─  here      │
│ GPIO 0 ──────┼─────────┼─→ BTN2     │
│ GND ─────────┼─────────┼─→ GND      │
└──────────────┘         └─────────────┘

Note: For best results, insert GLITCH_OUT
between power source and VMCU pin.
```

**Wiring Option 2 (Manual button press):**
```
Curious Bolt → Bolt CTF:
  GLITCH_OUT → VMCU (insert in power path)
  GND        → GND

Serial Monitor → Bolt CTF:
  RX → TX
  GND → GND
```

**Power Path Details:**

The glitcher needs to be **in series** with the power rail:

```
Power Source → GLITCH_OUT → VMCU Pin → Target MCU
```

When triggered, Curious Bolt pulls GLITCH_OUT to ground for ~8.3ns × repeat cycles.

**Best Practice:**
1. Cut the trace between power source and VMCU
2. Connect power source to one side
3. Connect GLITCH_OUT to VMCU pin
4. This gives clean glitch without backfeeding

## Challenge 3 Setup (I2C Glitching)

**Similar to Challenge 2, but:**
- Use GPIO to auto-trigger BTN3
- May need I2C monitoring on SDA/SCL

**Wiring:**
```
Curious Bolt → Bolt CTF:
  GLITCH_OUT → VMCU (power glitch)
  GPIO 0     → BTN3
  GND        → GND

Optional - Bus Pirate → Bolt CTF (I2C monitoring):
  IO1 → SDA
  IO2 → SCL
  GND → GND
```

## Challenge 4 Setup (Code Execution)

**Same as Challenge 3, but different GPIO:**
```
Curious Bolt → Bolt CTF:
  GLITCH_OUT → VMCU
  GPIO 0     → BTN4
  GND        → GND
```

## Using glitch-o-bolt

The glitch-o-bolt tool automates everything!

**Run Challenge 2:**
```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh/tooling/glitch-o-bolt
python3 glitch-o-bolt.py -c ConfigChall02.py
```

**What it does automatically:**
1. Monitors serial output for "Hold one of the 4 challenge buttons"
2. Triggers GPIO 0 to press BTN2
3. Starts glitching campaign
4. Detects "ctf" flag in output
5. Stops glitching and displays flag

**You just watch the magic happen!**

## Serial Monitoring

The Bolt CTF outputs serial data on:
- **Device**: /dev/cu.usbserial-110
- **Baud**: 115200
- **Format**: 8N1

**Monitor with tio:**
```bash
tio /dev/cu.usbserial-110
```

**Or with screen:**
```bash
screen /dev/cu.usbserial-110 115200
```

## Curious Bolt GPIO Pinout

```
┌─────────────────────────────────┐
│     Curious Bolt (Top View)     │
├─────────────────────────────────┤
│                                 │
│  [0] [1] [2] [3] [4] [5] [6] [7]│
│   ↑ GPIO Pins (8 total)         │
│                                 │
│  [GLITCH_OUT]  ← Crowbar output │
│  [GND] [3.3V]  ← Power          │
│                                 │
│  USB-C ───────                  │
└─────────────────────────────────┘
```

**GPIO Capabilities:**
- Input: Read trigger signals
- Output: Control external devices (button press, etc.)
- Pull-up/Pull-down: Set with triggers in config

## Power Glitch Insertion Methods

### Method 1: Direct VMCU Connection (Easiest)

```
Power Source (3.3V) → GLITCH_OUT → VMCU Pin
```

**Pros:**
- Simple wiring
- Works for most cases

**Cons:**
- May have backfeeding from USB power

### Method 2: Cut Trace (Best Results)

```
1. Find power trace on PCB
2. Cut trace with knife
3. Solder GLITCH_OUT to target side
4. Solder power source to source side
```

**Pros:**
- Clean power isolation
- Best glitch results

**Cons:**
- Requires PCB modification
- Harder to reverse

### Method 3: Power Jack Insertion

If target has external power jack:
```
External PSU → GLITCH_OUT → Power Jack → Target
```

**Pros:**
- No PCB modification
- Easy to remove

**Cons:**
- Only works if target has power jack

## Glitch Parameter Reference

**Key Parameters:**
- **length**: Placeholder (not used in Bolt)
- **repeat**: Glitch width in 8.3ns cycles
- **delay/ext_offset**: Delay after trigger in 8.3ns cycles

**Example Values:**
```python
REPEAT = 42    # ~350ns glitch
DELAY = 0      # No delay after trigger
```

**Finding Parameters:**
- Start with repeat = 10-100
- Use ConfigGlitchBrute.py for automated sweep
- Look for target crash/reset/unexpected behavior

## Safety Notes

⚠️ **Important:**
- Bolt CTF runs on 3.3V - do NOT apply 5V!
- Glitching can damage hardware - use at your own risk
- Start with short glitches (repeat < 100)
- Monitor current draw - high current = possible damage

## Troubleshooting

**No serial output from Bolt CTF:**
- Check /dev/cu.usbserial-110 exists
- Try unplugging/replugging USB
- Verify baud rate is 115200

**Glitcher not working:**
- Check Curious Bolt detected: `ls /dev/cu.usbmodem*`
- Run `python3 -c "from scope import Scope; s = Scope(); print('OK')"
- Verify GLITCH_OUT connected to power rail

**GPIO trigger not working:**
- Check GPIO wiring
- Verify config has correct pin number
- Test with manual button press first

**ST-Link not detected:**
- Run `pyocd list` to see connected debuggers
- May need udev rules on Linux
- macOS usually works out of box

## Next Steps

1. **Start with Challenge 1** - No glitching, pure debugging practice
2. **Move to Challenge 2** - Learn power glitching basics
3. **Use glitch-o-bolt** - Automate the process
4. **Experiment with parameters** - Learn what works

Good luck! 🔥
