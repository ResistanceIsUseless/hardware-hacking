#!/usr/bin/env python3
"""
Example 1: Device Discovery and Connection Test

This example demonstrates:
- Scanning for connected hardware devices
- Testing connections to each device
- Displaying device pool status

Usage:
    python3 examples/01_device_discovery.py
"""
import asyncio
from hwh.tui.device_pool import DevicePool


async def main():
    print("=== Hardware Device Discovery ===\n")

    # Create device pool
    pool = DevicePool()

    # Scan for devices
    print("Scanning for devices...")
    devices = await pool.scan_devices()

    if not devices:
        print("❌ No devices found!")
        print("\nTroubleshooting:")
        print("  - Check USB connections")
        print("  - Verify devices are powered")
        print("  - Check USB permissions (Linux: add user to dialout group)")
        return

    # Display found devices
    print(f"\n✓ Found {len(devices)} device(s):\n")
    for dev_id in devices:
        device = pool.get_device(dev_id)
        print(f"  {dev_id}:")
        print(f"    Type: {device.device_info.device_type}")
        print(f"    Port: {device.device_info.port}")
        print(f"    Capabilities: {', '.join(device.device_info.capabilities)}")
        print()

    # Test connections
    print("="*60)
    print("Testing connections...")
    print()

    connection_results = []
    for dev_id in devices:
        success = await pool.connect(dev_id)
        connection_results.append((dev_id, success))
        status = "✓" if success else "✗"
        print(f"  {status} {dev_id}: {'Connected' if success else 'Failed'}")

    # Display pool status
    print("\n" + "="*60)
    print("Device Pool Status:")
    print("="*60)
    pool.display_status()

    # Cleanup
    print("="*60)
    print("Disconnecting all devices...")
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
