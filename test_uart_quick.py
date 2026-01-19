#!/usr/bin/env python3
"""Quick test of UART communication with Bolt CTF"""

import sys
import time
sys.path.insert(0, '/Users/matthew/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh')

from hwh import detect, get_backend
from hwh.backends import UARTConfig

def test_uart():
    """Test UART with Bolt CTF"""

    # Detect devices
    print("Detecting devices...")
    devices = detect()

    print("\nFound devices:")
    for name, info in devices.items():
        print(f"  - {name}: {info.name} at {info.port}")

    if 'buspirate' not in devices:
        print("\n❌ Bus Pirate not found")
        return False

    # Connect to Bus Pirate
    print("\n[1] Connecting to Bus Pirate...")
    bp = get_backend(devices['buspirate'])

    with bp:
        # Enable PSU
        print("[2] Enabling PSU (3.3V, 100mA)...")
        bp.set_psu(enabled=True, voltage_mv=3300, current_ma=100)
        time.sleep(1)

        # Check current draw
        info = bp.get_info()
        print(f"    Current draw: {info.get('psu_measured_ma', 0)}mA")

        # Configure UART
        print("[3] Configuring UART (115200 8N1)...")
        success = bp.configure_uart(UARTConfig(baudrate=115200, data_bits=8, parity='N', stop_bits=1))

        if not success:
            print("❌ Failed to configure UART")
            return False

        print("✅ UART configured")

        # Get updated status
        info = bp.get_info()
        print(f"\nMode: {info.get('mode_current', 'Unknown')}")
        print(f"Pin voltages:")
        pin_voltages = info.get('adc_mv', [])
        pin_labels = info.get('mode_pin_labels', [])
        for label, voltage in zip(pin_labels, pin_voltages):
            if label:
                print(f"  {label}: {voltage}mV")

        # Listen for data
        print("\n[4] Listening for UART data (10 seconds)...")
        print("    (Press Ctrl+C to stop)")

        start = time.time()
        data_received = bytearray()

        try:
            while time.time() - start < 10:
                # Try to read
                result = bp.uart_read(32)
                if result:
                    data_received.extend(result)
                    print(f"    RX: {result}")

                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n    Stopped by user")

        if data_received:
            print(f"\n✅ Received {len(data_received)} bytes total:")
            print(f"    Hex: {data_received.hex()}")
            print(f"    ASCII: {data_received.decode('ascii', errors='replace')}")
        else:
            print("\n⚠️  No data received")
            print("    Bolt CTF may not be transmitting, or wiring may be incorrect")
            print("    Expected wiring:")
            print("      Bolt TX (pin 4) → Bus Pirate MISO (pin 5)")
            print("      Bolt RX (pin 5) → Bus Pirate MOSI (pin 3)")
            print("      Bolt GND       → Bus Pirate GND")

        # Try sending data
        print("\n[5] Sending test message...")
        test_msg = b"Hello from Bus Pirate!\r\n"
        bp.uart_write(test_msg)
        print(f"    TX: {test_msg}")

        # Wait for response
        print("    Waiting for response...")
        time.sleep(1)
        result = bp.uart_read(64)
        if result:
            print(f"    RX: {result}")
        else:
            print("    No response")

    print("\n✅ Test complete")
    return True

if __name__ == '__main__':
    try:
        test_uart()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
