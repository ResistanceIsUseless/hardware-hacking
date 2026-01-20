#!/usr/bin/env python3
"""
Example 2: UART Auto-Interaction

This example demonstrates:
- Finding UART-capable devices
- Auto-detecting environment (shell, login, bootloader)
- Auto-interacting (trying credentials, enumeration)
- Displaying captured information

Usage:
    python3 examples/02_uart_auto_interact.py

Requirements:
    - UART-capable device (Bus Pirate, Tigard, etc.)
    - Target device connected to UART pins
    - Target powered on
"""
import asyncio
from hwh.tui.device_pool import DevicePool
from hwh.automation import UARTAutomation


async def main():
    print("=== UART Auto-Interaction Example ===\n")

    # Setup device pool
    pool = DevicePool()
    print("Scanning for devices...")
    await pool.scan_devices()

    # Find UART-capable device
    uart_devices = pool.get_devices_by_capability("uart")
    if not uart_devices:
        print("❌ No UART-capable device found!")
        print("\nNeeded: Bus Pirate, Tigard, or Black Magic Probe")
        return

    device_id = uart_devices[0]
    print(f"✓ Using {device_id} for UART")

    # Connect
    if not await pool.connect(device_id):
        print(f"❌ Failed to connect to {device_id}")
        return

    print(f"✓ Connected to {device_id}\n")

    # Get backend
    backend = pool.get_backend(device_id)

    # Create UART automation
    print("="*60)
    print("Configuring UART automation...")
    automation = UARTAutomation(backend)

    # Configure UART (adjust baudrate for your target)
    baudrate = 115200  # Common default
    await automation.configure(baudrate=baudrate)
    print(f"✓ UART configured: {baudrate} baud, 8N1")

    # Auto-interact with target
    print("\n" + "="*60)
    print("Auto-interacting with target...")
    print("(This may take 30-60 seconds)")
    print("="*60 + "\n")

    try:
        results = await automation.auto_interact()

        # Display results
        print("\n" + "="*60)
        print("=== Results ===")
        print("="*60 + "\n")

        detected = results['detected_environment']
        print(f"Environment: {detected.environment_type.name}")

        if detected.patterns_matched:
            print(f"Patterns matched: {detected.patterns_matched[:3]}...")

        if results['login_attempted']:
            if results['login_success']:
                print("✓ Login successful")
                print(f"  Credentials: {results['credentials_used']}")
            else:
                print("✗ Login failed (tried common credentials)")

        if results['enumeration']:
            print("\n=== Enumeration Results ===\n")
            for cmd, output in results['enumeration'].items():
                print(f"Command: {cmd}")
                print(f"Output preview: {output[:200]}")
                print()

        if results['bootloader_probed']:
            print("\n=== Bootloader Info ===")
            for cmd, output in results['bootloader_commands'].items():
                print(f"  {cmd}: {output[:100]}")

        print("\n" + "="*60)
        print(f"Total data captured: {len(results['raw_capture'])} bytes")

    except Exception as e:
        print(f"\n❌ Error during auto-interaction: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    print("\n" + "="*60)
    print("Cleaning up...")
    await pool.disconnect_all()
    print("✓ Done")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
