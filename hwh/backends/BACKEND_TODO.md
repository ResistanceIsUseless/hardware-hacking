# hwh Backend Implementation Todo List

## Overview

This document tracks the implementation status and remaining work for all hwh device backends.

## Existing Backends - Completion Status

### BusPirateBackend (`backend_buspirate.py`) - ~70% Complete

**Working:**
- [x] SPI configuration and transfers
- [x] I2C configuration and scan
- [x] UART configuration
- [x] ADC voltage reading
- [x] PWM configuration
- [x] Power supply control

**Needs Implementation:**
- [ ] Flash chip operations (read_flash_id, dump_flash, erase_flash, write_flash) - Currently stubs
- [ ] Logic analyzer capture - Currently stub
- [ ] JTAG/SWD pin scanning - Not implemented
- [ ] Frequency counter - Not implemented
- [ ] Binary mode protocol - Currently uses text mode, BPIO2 would be more reliable

### BoltBackend (`backend_bolt.py`) - ~60% Complete

**Working:**
- [x] Glitch configuration (length, repeat, delay)
- [x] Arm/disarm/trigger
- [x] Trigger channel configuration
- [x] Native `scope` library integration

**Needs Implementation:**
- [ ] Serial fallback - All methods are stubs (returns fake data)
- [ ] Power analysis/ADC capture - Not implemented
- [ ] Logic analyzer - Not implemented
- [ ] GPIO control - Not implemented
- [ ] Conditions monitoring - Not implemented
- [ ] Glitch parameter sweep automation - Not implemented

### TigardBackend (`backend_tigard.py`) - ~40% Complete

**Working:**
- [x] Basic pyftdi integration
- [x] SPI configuration and transfers
- [x] I2C configuration and scan
- [x] UART configuration

**Needs Implementation:**
- [ ] Flash operations - Stubs only
- [ ] OpenOCD integration for JTAG - Stubs only
- [ ] OpenOCD integration for SWD - Stubs only
- [ ] Target detection - Not implemented
- [ ] Memory read/write via debug - Stubs only

---

## Missing Backends - Need Creation

### FaultyCatBackend - 0% (Needs Creation)

**File:** `hwh/backends/backend_faultycat.py`

**Required methods:**
- [ ] `connect()` / `disconnect()` - Serial connection to Arduino Micro
- [ ] `arm()` / `disarm()` - Safety controls
- [ ] `configure_pulse(duration, power)` - EMFI pulse settings
- [ ] `trigger()` - Fire the pulse
- [ ] `detect_pins()` - SWD/JTAG pin detection mode
- [ ] `get_status()` - Armed/safe state

**Dependencies to research:**
- FaultyCat firmware protocol (likely custom serial protocol)
- Arduino serial communication at appropriate baud rate

### TILinkBackend - 0% (Needs Creation)

**File:** `hwh/backends/backend_tilink.py`

**Required methods (wrapping mspdebug):**
- [ ] `connect()` - Launch mspdebug with tilib driver
- [ ] `disconnect()` - Clean shutdown
- [ ] `erase()` - Mass erase
- [ ] `program(firmware_path)` - Flash firmware
- [ ] `verify(firmware_path)` - Verify flash contents
- [ ] `read_memory(address, size)` - Memory dump
- [ ] `write_memory(address, data)` - Memory write
- [ ] `reset()` - Target reset
- [ ] `run()` / `halt()` - Execution control
- [ ] `set_breakpoint(address)` - Debug breakpoints
- [ ] `backchannel_uart_read()` - BSL UART
- [ ] `get_device_info()` - Detect MSP430/MSP432 variant

**Dependencies:**
- mspdebug installed and in PATH
- libmsp430.so/dylib (TI's proprietary driver)

### BlackMagicBackend - 0% (Needs Creation)

**File:** `hwh/backends/backend_blackmagic.py`

**Required methods:**
- [ ] `connect()` - Open GDB port
- [ ] `disconnect()` - Close connection
- [ ] `scan_targets()` - `monitor swdp_scan` / `monitor jtag_scan`
- [ ] `attach(target_num)` - Attach to detected target
- [ ] `detach()` - Detach from target
- [ ] `halt()` / `continue_()` / `step()` - Execution control
- [ ] `read_registers()` - Get register values
- [ ] `read_memory(address, size)` - Memory read
- [ ] `write_memory(address, data)` - Memory write
- [ ] `flash(firmware_path)` - Program via GDB load
- [ ] `reset()` - Target reset

**Implementation approach:**
- Use pygdbmi (GDB Machine Interface) library
- Or direct GDB remote serial protocol over the BMP's serial port

---

## Shared Infrastructure Needed

### Protocol Decoders

**File:** `hwh/backends/decoders.py`

- [ ] SPI decoder (for logic analyzer captures)
- [ ] I2C decoder
- [ ] UART decoder
- [ ] JTAG decoder (TMS/TCK/TDI/TDO state machine)
- [ ] SWD decoder

### Flash Chip Database

**File:** `hwh/backends/flash_db.py`

- [ ] JEDEC ID to chip info mapping
- [ ] Read/write/erase command sets per chip family
- [ ] Timing parameters
- [ ] Reference: flashrom's flashchips.c

### Common Utilities

**File:** `hwh/backends/utils.py`

- [ ] Hex dump formatting
- [ ] Binary file handling (ELF, Intel HEX, S-Record parsing)
- [ ] Address range validation
- [ ] Checksum calculations

---

## Testing Requirements

### Unit Tests

- [ ] `tests/backends/test_buspirate.py` - Mock serial, test command generation
- [ ] `tests/backends/test_bolt.py` - Mock scope library
- [ ] `tests/backends/test_tigard.py` - Mock pyftdi
- [ ] `tests/backends/test_faultycat.py`
- [ ] `tests/backends/test_tilink.py` - Mock subprocess for mspdebug
- [ ] `tests/backends/test_blackmagic.py` - Mock GDB responses

### Integration Tests (require hardware)

- [ ] `tests/integration/test_real_buspirate.py`
- [ ] `tests/integration/test_real_bolt.py`
- [ ] `tests/integration/test_real_tigard.py`
- [ ] `tests/integration/test_real_faultycat.py`
- [ ] `tests/integration/test_real_tilink.py`
- [ ] `tests/integration/test_real_blackmagic.py`

---

## Dependencies to Add

```toml
# pyproject.toml additions
[project.optional-dependencies]
all = [
    "pyserial>=3.5",        # Serial communication
    "pyftdi>=0.55.0",       # Tigard FTDI interface
    "pybpio>=0.1.0",        # Bus Pirate BPIO2 protocol
    "scope",                # Curious Bolt native library
    "pygdbmi>=0.11.0",      # GDB Machine Interface (for Black Magic)
    "intelhex>=2.3.0",      # Intel HEX file parsing
]
```

---

## Priority Order (Recommended)

1. **Complete BoltBackend serial fallback** - Most users won't have `scope` library
2. **Complete BusPirateBackend flash operations** - Common use case
3. **Create FaultyCatBackend** - Relatively simple serial protocol
4. **Create BlackMagicBackend** - pygdbmi makes this straightforward
5. **Complete TigardBackend OpenOCD** - Complex but important
6. **Create TILinkBackend** - Niche but useful if you have the hardware
7. **Add protocol decoders** - Nice to have for logic analyzer
8. **Flash chip database** - Can use flashrom's database as reference

---

## Notes

- All backends should fail gracefully when dependencies are missing
- Backends should provide clear error messages about what's needed
- Consider adding a `backend.capabilities` property to report what's actually working
- Serial fallback implementations should match native library behavior exactly
