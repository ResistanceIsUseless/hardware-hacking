# What to Try Next - Connection Options

Based on your current setup and what we've learned, here are your best options:

---

## 🔥 **Option 1: Try UART (Recommended)**

**Why:** Most likely to work right now. No I2C issues, no flash required.

**Current Issue:** Bus Pirate firmware v0.0 doesn't support UART mode switching yet.

**What You Need:**
- 4 wires already connected: TX, RX, GND, VCC
- Bolt CTF must have UART enabled in its firmware

**Wiring (if not already connected):**
```
Bus Pirate          →    Bolt CTF
─────────────────────────────────
Pin 3 (TX)          →    RX (PA10 or PA3)
Pin 5 (RX)          →    TX (PA9 or PA2)
Pin 9 (GND)         →    GND
PSU (3.3V)          →    VCC/3V3
```

**When Firmware Supports It:**
```bash
python3 <<'EOF'
from hwh import detect, get_backend
from hwh.backends import UARTConfig

bp = get_backend(list(detect().values())[0])
with bp:
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
    bp.configure_uart(UARTConfig(baudrate=115200))
    bp.uart_write(b"Hello\r\n")
    data = bp.uart_read(100)
    print(f"Received: {data}")
EOF
```

---

## 🎯 **Option 2: Use Curious Bolt for UART**

**Why:** Curious Bolt is connected and responding. Use it as UART interface!

**Wiring:**
```
Curious Bolt        →    Bolt CTF
─────────────────────────────────
TX                  →    RX (PA10 or PA3)
RX                  →    TX (PA9 or PA2)
GND                 →    GND
```

**Test it now:**
```python
import serial
import time

# Connect to Curious Bolt port
ser = serial.Serial('/dev/cu.usbmodem2103', 115200, timeout=1)

# Try to send data through to Bolt CTF
ser.write(b"?\r\n")
time.sleep(0.5)

if ser.in_waiting:
    response = ser.read(ser.in_waiting)
    print(f"Response: {response}")

ser.close()
```

**Next Step:** Figure out Curious Bolt's command protocol for GPIO/UART passthrough

---

## 🔧 **Option 3: Keep Using I2C (Fix the Issue)**

**Current Status:**
- SDA stuck at 19mV (should be 3.3V)
- SCL working at 3272mV
- Bolt CTF pulling SDA LOW

**Solution: Program Bolt CTF via SWD**

**You Need:**
- ST-Link V2 or V3
- 5 wires: SWDIO, SWCLK, GND, VCC, NRST (optional)

**ST-Link → Bolt CTF Wiring:**
```
ST-Link             →    Bolt CTF
─────────────────────────────────
SWDIO               →    SWDIO
SWCLK               →    SWCLK
GND                 →    GND
3.3V                →    VCC
NRST (optional)     →    NRST
```

**Programming:**
```bash
# Using openocd
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg

# Or using st-flash
st-flash write firmware.bin 0x8000000

# Or using STM32CubeProgrammer (GUI)
```

**After Programming:**
Test I2C again - SDA should read 3.3V

---

## 🎲 **Option 4: Try SPI (Already Works!)**

**Current Status:** ✅ SPI working, but no flash detected

**Maybe Bolt CTF has:**
- Internal flash only (no external SPI flash)
- SPI peripheral for communication
- Different pins for SPI

**Wiring (if different from current):**
```
Bus Pirate          →    Bolt CTF
─────────────────────────────────
Pin 5 (MISO)        →    MISO (PA6 or PB4)
Pin 6 (CS)          →    NSS  (PA4 or PA15)
Pin 7 (CLK)         →    SCK  (PA5 or PB3)
Pin 8 (MOSI)        →    MOSI (PA7 or PB5)
Pin 9 (GND)         →    GND
PSU (3.3V)          →    VCC
```

**Test Custom SPI Commands:**
```python
from hwh import detect, get_backend
from hwh.backends import SPIConfig

bp = get_backend(list(detect().values())[0])
with bp:
    bp.configure_spi(SPIConfig(speed_hz=100_000, mode=0))  # Try slower

    # Try different commands
    commands = [0x9F, 0xAB, 0x90, 0x05]  # Common SPI commands

    for cmd in commands:
        result = bp.spi_transfer([cmd], read_len=4)
        print(f"Command 0x{cmd:02x}: {result.hex()}")
```

---

## 🚀 **Option 5: Coordinate Curious Bolt + Bus Pirate**

**Why:** Use both devices together for advanced testing

**Setup:**
- Bus Pirate: Powers Bolt CTF, monitors protocols
- Curious Bolt: Logic analyzer captures signals

**Wiring:**
```
Bus Pirate → Bolt CTF (Power + I2C/SPI/UART)
Curious Bolt → Bolt CTF (Logic Analyzer channels)
```

**Curious Bolt Logic Analyzer:**
```
Curious Bolt CH0    →    Bolt CTF TX (PA9)
Curious Bolt CH1    →    Bolt CTF RX (PA10)
Curious Bolt CH2    →    Bolt CTF SDA
Curious Bolt CH3    →    Bolt CTF SCL
Curious Bolt GND    →    Bolt CTF GND
```

**Use Case:**
- Bus Pirate sends I2C commands
- Curious Bolt captures timing on logic analyzer
- See exactly what's happening on the bus

---

## 🎯 **My Recommendation: Try This Order**

### 1. **Check Current Wiring**
Run this to see what you have now:
```bash
cd "/Users/matthew/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking"
~/.pyenv/versions/3.12.10/bin/python3 <<'EOF'
from hwh import detect, get_backend

bp = get_backend(list(detect().values())[0])
with bp:
    results = bp.scan_target()

    print("Current Status:")
    print(f"  Power: {results['psu']['measured_voltage_mv']}mV @ {results['psu']['measured_current_ma']}mA")

    print("\nPin Voltages:")
    for pin, voltage in results['pin_voltages'].items():
        if pin:
            status = "HIGH" if voltage > 2000 else "LOW"
            print(f"  {pin:8s}: {voltage:4d}mV  [{status}]")
EOF
```

### 2. **Try Curious Bolt Serial**
Since Curious Bolt responds, try using it:
```python
import serial
ser = serial.Serial('/dev/cu.usbmodem2103', 115200)
ser.write(b"help\r\n")
print(ser.read(100))
```

### 3. **Add UART Wires to Bolt CTF**
If you have spare wires, add TX/RX connections:
- Bolt CTF TX → Curious Bolt RX or Bus Pirate Pin 5
- Bolt CTF RX → Curious Bolt TX or Bus Pirate Pin 3

### 4. **Monitor Everything**
Run multi-device test to see all interactions:
```bash
python3 test_multi_device.py
```

### 5. **Get ST-Link** (If You Want Full I2C)
Program Bolt CTF properly to fix the I2C SDA issue

---

## 🔍 **Quick Diagnostics**

### Check if Bolt CTF is Running
Current draw tells you:
- **0-5mA:** Device off or in deep sleep
- **10-30mA:** ✅ Device running normally (YOUR STATUS)
- **50-100mA:** High activity or peripherals active
- **100+mA:** Something wrong or high-power peripheral

### Check Pin Voltages
Run this anytime:
```python
from hwh import detect, get_backend
bp = get_backend(list(detect().values())[0])
with bp:
    info = bp.get_info()
    for label, voltage in zip(info['mode_pin_labels'], info['adc_mv']):
        if label: print(f"{label}: {voltage}mV")
```

### Power Cycle Test
See if Bolt CTF transmits on power-up:
```python
from hwh import detect, get_backend
import time

bp = get_backend(list(detect().values())[0])
with bp:
    # Power cycle
    bp.set_psu(enabled=False)
    time.sleep(1)
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
    time.sleep(2)

    # Check if behavior changed
    info = bp.get_info()
    print(f"Current: {info['psu_measured_ma']}mA")
```

---

## 📚 **Documentation Reference**

- **Full Pinout Guide:** `PINOUT_GUIDE.md`
- **Visual Diagrams:** `WIRING_DIAGRAMS.txt`
- **Multi-Device Tests:** `MULTI_DEVICE_SUMMARY.md`
- **Quick Reference:** `QUICK_REFERENCE.md`

---

## ❓ **Questions to Answer**

1. **What pins are currently wired?**
   - Run scan_target() to see voltages

2. **What do you want to test?**
   - I2C → Need to fix SDA issue first
   - UART → Need Bus Pirate firmware update OR use Curious Bolt
   - SPI → Already works, try custom commands
   - Glitching → Need to implement Curious Bolt backend

3. **Do you have an ST-Link?**
   - Yes → Program Bolt CTF, fix I2C
   - No → Use UART/SPI/Curious Bolt instead

---

**My top recommendation:** Try using Curious Bolt for serial communication with Bolt CTF while you figure out its command protocol. Both devices are connected and working!
