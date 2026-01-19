#!/usr/bin/env python3
"""
Interactive Hardware Hacking Tool

Detects connected hardware devices and provides an intelligent menu system
for interacting with them. Inspired by Bus Pirate's menu but with enhanced
device detection and context-aware guidance.
"""

import sys
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .detect import detect, DeviceInfo
from .backends import get_backend, SPIConfig, I2CConfig, UARTConfig


@dataclass
class Session:
    """Current session state"""
    devices: Dict[str, DeviceInfo]
    active_device: Optional[str] = None
    active_backend: Optional[Any] = None


def print_banner():
    """Print welcome banner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Hardware Hacking Tool - Interactive Mode                    ║
║  Unified interface for hardware security tools               ║
╚══════════════════════════════════════════════════════════════╝
""")


def detect_devices() -> Dict[str, DeviceInfo]:
    """Detect all connected devices"""
    print("[*] Scanning for connected devices...")
    devices = detect()

    if not devices:
        print("  [!] No devices found")
        print("  [!] Make sure your hardware is connected via USB")
        return {}

    print(f"  [+] Found {len(devices)} device(s):\n")

    for i, (name, info) in enumerate(devices.items(), 1):
        print(f"  [{i}] {info.name}")
        print(f"      Type: {info.device_type}")
        print(f"      Port: {info.port}")
        if info.vid and info.pid:
            print(f"      USB: {info.vid:04x}:{info.pid:04x}")
        print()

    return devices


def show_device_menu(device_name: str, device_info: DeviceInfo):
    """Show context-aware menu for a specific device"""
    print(f"\n╔══ {device_info.name} ══")
    print(f"║ Port: {device_info.port}")
    print(f"║ Type: {device_info.device_type}")
    print("╠═══════════════════════════════════════")

    if device_info.device_type == 'buspirate':
        print("║ [1] Configure SPI")
        print("║ [2] Configure I2C")
        print("║ [3] Configure UART (if firmware supports)")
        print("║ [4] Scan target device (auto-detect interfaces)")
        print("║ [5] PSU control")
        print("║ [6] Read pin voltages")
        print("║ [7] Device info")
    elif device_info.device_type == 'bolt':
        print("║ [1] Voltage glitch configuration")
        print("║ [2] Logic analyzer")
        print("║ [3] Power analysis")
        print("║ [4] Single glitch test")
        print("║ [5] Glitch parameter sweep")
    elif device_info.device_type == 'stlink':
        print("║ [1] Read memory")
        print("║ [2] Dump firmware")
        print("║ [3] Flash firmware")
        print("║ [4] Reset target")
    else:
        print(f"║ [!] Device type '{device_info.device_type}' not yet supported")

    print("║")
    print("║ [b] Back to device selection")
    print("║ [q] Quit")
    print("╚═══════════════════════════════════════")


def handle_buspirate_commands(session: Session):
    """Handle Bus Pirate specific commands"""
    if not session.active_backend:
        backend = get_backend(session.devices[session.active_device])
        if not backend.connect():
            print("[!] Failed to connect to Bus Pirate")
            return
        session.active_backend = backend

    bp = session.active_backend

    while True:
        device_info = session.devices[session.active_device]
        show_device_menu(session.active_device, device_info)

        choice = input("\nCommand: ").strip().lower()

        if choice == 'q':
            bp.disconnect()
            sys.exit(0)
        elif choice == 'b':
            bp.disconnect()
            session.active_backend = None
            return

        elif choice == '1':  # SPI
            print("\n[SPI Configuration]")
            speed = input("  Speed (Hz) [1000000]: ").strip() or "1000000"
            mode = input("  Mode (0-3) [0]: ").strip() or "0"

            config = SPIConfig(speed_hz=int(speed), mode=int(mode))
            if bp.configure_spi(config):
                print("  [+] SPI configured successfully")

                # Offer to read flash ID
                if input("  Read SPI flash ID? (y/n) [y]: ").strip().lower() != 'n':
                    flash_id = bp.spi_flash_read_id()
                    if flash_id:
                        print(f"  Flash ID: {flash_id.hex()}")
                        mfg = flash_id[0] if len(flash_id) > 0 else 0
                        dev = flash_id[1:3].hex() if len(flash_id) >= 3 else "unknown"
                        print(f"  Manufacturer: 0x{mfg:02x}")
                        print(f"  Device: 0x{dev}")

        elif choice == '2':  # I2C
            print("\n[I2C Configuration]")
            speed = input("  Speed (Hz) [100000]: ").strip() or "100000"

            config = I2CConfig(speed_hz=int(speed))
            if bp.configure_i2c(config):
                print("  [+] I2C configured successfully")

                # Offer to scan bus
                if input("  Scan I2C bus? (y/n) [y]: ").strip().lower() != 'n':
                    bp.set_pullups(enabled=True)
                    print("  Scanning I2C bus (0x08-0x77)...")
                    devices = bp.i2c_scan(start_addr=0x08, end_addr=0x77)
                    if devices:
                        print(f"  [+] Found {len(devices)} device(s):")
                        for addr in devices:
                            print(f"      0x{addr:02x}")
                    else:
                        print("  [!] No I2C devices found")

        elif choice == '3':  # UART
            print("\n[UART Configuration]")
            print("  [!] Note: UART may not be supported in all firmware versions")
            baud = input("  Baud rate [115200]: ").strip() or "115200"
            data_bits = input("  Data bits [8]: ").strip() or "8"
            parity = input("  Parity (N/E/O) [N]: ").strip().upper() or "N"
            stop_bits = input("  Stop bits (1/2) [1]: ").strip() or "1"

            config = UARTConfig(
                baudrate=int(baud),
                data_bits=int(data_bits),
                parity=parity,
                stop_bits=int(stop_bits)
            )
            if bp.configure_uart(config):
                print("  [+] UART configured successfully")
            else:
                print("  [!] UART configuration failed (firmware may not support it)")

        elif choice == '4':  # Scan target
            print("\n[Scanning Target Device]")
            print("  This will:")
            print("  - Enable PSU (3.3V)")
            print("  - Scan I2C bus")
            print("  - Test SPI flash")
            print("  - Read all pin voltages")
            print()

            if input("  Proceed? (y/n) [y]: ").strip().lower() == 'n':
                continue

            results = bp.scan_target(power_voltage_mv=3300, power_current_ma=300)

            print("\n  [Results]")
            print(f"  PSU: {results['psu']['measured_voltage_mv']}mV @ {results['psu']['measured_current_ma']}mA")

            if results['i2c_devices']:
                print(f"  I2C: Found {len(results['i2c_devices'])} device(s)")
                for addr in results['i2c_devices']:
                    print(f"       0x{addr:02x}")
            else:
                print("  I2C: No devices found")

            if results['spi_flash']['detected']:
                print(f"  SPI Flash: Detected (ID: {results['spi_flash']['id']})")
            else:
                print("  SPI Flash: Not detected")

            print("\n  Pin voltages:")
            for pin, voltage in results['pin_voltages'].items():
                if pin:  # Skip empty labels
                    print(f"    {pin:8s}: {voltage:4d}mV")

        elif choice == '5':  # PSU control
            print("\n[PSU Control]")
            enable = input("  Enable PSU? (y/n): ").strip().lower() == 'y'

            if enable:
                voltage = input("  Voltage (mV) [3300]: ").strip() or "3300"
                current = input("  Current limit (mA) [300]: ").strip() or "300"
                bp.set_psu(enabled=True, voltage_mv=int(voltage), current_ma=int(current))
                print(f"  [+] PSU enabled: {voltage}mV, {current}mA limit")
            else:
                bp.set_psu(enabled=False)
                print("  [+] PSU disabled")

        elif choice == '6':  # Read pin voltages
            info = bp.get_info()
            voltages = info.get('adc_mv', [])
            labels = info.get('mode_pin_labels', [])

            print("\n  [Pin Voltages]")
            for label, voltage in zip(labels, voltages):
                if label:
                    print(f"    {label:8s}: {voltage:4d}mV")

        elif choice == '7':  # Device info
            info = bp.get_info()
            print("\n  [Device Information]")
            print(f"    Firmware: v{info.get('version_firmware_major')}.{info.get('version_firmware_minor')}")
            print(f"    Hardware: v{info.get('version_hardware_major')} REV{info.get('version_hardware_minor')}")
            print(f"    Date: {info.get('version_firmware_date')}")
            print(f"    Git: {info.get('version_firmware_git_hash')}")
            print(f"    Mode: {info.get('mode_current')}")
            print(f"\n    Available modes:")
            for mode in info.get('modes_available', []):
                print(f"      - {mode}")


def select_device(session: Session) -> bool:
    """Let user select a device to interact with"""
    if not session.devices:
        return False

    print("\n[Select Device]")
    device_list = list(session.devices.items())

    for i, (name, info) in enumerate(device_list, 1):
        print(f"  [{i}] {info.name} ({info.device_type})")

    print(f"  [q] Quit")

    choice = input("\nDevice: ").strip().lower()

    if choice == 'q':
        return False

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(device_list):
            session.active_device = device_list[idx][0]
            return True
    except ValueError:
        pass

    print("[!] Invalid selection")
    return select_device(session)


def main():
    """Main interactive loop"""
    print_banner()

    # Detect devices
    devices = detect_devices()

    if not devices:
        print("[!] No devices found. Exiting.")
        return 1

    # Create session
    session = Session(devices=devices)

    # If only one device, auto-select it
    if len(devices) == 1:
        session.active_device = list(devices.keys())[0]
        print(f"[*] Auto-selected: {devices[session.active_device].name}\n")
    else:
        # Let user select device
        if not select_device(session):
            return 0

    # Device-specific command loop
    device_info = devices[session.active_device]

    if device_info.device_type == 'buspirate':
        handle_buspirate_commands(session)
    else:
        print(f"[!] Interactive mode for '{device_info.device_type}' not yet implemented")
        print("[!] Coming soon: Bolt, ST-Link, Tigard, Black Magic Probe support")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
