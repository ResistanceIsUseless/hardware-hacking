#!/usr/bin/env python3
"""Test UART communication with Bolt CTF device via Bus Pirate"""

import sys
import time
sys.path.insert(0, '/Users/matthew/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh')

from pybpio.bpio_client import BPIOClient
from pybpio.bpio_uart import BPIOUART

def test_bolt_uart():
    """Test UART communication with Bolt CTF"""

    # Connect to Bus Pirate
    port = '/dev/cu.usbmodem6buspirate3'  # BPIO2 binary port
    print(f"Connecting to Bus Pirate on {port}...")

    client = BPIOClient(port)
    uart = BPIOUART(client)

    # Configure UART mode with PSU enabled
    print("\nConfiguring UART: 115200 baud, 8N1...")
    success = uart.configure(
        speed=115200,
        data_bits=8,
        parity=False,
        stop_bits=1,
        flow_control=False,
        signal_inversion=False,
        psu_enable=True,
        psu_set_mv=3300,
        psu_set_ma=100,
        pullup_enable=False  # UART doesn't need pull-ups
    )

    if not success:
        print("❌ Failed to configure UART mode")
        client.close()
        return False

    print("✅ UART configured successfully")

    # Check status
    time.sleep(0.5)
    status = uart.get_status()
    print(f"\nCurrent mode: {status.get('mode_current', 'Unknown')}")
    print(f"PSU enabled: {status.get('psu_enabled', False)}")
    print(f"PSU voltage: {status.get('psu_measured_mv', 0)}mV")
    print(f"PSU current: {status.get('psu_measured_ma', 0)}mA")

    # Get pin voltages
    pin_voltages = status.get('adc_mv', [])
    pin_labels = status.get('mode_pin_labels', [])

    if pin_voltages and pin_labels:
        print("\nPin voltages:")
        for i, (label, voltage) in enumerate(zip(pin_labels, pin_voltages)):
            if label:  # Skip empty labels
                print(f"  {label}: {voltage}mV")

    # Try reading from UART (check if Bolt is transmitting anything)
    print("\n[Test 1] Attempting to read from Bolt UART (5 second timeout)...")
    print("Listening for data...")

    # Read in a loop for 5 seconds
    start_time = time.time()
    data_received = []

    while time.time() - start_time < 5:
        result = uart.read(32)  # Try to read 32 bytes
        if result:
            data_received.extend(result)
            print(f"Received: {bytes(result)}")

        time.sleep(0.1)

    if data_received:
        print(f"✅ Received {len(data_received)} bytes from Bolt")
        print(f"Data: {bytes(data_received)}")
    else:
        print("⚠️  No data received (Bolt may not be transmitting)")

    # Try writing to UART
    print("\n[Test 2] Writing test data to Bolt UART...")
    test_message = b"Hello from Bus Pirate!\r\n"
    result = uart.write(list(test_message))

    if result is not False:
        print(f"✅ Wrote {len(test_message)} bytes")

        # Try reading response
        print("Waiting for response...")
        time.sleep(1)
        result = uart.read(64)
        if result:
            print(f"✅ Received response: {bytes(result)}")
        else:
            print("⚠️  No response received")
    else:
        print("❌ Write failed")

    # Final status
    print("\n" + "="*50)
    status = uart.get_status()
    print(f"Final PSU current: {status.get('psu_measured_ma', 0)}mA")
    print(f"Final pin voltages:")
    pin_voltages = status.get('adc_mv', [])
    pin_labels = status.get('mode_pin_labels', [])
    for i, (label, voltage) in enumerate(zip(pin_labels, pin_voltages)):
        if label:
            print(f"  {label}: {voltage}mV")

    client.close()
    print("\n✅ Test complete!")
    return True

if __name__ == '__main__':
    try:
        success = test_bolt_uart()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
