#!/usr/bin/env python3
"""
Test script for Bus Pirate BPIO2 implementation.

This script tests the Bus Pirate backend with a real Bus Pirate 5/6 device.
Connect your Bus Pirate before running.

Usage:
    python test_buspirate.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import hwh
sys.path.insert(0, str(Path(__file__).parent.parent))

from hwh import detect, get_backend
from hwh.backends import SPIConfig, I2CConfig


def test_detection():
    """Test device detection."""
    print("=" * 60)
    print("TEST 1: Device Detection")
    print("=" * 60)

    devices = detect()

    if 'buspirate' not in devices:
        print("❌ Bus Pirate not detected")
        print(f"Found devices: {list(devices.keys())}")
        return None

    print(f"✅ Bus Pirate detected: {devices['buspirate'].name}")
    print(f"   Port: {devices['buspirate'].port}")
    print(f"   VID:PID: {devices['buspirate'].vid:04x}:{devices['buspirate'].pid:04x}")
    print(f"   Capabilities: {', '.join(devices['buspirate'].capabilities)}")

    return devices['buspirate']


def test_connection(device):
    """Test backend connection."""
    print("\n" + "=" * 60)
    print("TEST 2: Backend Connection")
    print("=" * 60)

    backend = get_backend(device)
    if not backend:
        print("❌ Failed to create backend")
        return None

    print(f"✅ Backend created: {backend.__class__.__name__}")

    if not backend.connect():
        print("❌ Failed to connect to Bus Pirate")
        return None

    print("✅ Connected to Bus Pirate")

    return backend


def test_status_request(backend):
    """Test status request."""
    print("\n" + "=" * 60)
    print("TEST 3: Status Request")
    print("=" * 60)

    info = backend.get_info()
    if not info:
        print("❌ Failed to get status")
        return False

    print("✅ Status received:")

    if 'version' in info:
        ver = info['version']
        print(f"   Firmware: v{ver.get('firmware_major', 0)}.{ver.get('firmware_minor', 0)}")
        print(f"   Hardware: v{ver.get('hardware_major', 0)}.{ver.get('hardware_minor', 0)}")
        if 'git_hash' in ver:
            print(f"   Git hash: {ver['git_hash']}")
        if 'date' in ver:
            print(f"   Date: {ver['date']}")

    if 'mode' in info:
        print(f"   Current mode: {info['mode']}")

    if 'modes_available' in info:
        print(f"   Available modes: {', '.join(info['modes_available'])}")

    if 'psu' in info:
        psu = info['psu']
        print(f"   PSU: {'Enabled' if psu.get('enabled') else 'Disabled'}")
        if psu.get('enabled'):
            print(f"   PSU voltage: {psu.get('set_mv', 0)}mV (measured: {psu.get('measured_mv', 0)}mV)")
            print(f"   PSU current: {psu.get('set_ma', 0)}mA (measured: {psu.get('measured_ma', 0)}mA)")

    return True


def test_spi_configuration(backend):
    """Test SPI configuration."""
    print("\n" + "=" * 60)
    print("TEST 4: SPI Configuration")
    print("=" * 60)

    spi_config = SPIConfig(
        speed_hz=1_000_000,
        mode=0,  # CPOL=0, CPHA=0
        bits_per_word=8
    )

    print(f"Configuring SPI: {spi_config.speed_hz}Hz, mode={spi_config.mode}")

    if not backend.configure_spi(spi_config):
        print("❌ Failed to configure SPI")
        return False

    print("✅ SPI configured successfully")

    return True


def test_spi_flash_id(backend):
    """Test reading SPI flash ID (if flash chip connected)."""
    print("\n" + "=" * 60)
    print("TEST 5: SPI Flash ID (Optional)")
    print("=" * 60)

    print("Attempting to read SPI flash ID (0x9F command)...")
    print("Note: This requires an SPI flash chip connected to the Bus Pirate")

    try:
        flash_id = backend.spi_flash_read_id()

        if flash_id and len(flash_id) >= 3:
            print(f"✅ Flash ID: {flash_id.hex()}")
            print(f"   Manufacturer: 0x{flash_id[0]:02x}")
            print(f"   Device: 0x{flash_id[1]:02x}{flash_id[2]:02x}")

            # Decode common manufacturers
            manufacturers = {
                0xEF: "Winbond",
                0xC2: "Macronix",
                0x20: "Micron",
                0x01: "Spansion",
                0xBF: "SST",
            }
            if flash_id[0] in manufacturers:
                print(f"   ({manufacturers[flash_id[0]]})")

            return True
        else:
            print("⚠️  No flash chip detected or invalid response")
            print("   This is expected if no SPI flash is connected")
            return True  # Not a failure

    except Exception as e:
        print(f"⚠️  Flash ID read error: {e}")
        print("   This is expected if no SPI flash is connected")
        return True  # Not a failure


def test_i2c_configuration(backend):
    """Test I2C configuration."""
    print("\n" + "=" * 60)
    print("TEST 6: I2C Configuration")
    print("=" * 60)

    i2c_config = I2CConfig(
        speed_hz=400_000,  # 400kHz standard mode
        address_bits=7
    )

    print(f"Configuring I2C: {i2c_config.speed_hz}Hz")

    if not backend.configure_i2c(i2c_config):
        print("❌ Failed to configure I2C")
        return False

    print("✅ I2C configured successfully")

    return True


def main():
    """Main test function."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Bus Pirate BPIO2 Implementation Test" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Test 1: Detection
    device = test_detection()
    if not device:
        print("\n❌ FAILED: Device detection")
        return 1

    # Test 2: Connection
    backend = test_connection(device)
    if not backend:
        print("\n❌ FAILED: Backend connection")
        return 1

    try:
        # Test 3: Status Request
        if not test_status_request(backend):
            print("\n❌ FAILED: Status request")
            return 1

        # Test 4: SPI Configuration
        if not test_spi_configuration(backend):
            print("\n❌ FAILED: SPI configuration")
            return 1

        # Test 5: SPI Flash ID (optional)
        test_spi_flash_id(backend)

        # Test 6: I2C Configuration
        if not test_i2c_configuration(backend):
            print("\n❌ FAILED: I2C configuration")
            return 1

        # All tests passed
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("The Bus Pirate BPIO2 implementation is working correctly.")
        print()

        return 0

    finally:
        # Cleanup
        backend.disconnect()
        print("\nDisconnected from Bus Pirate")


if __name__ == '__main__':
    sys.exit(main())
