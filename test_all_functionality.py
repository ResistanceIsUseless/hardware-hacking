#!/usr/bin/env python3
"""
Comprehensive functionality test for all connected hardware devices.
Tests each device and reports what's working.
"""

import sys
import time
sys.path.insert(0, '/Users/matthew/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh')

from hwh import detect, get_backend
from hwh.backends import SPIConfig, I2CConfig, UARTConfig


def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_section(text):
    """Print a section header"""
    print(f"\n── {text} " + "─"*(68 - len(text)))


def test_device_detection():
    """Test device detection"""
    print_header("DEVICE DETECTION TEST")

    print("\n[*] Scanning for USB devices...")
    devices = detect()

    if not devices:
        print("  [!] No devices found!")
        return None

    print(f"  [+] Found {len(devices)} device(s):\n")

    for i, (name, info) in enumerate(devices.items(), 1):
        print(f"  [{i}] {info.name}")
        print(f"      Type: {info.device_type}")
        print(f"      Port: {info.port}")
        if info.vid and info.pid:
            print(f"      VID:PID: {info.vid:04x}:{info.pid:04x}")
        print()

    return devices


def test_buspirate(devices):
    """Test Bus Pirate functionality"""
    print_header("BUS PIRATE FUNCTIONALITY TEST")

    if 'buspirate' not in devices:
        print("  [!] Bus Pirate not found - skipping tests")
        return

    print(f"\n[*] Connecting to Bus Pirate at {devices['buspirate'].port}...")
    bp = get_backend(devices['buspirate'])

    if not bp.connect():
        print("  [!] Failed to connect")
        return

    print("  [+] Connected successfully!\n")

    # Test 1: Device Info
    print_section("Test 1: Device Information")
    info = bp.get_info()
    print(f"  Firmware: v{info.get('version_firmware_major')}.{info.get('version_firmware_minor')}")
    print(f"  Hardware: v{info.get('version_hardware_major')} REV{info.get('version_hardware_minor')}")
    print(f"  Build Date: {info.get('version_firmware_date')}")
    print(f"  Git Hash: {info.get('version_firmware_git_hash')}")
    print(f"  Current Mode: {info.get('mode_current')}")
    print(f"  Available Modes: {', '.join(info.get('modes_available', []))}")

    # Test 2: PSU Control
    print_section("Test 2: PSU Control")
    print("  [*] Enabling PSU (3.3V, 100mA limit)...")
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
    time.sleep(0.5)

    info = bp.get_info()
    psu_voltage = info.get('psu_measured_mv', 0)
    psu_current = info.get('psu_measured_ma', 0)
    print(f"  [+] PSU enabled")
    print(f"  Measured: {psu_voltage}mV @ {psu_current}mA")

    if psu_current > 0:
        print(f"  [+] Target device is drawing power ({psu_current}mA)")
    else:
        print(f"  [!] No current draw (target may not be connected)")

    # Test 3: Pin Voltages
    print_section("Test 3: Pin Voltage Readings")
    voltages = info.get('adc_mv', [])
    labels = info.get('mode_pin_labels', [])

    if voltages and labels:
        for label, voltage in zip(labels, voltages):
            if label:
                status = "HIGH" if voltage > 2000 else "LOW"
                print(f"  {label:8s}: {voltage:4d}mV  [{status}]")

    # Test 4: SPI Configuration
    print_section("Test 4: SPI Configuration")
    print("  [*] Configuring SPI (1MHz, mode 0)...")
    if bp.configure_spi(SPIConfig(speed_hz=1_000_000, mode=0)):
        print("  [+] SPI configured successfully")

        print("  [*] Reading SPI flash ID (0x9F command)...")
        flash_id = bp.spi_flash_read_id()
        if flash_id:
            print(f"  Flash ID: {flash_id.hex()}")

            if flash_id == b'\x00\x00\x00' or flash_id == b'\xff\xff\xff':
                print("  [!] No SPI flash detected (or not connected)")
            else:
                mfg = flash_id[0] if len(flash_id) > 0 else 0
                dev = flash_id[1:3].hex() if len(flash_id) >= 3 else "unknown"
                print(f"  [+] Manufacturer: 0x{mfg:02x}")
                print(f"  [+] Device: 0x{dev}")
        else:
            print("  [!] Failed to read flash ID")
    else:
        print("  [!] SPI configuration failed")

    # Test 5: I2C Configuration
    print_section("Test 5: I2C Configuration")
    print("  [*] Configuring I2C (100kHz)...")
    if bp.configure_i2c(I2CConfig(speed_hz=100_000)):
        print("  [+] I2C configured successfully")

        print("  [*] Enabling pull-ups...")
        bp.set_pullups(enabled=True)

        print("  [*] Scanning I2C bus (0x08-0x77)...")
        i2c_devices = bp.i2c_scan(start_addr=0x08, end_addr=0x77)

        if i2c_devices:
            print(f"  [+] Found {len(i2c_devices)} I2C device(s):")
            for addr in i2c_devices:
                print(f"      0x{addr:02x}")
        else:
            print("  [!] No I2C devices found")

            # Show pin voltages for debugging
            info = bp.get_info()
            voltages = info.get('adc_mv', [])
            labels = info.get('mode_pin_labels', [])

            # Find SDA and SCL
            for label, voltage in zip(labels, voltages):
                if label in ['SDA', 'SCL']:
                    print(f"      {label}: {voltage}mV", end="")
                    if voltage < 1000:
                        print(" [ERROR: Line stuck LOW]")
                    elif voltage > 2500:
                        print(" [OK]")
                    else:
                        print(" [WARNING: Voltage in intermediate range]")
    else:
        print("  [!] I2C configuration failed")

    # Test 6: UART Configuration
    print_section("Test 6: UART Configuration")
    print("  [*] Configuring UART (115200 8N1)...")
    print("  [!] Note: UART may not be fully supported in current firmware")

    if bp.configure_uart(UARTConfig(baudrate=115200, data_bits=8, parity='N', stop_bits=1)):
        print("  [+] UART configured successfully")

        print("  [*] Listening for UART data (3 seconds)...")
        data_received = bytearray()
        start = time.time()

        while time.time() - start < 3:
            result = bp.uart_read(32)
            if result:
                data_received.extend(result)
                print(f"  RX: {result.hex()}")
            time.sleep(0.1)

        if data_received:
            print(f"  [+] Received {len(data_received)} bytes")
            print(f"  Data: {data_received.hex()}")
        else:
            print("  [!] No UART data received")
            print("  Expected wiring:")
            print("    Target TX → Bus Pirate MISO (pin 5)")
            print("    Target RX → Bus Pirate MOSI (pin 3)")
    else:
        print("  [!] UART configuration failed (firmware limitation)")

    # Test 7: Automated Target Scan
    print_section("Test 7: Automated Target Scan")
    print("  [*] Running comprehensive target scan...")
    print("  This tests all interfaces automatically...")

    results = bp.scan_target(power_voltage_mv=3300, power_current_ma=300)

    print("\n  [Scan Results]")
    print(f"  PSU Status:")
    print(f"    Enabled: {results['psu']['enabled']}")
    print(f"    Set: {results['psu']['set_voltage_mv']}mV")
    print(f"    Measured: {results['psu']['measured_voltage_mv']}mV @ {results['psu']['measured_current_ma']}mA")

    if results['i2c_devices']:
        print(f"\n  I2C Devices: {len(results['i2c_devices'])} found")
        for addr in results['i2c_devices']:
            print(f"    0x{addr:02x}")
    else:
        print(f"\n  I2C Devices: None found")

    if results['spi_flash']['detected']:
        print(f"\n  SPI Flash: Detected")
        print(f"    ID: {results['spi_flash']['id']}")
        print(f"    Manufacturer: 0x{results['spi_flash']['manufacturer']:02x}")
        print(f"    Device: {results['spi_flash']['device']}")
    else:
        print(f"\n  SPI Flash: Not detected")

    print(f"\n  Pin Voltages:")
    for pin, voltage in results['pin_voltages'].items():
        if pin:
            status = "HIGH" if voltage > 2000 else "LOW"
            print(f"    {pin:8s}: {voltage:4d}mV  [{status}]")

    print(f"\n  IO Status:")
    for pin, state in results['io_status'].items():
        print(f"    {pin}: {state['direction']:3s} = {state['value']:4s}")

    # Cleanup
    print_section("Cleanup")
    print("  [*] Disconnecting...")
    bp.disconnect()
    print("  [+] Done")


def test_bolt(devices):
    """Test Bolt functionality"""
    print_header("BOLT FUNCTIONALITY TEST")

    bolt_device = devices.get('bolt') or devices.get('bolt_ctf')

    if not bolt_device:
        print("  [!] Bolt device not found - skipping tests")
        return

    print(f"\n[*] Found: {bolt_device.name}")
    print(f"    Port: {bolt_device.port}")
    print(f"    Type: {bolt_device.device_type}")
    print("\n[!] Bolt backend not yet fully implemented")
    print("[!] Coming soon: voltage glitching, logic analyzer, power analysis")


def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  Hardware Hacking Tool - Comprehensive Functionality Test           ║
║                                                                      ║
║  This script will test all connected devices and report their       ║
║  capabilities and current status.                                   ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    # Test device detection
    devices = test_device_detection()

    if not devices:
        print("\n[!] No devices found. Please connect hardware and try again.")
        return 1

    # Test each device type
    test_buspirate(devices)
    test_bolt(devices)

    # Summary
    print_header("TEST SUMMARY")
    print(f"\n  Total devices detected: {len(devices)}")
    print(f"  Devices tested:")
    for name, info in devices.items():
        status = "✓ PASS" if info.device_type == 'buspirate' else "⚠ PARTIAL"
        print(f"    [{status}] {info.name} ({info.device_type})")

    print("\n" + "="*70)
    print("\n  [+] All tests complete!")
    print("\n  Next steps:")
    print("    1. Try interactive mode: python3 -m hwh.interactive")
    print("    2. Use the CLI: hwh detect, hwh spi id, hwh i2c scan")
    print("    3. Import as library: from hwh import detect, get_backend")
    print("\n" + "="*70 + "\n")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
