# Curious Bolt CTF - Quick Start Guide

## ✅ Setup Complete!

Your devices are detected and ready:
- ✅ **Curious Bolt Glitcher** - Connected, library installed (v0.0.1)
- ✅ **Bolt CTF Board** - Transmitting on `/dev/cu.usbserial-110`
- ✅ **Bus Pirate 6** - For power monitoring

---

## 🎯 Challenge Overview

Your Bolt CTF has **4 progressive challenges**:

| Challenge | Difficulty | Technique | Equipment Needed |
|-----------|-----------|-----------|------------------|
| **1. RAM Dump** | ⭐ Easy | SWD debugging | ST-Link |
| **2. Boolean Glitch** | ⭐⭐ Medium | Power glitching | Curious Bolt |
| **3. I2C Corruption** | ⭐⭐⭐ Hard | I2C line glitching | Curious Bolt + Logic Analyzer |
| **4. Code Execution** | ⭐⭐⭐⭐ Expert | Firmware extraction + patching | ST-Link + Curious Bolt |

---

## 🚀 Start with Challenge 1 (Easiest)

### Wiring for Challenge 1:
```
ST-Link → Bolt CTF
─────────────────────
SWDIO   →  SWDIO
SWCLK   →  SWCLK
GND     →  GND
3.3V    →  VCC
```

### Run Challenge 1:
```bash
cd "/Users/matthew/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking"
~/.pyenv/versions/3.12.10/bin/python3 challenge1_ram_dump.py
```

**Steps:**
1. Press button 1 on Bolt CTF
2. Enter bootloader mode (hold BOOT, press RESET)
3. Script uses PyOCD to dump RAM
4. Flag extracted automatically

**No glitching required!** This is pure debugging.

---

## ⚡ Challenge 2: Power Glitching

### Wiring for Challenge 2:
```
Curious Bolt → Bolt CTF
───────────────────────────────────────
GLITCH_OUT   →  VCC (insert in power path!)
GND          →  GND
TRIGGER      →  Optional (for timing)

Bus Pirate (monitoring):
────────────────────────
PSU          →  Bolt CTF VCC
GND          →  Bolt CTF GND
```

**Important:** GLITCH_OUT must be **in series** with power supply to pull voltage low.

### Run Challenge 2:
```bash
~/.pyenv/versions/3.12.10/bin/python3 challenge2_glitching.py
```

**What it does:**
1. Configures glitch parameters
2. Tests single glitch
3. Runs automated parameter sweep
4. Monitors serial output for flag

---

## 🔌 Wiring Diagrams

### Challenge 1: SWD Debugging
```
    ST-Link                 Bolt CTF
   ┌─────────┐              ┌──────────┐
   │ SWDIO   ├──────────────┤ SWDIO    │
   │ SWCLK   ├──────────────┤ SWCLK    │
   │ GND     ├──────────────┤ GND      │
   │ 3.3V    ├──────────────┤ VCC      │
   └─────────┘              └──────────┘
```

### Challenge 2: Power Glitching
```
    Curious Bolt            Bolt CTF
   ┌──────────────┐         ┌──────────┐
   │              │         │          │
   │  GLITCH_OUT  ├─────────┤ VCC      │
   │              │  (crowbar attack)  │
   │  GND         ├─────────┤ GND      │
   └──────────────┘         └──────────┘

    Bus Pirate (monitoring)
   ┌──────────┐
   │ PSU      ├──────┐
   │ GND      ├──┐   │
   └──────────┘  │   │
                 │   └──→ Bolt CTF VCC (measure current)
                 └──────→ Bolt CTF GND
```

---

## 🧪 Testing Your Setup

### Test 1: Check Curious Bolt
```python
from scope import Scope
s = Scope()
print(f"Bolt connected: {s}")

# Test glitch config
s.glitch.repeat = 60
s.glitch.ext_offset = 0
print("Config set successfully!")

# Manual trigger
s.trigger()
print("Glitch triggered!")
```

### Test 2: Monitor Serial Output
```python
import serial
ser = serial.Serial('/dev/cu.usbserial-110', 115200)
data = ser.read(100)
print(data.decode('ascii'))
# Should see: "Hold one of the 4 challenge buttons to start them"
```

### Test 3: Check Bus Pirate
```python
from hwh import detect, get_backend

bp = get_backend(detect()['buspirate'])
with bp:
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
    info = bp.get_info()
    print(f"Current draw: {info['psu_measured_ma']}mA")
```

---

## 📚 Complete Documentation

- **Full Guide:** `BOLT_CTF_GUIDE.md` - All 4 challenges with detailed walkthroughs
- **Pinout Reference:** `PINOUT_GUIDE.md` - All device pin mappings
- **Wiring Diagrams:** `WIRING_DIAGRAMS.txt` - ASCII art diagrams

---

## 🛠️ Command Reference

### PyOCD (for Challenge 1):
```bash
# Interactive commander
pyocd commander

# In commander:
>>> savemem 0x20000000 20480 dump.bin
>>> exit

# Extract flag
strings dump.bin | grep ctf
```

### Curious Bolt Glitching:
```python
from scope import Scope

s = Scope()

# Configure glitch
s.glitch.repeat = 60      # Width in 8.3ns cycles
s.glitch.ext_offset = 0   # Delay in 8.3ns cycles

# Manual trigger
s.trigger()

# Armed trigger (waits for external signal)
s.arm(channel=0, edge=Scope.RISING_EDGE)
```

### Serial Monitoring:
```bash
# Using screen
screen /dev/cu.usbserial-110 115200

# Using Python
python3 -c "
import serial
ser = serial.Serial('/dev/cu.usbserial-110', 115200)
while True:
    print(ser.read(100).decode('ascii', errors='ignore'))
"
```

---

## ⚠️ Troubleshooting

### "No flag found" in Challenge 1
- Make sure you pressed button 1 first
- Verify you entered bootloader mode correctly
- Check ST-Link connection with `pyocd list`
- RAM address may vary: try `strings dump.bin | less`

### "No glitch effect" in Challenge 2
- Verify GLITCH_OUT is in power path
- Try holding button 2 during glitching
- Check glitch appears on oscilloscope
- Increase glitch width: `s.glitch.repeat = 100`

### "Device not found"
```bash
# Check connections
ls /dev/cu.usb*

# Curious Bolt should be: /dev/cu.usbmodem2103
# Bolt CTF serial: /dev/cu.usbserial-110
# Bus Pirate: /dev/cu.usbmodem6buspirate3

# Verify with detection
python3 -c "from hwh import detect; print(detect())"
```

---

## 🎯 Recommended Order

**Week 1:**
1. ✅ Setup complete (you are here!)
2. Challenge 1: RAM dump (1-2 hours)
3. Study Challenge 2 walkthrough

**Week 2:**
4. Challenge 2: Power glitching (4-8 hours of parameter tuning)
5. Learn logic analyzer with PulseView

**Week 3:**
6. Challenge 3: I2C corruption (advanced)
7. Challenge 4: Firmware patching (expert)

---

## 🔗 Resources

- **Official Docs:** https://bolt.curious.supplies/docs/
- **GitHub:** https://github.com/tjclement/bolt
- **Walkthrough:** https://rossmarks.uk/blog/curious-bolt-ctf-level-1/
- **CTF Solutions:** https://github.com/kxynos/cs-bolt-p-glitching

---

## 🏁 Ready to Start!

**Option 1: Challenge 1 (Recommended for beginners)**
```bash
python3 challenge1_ram_dump.py
```

**Option 2: Challenge 2 (If you want glitching action)**
```bash
python3 challenge2_glitching.py
```

**Option 3: Manual exploration**
- Press buttons 1-4 on Bolt CTF to see different challenges
- Monitor serial output to see what each challenge does
- Read the detailed guide: `BOLT_CTF_GUIDE.md`

---

**Good luck and have fun! 🎉**
