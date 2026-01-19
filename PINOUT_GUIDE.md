# Hardware Connection Pinout Guide

Complete wiring guide for Bus Pirate, Curious Bolt, and Bolt CTF connections.

---

## Bus Pirate 6 Pinout

### Physical Connector
The Bus Pirate 6 has a 10-pin header. Pin numbers are logical (software), physical pins vary.

### Pin Assignments by Mode

#### Common Pins (All Modes)
```
Pin 0  → OFF/ON    (Power sense/enable)
Pin 9  → GND       (Ground - ALWAYS CONNECT THIS!)
PSU    → VPU       (Programmable power supply output, 0-5V)
```

#### I2C Mode
```
Pin 1  → SDA       (I2C Data line, needs pull-up)
Pin 2  → SCL       (I2C Clock line, needs pull-up)
Pin 9  → GND
```

#### SPI Mode
```
Pin 5  → MISO      (Master In, Slave Out)
Pin 6  → CS        (Chip Select)
Pin 7  → CLK       (Clock)
Pin 8  → MOSI      (Master Out, Slave In)
Pin 9  → GND
```

#### UART Mode (When Firmware Supports)
```
Pin 3  → TX        (Transmit from Bus Pirate)
Pin 5  → RX        (Receive to Bus Pirate)
Pin 9  → GND
```

Note: UART pin numbers may vary. Check with `info.get('mode_pin_labels')` after configuring.

---

## Bolt CTF (STM32-based Device)

### Common STM32 Interfaces

#### SWD (Serial Wire Debug) - For Programming
**Use ST-Link for this, not Bus Pirate!**
```
SWDIO  → Data I/O
SWCLK  → Clock
GND    → Ground
VCC    → 3.3V
NRST   → Reset (optional)
```

#### UART (Serial Communication)
```
TX (PA9 or PA2)   → Transmit from Bolt CTF
RX (PA10 or PA3)  → Receive to Bolt CTF
GND               → Ground
VCC (optional)    → 3.3V power
```

Common STM32 UART pins:
- USART1: PA9 (TX), PA10 (RX)
- USART2: PA2 (TX), PA3 (RX)
- USART3: PB10 (TX), PB11 (RX)

#### I2C (Two-Wire Communication)
```
SDA (PB7 or PB9)  → Data line
SCL (PB6 or PB8)  → Clock line
GND               → Ground
VCC (optional)    → 3.3V power
```

Common STM32 I2C pins:
- I2C1: PB6 (SCL), PB7 (SDA)
- I2C1 alt: PB8 (SCL), PB9 (SDA)
- I2C2: PB10 (SCL), PB11 (SDA)

#### SPI (Serial Peripheral Interface)
```
MOSI (PA7 or PB5) → Master Out Slave In
MISO (PA6 or PB4) → Master In Slave Out
SCK  (PA5 or PB3) → Clock
NSS  (PA4 or PA15)→ Chip Select
GND               → Ground
VCC (optional)    → 3.3V power
```

Common STM32 SPI pins:
- SPI1: PA5 (SCK), PA6 (MISO), PA7 (MOSI), PA4 (NSS)
- SPI1 alt: PB3 (SCK), PB4 (MISO), PB5 (MOSI), PA15 (NSS)

---

## Connection Scenarios

### Scenario 1: Bus Pirate → Bolt CTF (I2C)

**Current Setup (Based on Tests):**
```
Bus Pirate          Bolt CTF STM32
──────────────────────────────────────
Pin 1 (SDA)    →    SDA (PB7 or PB9)
Pin 2 (SCL)    →    SCL (PB6 or PB8)
Pin 9 (GND)    →    GND
PSU (3.3V)     →    VCC/3V3

⚠️  Enable pull-ups on Bus Pirate!
```

**Status:** ⚠️ SDA stuck LOW (Bolt CTF needs SWD programming first)

**Python Code:**
```python
from hwh import detect, get_backend
from hwh.backends import I2CConfig

bp = get_backend(list(detect().values())[0])
with bp:
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
    bp.set_pullups(enabled=True)  # CRITICAL for I2C!
    bp.configure_i2c(I2CConfig(speed_hz=100_000))
    devices = bp.i2c_scan(start_addr=0x08, end_addr=0x77)
    print(f"Found: {[hex(addr) for addr in devices]}")
```

---

### Scenario 2: Bus Pirate → Bolt CTF (UART)

**Recommended Wiring (UART cross-over):**
```
Bus Pirate          Bolt CTF STM32
──────────────────────────────────────
Pin 3 (TX)     →    RX (PA10 or PA3)
Pin 5 (RX)     →    TX (PA9 or PA2)
Pin 9 (GND)    →    GND
PSU (3.3V)     →    VCC/3V3 (optional if separately powered)

Note: TX connects to RX and vice versa!
```

**Status:** ⚠️ Bus Pirate firmware v0.0 doesn't support UART mode yet

**Python Code (When Working):**
```python
from hwh import detect, get_backend
from hwh.backends import UARTConfig

bp = get_backend(list(detect().values())[0])
with bp:
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
    bp.configure_uart(UARTConfig(baudrate=115200, data_bits=8, parity='N', stop_bits=1))

    # Send data
    bp.uart_write(b"Hello from Bus Pirate!\r\n")

    # Read response
    data = bp.uart_read(100)
    print(f"Received: {data}")
```

---

### Scenario 3: Bus Pirate → Bolt CTF (SPI)

**Wiring for SPI Flash or SPI Peripheral:**
```
Bus Pirate          Bolt CTF STM32
──────────────────────────────────────
Pin 5 (MISO)   →    MISO (PA6 or PB4)
Pin 6 (CS)     →    NSS  (PA4 or PA15)
Pin 7 (CLK)    →    SCK  (PA5 or PB3)
Pin 8 (MOSI)   →    MOSI (PA7 or PB5)
Pin 9 (GND)    →    GND
PSU (3.3V)     →    VCC/3V3 (optional)
```

**Status:** ✅ SPI working, but no flash detected on Bolt CTF

**Python Code:**
```python
from hwh import detect, get_backend
from hwh.backends import SPIConfig

bp = get_backend(list(detect().values())[0])
with bp:
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
    bp.configure_spi(SPIConfig(speed_hz=1_000_000, mode=0))

    # Read flash ID
    flash_id = bp.spi_flash_read_id()
    print(f"Flash ID: {flash_id.hex()}")
```

---

### Scenario 4: Curious Bolt → Bolt CTF (Glitching)

**Typical Glitching Setup:**
```
Curious Bolt        Bolt CTF STM32
──────────────────────────────────────
GLITCH_OUT     →    VCC (power rail to glitch)
TRIGGER_IN     ←    GPIO (trigger signal from target)
GND            →    GND

Logic Analyzer Channels (if using):
CH0            →    UART TX (PA9)
CH1            →    UART RX (PA10)
CH2            →    SWD CLK
CH3            →    SWD IO
CH4-7          →    Other signals of interest
GND            →    GND
```

**Notes:**
- Glitch output targets the power rail (VCC)
- May need to insert between power source and target
- Trigger can be from any GPIO that indicates operation start
- Logic analyzer captures digital signals for timing analysis

**Backend:** ⏳ Coming soon (Curious Bolt backend pending)

---

### Scenario 5: Bus Pirate → Bolt CTF (Power + Multi-Protocol)

**Maximum Monitoring Setup:**
```
Bus Pirate          Bolt CTF STM32
──────────────────────────────────────
Pin 1 (SDA)    →    SDA (I2C data)
Pin 2 (SCL)    →    SCL (I2C clock)
Pin 3 (TX)     →    RX  (UART receive)
Pin 5 (RX)     →    TX  (UART transmit)
Pin 9 (GND)    →    GND
PSU (3.3V)     →    VCC/3V3 (power supply)

Note: Can only use one protocol at a time!
Switch modes with configure_i2c() or configure_uart()
```

**Use Case:** Quick protocol switching without rewiring

---

## Curious Bolt Pinout (Estimated)

**Based on typical RP2040-based glitching tools:**

### Power and Ground
```
VCC   → 3.3V or 5V input
GND   → Ground
VOUT  → Regulated output for target
```

### Glitching
```
GLITCH_OUT  → Voltage glitch output (connects to target VCC)
GLITCH_EN   → Enable glitch
ARM         → Arm glitch trigger
```

### Trigger
```
TRIG_IN     → External trigger input
TRIG_OUT    → Trigger output signal
```

### Logic Analyzer (8 channels typical)
```
CH0-CH7     → Digital input channels (0-3.3V)
GND         → Ground (share with target)
```

### Communication
```
TX    → Serial transmit
RX    → Serial receive
SDA   → I2C data (if supported)
SCL   → I2C clock (if supported)
```

**Note:** Exact pinout depends on Curious Bolt documentation. Check the device manual or silk screen labels.

---

## Recommended Test Sequence

### Step 1: Power Test
```
Bus Pirate PSU  →  Bolt CTF VCC
Bus Pirate GND  →  Bolt CTF GND
```

Power on, measure current draw (should be 15-25mA for STM32).

### Step 2: I2C Test
Add I2C connections (SDA, SCL), enable pull-ups, scan bus.

### Step 3: SPI Test
Switch to SPI mode, try reading flash ID.

### Step 4: UART Test (when firmware supports)
Add UART connections, test serial communication.

### Step 5: Multi-Device Coordination
Add Curious Bolt for glitching while Bus Pirate monitors.

---

## Common Issues & Solutions

### Issue: I2C SDA Stuck LOW
**Symptoms:** SDA reads 17-19mV, no devices found
**Causes:**
- Target device pulling SDA low (common with unprogrammed STM32)
- Faulty wiring
- Wrong I2C pins

**Solutions:**
1. Program target via SWD first (use ST-Link)
2. Verify wiring (SDA → SDA, SCL → SCL, not swapped)
3. Check pull-ups are enabled
4. Try different I2C pins (PB6/PB7 vs PB8/PB9)

### Issue: No SPI Flash Detected
**Symptoms:** Flash ID returns 0x000000 or 0xFFFFFF
**Causes:**
- No external SPI flash on device
- Wrong SPI pins
- Clock too fast
- Incorrect SPI mode

**Solutions:**
1. Confirm device has external flash (may be internal only)
2. Try lower speeds (100kHz, 400kHz)
3. Try different SPI modes (0-3)
4. Check wiring carefully

### Issue: UART No Response
**Symptoms:** Can send but no data received
**Causes:**
- TX/RX not crossed over (TX → TX won't work!)
- Wrong baud rate
- Target not transmitting
- Firmware doesn't support UART mode

**Solutions:**
1. Verify crossover: Bus Pirate TX → Target RX
2. Try common baud rates: 9600, 38400, 115200
3. Check target firmware is running and using UART
4. For Bus Pirate v0.0: Wait for firmware update

---

## Voltage Levels

### Bus Pirate
- **Logic levels:** 3.3V (not 5V tolerant!)
- **PSU output:** 0-5V programmable
- **Current limit:** Up to 500mA (set lower for safety)
- **Input protection:** Some, but avoid overvoltage

### STM32 (Bolt CTF)
- **Logic levels:** 3.3V
- **5V tolerant pins:** Many, but check datasheet
- **Power supply:** 2.0V - 3.6V typical
- **Current consumption:** ~15-25mA typical

### Safety
- ⚠️ Always connect GND first!
- ⚠️ Set PSU current limit before enabling
- ⚠️ Verify voltage before connecting
- ⚠️ Don't exceed 3.3V on Bus Pirate pins
- ⚠️ Use external power for high-current targets

---

## Quick Reference Commands

### Check Current Wiring
```python
from hwh import detect, get_backend

bp = get_backend(list(detect().values())[0])
with bp:
    info = bp.get_info()
    voltages = info['adc_mv']
    labels = info['mode_pin_labels']

    for label, voltage in zip(labels, voltages):
        if label:
            status = "HIGH" if voltage > 2000 else "LOW"
            print(f"{label}: {voltage}mV [{status}]")
```

### Auto-Scan Target
```python
from hwh import detect, get_backend

bp = get_backend(list(detect().values())[0])
with bp:
    results = bp.scan_target(power_voltage_mv=3300, power_current_ma=100)
    print(f"Current: {results['psu']['measured_current_ma']}mA")
    print(f"I2C devices: {results['i2c_devices']}")
    print(f"SPI flash: {results['spi_flash']['detected']}")
```

---

## Next Steps

1. **Verify your current wiring** - Run pin voltage check
2. **Try I2C scan** - See if SDA issue persists
3. **If I2C doesn't work** - Consider UART or SPI instead
4. **For full I2C support** - Program Bolt CTF via ST-Link/SWD
5. **Add Curious Bolt** - For coordinated glitching attacks

---

**Need help?** Run the diagnostic script:
```bash
python3 test_all_functionality.py
```

This will test all interfaces and show current status!
