# Known Issues and Limitations

This document tracks known issues, limitations, and required fixes for the hwh package.

## Critical Issues

### 1. Bus Pirate BPIO2 Implementation Incomplete

**Status:** STUB - Non-functional
**Affected:** `backend_buspirate.py`
**Impact:** Bus Pirate backend cannot communicate with hardware

**Description:**
The Bus Pirate 5/6 uses the BPIO2 FlatBuffers protocol over COBS-encoded serial. The current implementation has placeholder/stub methods that do not actually communicate with the hardware.

**Required:**
- Implement FlatBuffers serialization/deserialization
- Add BPIO2 protocol state machine
- Implement proper StatusRequest/StatusResponse
- Implement ConfigurationRequest for mode changes
- Implement DataRequest for bus transactions

**Workaround:**
Use Tigard for SPI/I2C operations, or use Bus Pirate via its terminal interface separately.

**References:**
- BPIO2 Protocol: https://docs.buspirate.com/docs/binmode-reference/protocol-bpio2/
- FlatBuffers: https://google.github.io/flatbuffers/
- Bus Pirate firmware: https://github.com/DangerousPrototypes/BusPirate5-firmware

**Estimated Effort:** 2-3 days for basic implementation

---

### 2. Multi-Port Device Detection

**Status:** PARTIAL - May connect to wrong port
**Affected:** `backend_buspirate.py`, `backend_tigard.py`, `backend_blackmagic.py`
**Impact:** May connect to console port instead of data port

**Description:**
Devices with multiple USB serial ports (Bus Pirate, Tigard FT2232H, Black Magic Probe) expose 2+ ports:
- **Bus Pirate:** Port 0 = Console, Port 1 = BPIO2 binary interface
- **Tigard:** Channel A = UART, Channel B = MPSSE (SPI/I2C)
- **Black Magic Probe:** Port 0 = GDB server, Port 1 = UART passthrough

Currently, detection may return the first port found, which might be the wrong one.

**Fix Required:**
- Enumerate all ports for a device by USB path
- Select correct port based on device type and use case
- Store both ports in DeviceInfo for multi-function access

**Workaround:**
Manually specify correct port in DeviceInfo before creating backend.

---

## Missing Features

### 3. FaultyCat Backend Not Implemented

**Status:** PLANNED - Not started
**Affected:** Missing `backend_faultycat.py`
**Impact:** Cannot use FaultyCat hardware

**Description:**
Electronic Cats FaultyCat (EMFI + glitching) support is planned but not implemented.

**Requirements:**
- Implement GlitchBackend interface
- EMFI pulse control
- Voltage glitching
- SWD/JTAG pin detection (JTAGulator-like)

**References:**
- FaultyCat repo: https://github.com/ElectronicCats/faultycat

---

### 4. TUI Not Implemented

**Status:** PLANNED - In TODO list
**Affected:** No TUI module
**Impact:** CLI-only interface

**Description:**
Terminal UI using `textual` library for interactive device control is planned.

**Proposed Features:**
- Device list with live status
- Protocol configuration panels
- Real-time data display
- Glitch campaign monitoring

---

### 5. Protocol Auto-Detection Missing

**Status:** PLANNED
**Affected:** All BusBackend implementations
**Impact:** Must manually specify protocol

**Description:**
Would be useful to auto-detect SPI flash chips, I2C devices, etc.

---

### 6. JTAG/SWD Pin Finder Not Implemented

**Status:** PLANNED
**Affected:** Debug backends
**Impact:** Must know pin locations

**Description:**
JTAGulator-style pin finding for unknown targets would be valuable.

---

## Test Coverage

### 7. No Integration Tests

**Status:** MINIMAL - Unit tests only
**Affected:** All backends
**Impact:** No hardware validation

**Description:**
Current tests are unit tests with mocks. No integration tests with actual hardware.

**Recommendations:**
- Add hardware-in-the-loop tests (optional, marked with pytest.mark.hardware)
- Mock backend tests for protocol logic
- CLI command tests

---

## Design Decisions and Limitations

### 8. Single Protocol Mode (Bus Pirate)

**Description:**
Bus Pirate can only be in one protocol mode at a time. Switching requires reconfiguration.

**Expected Behavior:**
Calling `configure_spi()` will disable I2C/UART if previously configured.

---

### 9. No Async Support

**Description:**
All operations are synchronous/blocking. Long operations (flash dumps, glitch sweeps) will block.

**Future Enhancement:**
Consider async/await API for concurrent operations.

---

### 10. Tigard JTAG/SWD Requires OpenOCD

**Description:**
Tigard debug operations require external OpenOCD process. Not integrated into backend.

**Workaround:**
Run OpenOCD separately: `openocd -f tigard-jtag.cfg`

**Future Enhancement:**
Integrate OpenOCD subprocess management into TigardDebugBackend.

---

## Fixed Issues

### ✅ Missing Abstract Methods in Base Classes

**Fixed:** 2026-01-17
**PR/Commit:** [pending]

Added missing abstract methods:
- `BusBackend.spi_flash_read_id()`
- `BusBackend.spi_flash_read()`
- `BusBackend.i2c_scan()`
- `DebugBackend.dump_firmware()`
- `GlitchBackend.run_glitch_sweep()` (concrete method with default impl)

---

### ✅ Duplicate VID:PID Entries in Detection

**Fixed:** 2026-01-17
**PR/Commit:** [pending]

Fixed duplicate dictionary entries for RP2040 devices (0x2E8A:0x000A).
Now correctly marks as `rp2040_unknown` requiring runtime identification.

---

## Contributing

When adding to this document:
1. Use clear status markers (CRITICAL, PLANNED, PARTIAL, etc.)
2. Include affected files
3. Describe user impact
4. Provide workarounds if available
5. Link to relevant documentation/issues
6. Move to "Fixed Issues" when resolved

Last updated: 2026-01-17
