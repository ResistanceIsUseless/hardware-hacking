# Fixes Applied - 2026-01-17

This document summarizes the fixes applied to address code review findings.

## Critical Fixes Applied

### 1. ✅ Added Missing Abstract Methods to BusBackend

**File:** `hwh/backends.py`

**Changes:**
- Added `spi_flash_read_id()` - Read JEDEC ID from SPI flash
- Added `spi_flash_read(address, length)` - Read from SPI flash memory
- Added `i2c_scan(start_addr, end_addr)` - Scan I2C bus for devices

**Impact:** CLI commands now have guaranteed interface across all bus backends

---

### 2. ✅ Added Missing Abstract Methods to DebugBackend

**File:** `hwh/backends.py`

**Changes:**
- Added `dump_firmware(start_address, size, chunk_size)` - Dump firmware from target

**Impact:** CLI debug dump command will work consistently

---

### 3. ✅ Added Glitch Sweep to GlitchBackend

**File:** `hwh/backends.py`

**Changes:**
- Added `run_glitch_sweep()` as concrete method with default implementation
- Backends can override for device-specific optimizations

**Impact:** CLI glitch sweep command will work on all glitch backends

---

### 4. ✅ Fixed Duplicate VID:PID Entries

**File:** `hwh/detect.py`

**Changes:**
- Removed duplicate entries for RP2040 devices (0x2E8A:0x000A)
- All RP2040 devices now marked as `rp2040_unknown` pending runtime ID

**Impact:** Device detection will work correctly

---

### 5. ✅ Implemented Missing Methods in Bus Pirate Backend

**File:** `hwh/backend_buspirate.py`

**Changes:**
- Implemented `spi_flash_read_id()` - Sends 0x9F command via SPI
- Implemented `spi_flash_read()` - Sends 0x03 + address read command

**Impact:** Bus Pirate can now be used for basic SPI flash operations (once BPIO2 is implemented)

---

### 6. ✅ Created Test Suite

**Files Created:**
- `hwh/tests/__init__.py`
- `hwh/tests/conftest.py` - Pytest fixtures
- `hwh/tests/test_detect.py` - Device detection tests
- `hwh/tests/test_backends.py` - Backend system tests

**Test Coverage:**
- DeviceInfo creation and attributes
- Device deduplication logic
- Backend registration and retrieval
- Configuration dataclasses
- Context manager protocol
- Glitch sweep calculation
- Known device database

**Run tests with:**
```bash
cd hwh
pytest -v
```

---

### 7. ✅ Documented Known Issues

**File Created:** `hwh/KNOWN_ISSUES.md`

**Contents:**
- Bus Pirate BPIO2 incomplete implementation (CRITICAL)
- Multi-port device detection issues
- Missing features (FaultyCat, TUI, auto-detection)
- Test coverage gaps
- Design limitations

---

## Remaining Known Issues

### Bus Pirate BPIO2 Implementation

**Status:** STUB - Non-functional

The Bus Pirate backend has placeholder implementations. Full functionality requires:

1. FlatBuffers schema implementation
2. COBS encoding/decoding (already imported)
3. Protocol state machine
4. Proper request/response handling

**Estimated effort:** 2-3 days

**Test with your Bus Pirate:**
We can verify detection works, but protocol communication will need BPIO2 implementation.

---

### Multi-Port Device Port Selection

**Status:** May select wrong port

Devices with 2+ serial ports may connect to the wrong one:
- Bus Pirate: Need port 1 (BPIO2), not port 0 (console)
- Tigard: Need correct channel for operation
- Black Magic Probe: Need port 0 for GDB, port 1 for UART

**Fix required:** Enumerate all ports by USB path, select correct one

---

## Testing Recommendations

### With Bus Pirate Connected

1. **Detection Test:**
   ```bash
   python -m hwh.detect
   # Should show Bus Pirate with capabilities
   ```

2. **CLI Detection:**
   ```bash
   hwh detect
   # Should list Bus Pirate
   ```

3. **Backend Creation:**
   ```python
   from hwh import detect, get_backend
   devices = detect()
   if 'buspirate' in devices:
       bp = get_backend(devices['buspirate'])
       print(f"Created backend: {bp}")
   ```

4. **Connection Attempt:**
   ```python
   # Will fail with STUB message
   bp.connect()
   # Expected: "[BusPirate] STUB: _status_request - needs BPIO2 FlatBuffers tooling"
   ```

### Expected Behavior

- ✅ Detection should find the device
- ✅ VID:PID should be recognized
- ✅ Backend should be created
- ❌ Connection will show STUB message
- ❌ Protocol operations won't work (need BPIO2)

---

## Next Steps

### Priority 1: BPIO2 Implementation
1. Add FlatBuffers schema files
2. Implement serialization/deserialization
3. Implement protocol state machine
4. Test with real Bus Pirate

### Priority 2: Multi-Port Detection
1. Enumerate USB device paths
2. Match multiple ports to single device
3. Select correct port based on device type

### Priority 3: Integration Tests
1. Add `pytest.mark.hardware` for tests requiring devices
2. Create hardware test suite
3. Document test hardware requirements

---

## Files Modified

- `hwh/backends.py` - Added abstract methods
- `hwh/backend_buspirate.py` - Added SPI flash methods
- `hwh/detect.py` - Fixed duplicate VID:PID

## Files Created

- `hwh/tests/__init__.py`
- `hwh/tests/conftest.py`
- `hwh/tests/test_detect.py`
- `hwh/tests/test_backends.py`
- `hwh/KNOWN_ISSUES.md`
- `hwh/FIXES_APPLIED.md` (this file)

---

## Running Tests

```bash
# Install in dev mode
cd /path/to/hardware-hacking
pip install -e "hwh[dev]"

# Run all tests
cd hwh
pytest -v

# Run specific test file
pytest tests/test_detect.py -v

# Run with coverage
pytest --cov=hwh --cov-report=term-missing
```

## Verification Checklist

- [x] Abstract methods added to base classes
- [x] Duplicate VID:PID fixed
- [x] Bus Pirate methods implemented
- [x] Test suite created
- [x] Known issues documented
- [ ] BPIO2 implementation (future work)
- [ ] Multi-port detection fix (future work)
- [ ] Hardware integration tests (future work)

Last updated: 2026-01-17
