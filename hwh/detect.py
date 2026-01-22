"""
Device detection - enumerate connected hardware hacking tools.

Scans USB and serial ports to identify known devices.
"""

import sys
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

# --------------------------------------------------------------------------
# Known Device Definitions
# --------------------------------------------------------------------------

@dataclass
class DeviceInfo:
    """Metadata about a detected device."""
    name: str
    device_type: str  # stlink, buspirate, tigard, bolt, faultycat
    port: Optional[str] = None  # Serial port path (e.g., /dev/ttyACM0)
    usb_path: Optional[str] = None  # USB device path
    vid: Optional[int] = None
    pid: Optional[int] = None
    serial: Optional[str] = None
    capabilities: list[str] = field(default_factory=list)


# USB VID:PID mappings for known devices
# Format: (VID, PID): (name, device_type, capabilities)
KNOWN_USB_DEVICES = {
    # ST-Link variants
    (0x0483, 0x3748): ("ST-Link V2", "stlink", ["swd", "jtag", "debug"]),
    (0x0483, 0x374B): ("ST-Link V2-1", "stlink", ["swd", "jtag", "debug"]),
    (0x0483, 0x374D): ("ST-Link V3 Mini", "stlink", ["swd", "jtag", "debug"]),
    (0x0483, 0x374E): ("ST-Link V3", "stlink", ["swd", "jtag", "debug"]),
    (0x0483, 0x374F): ("ST-Link V3", "stlink", ["swd", "jtag", "debug"]),
    (0x0483, 0x3752): ("ST-Link V2.1", "stlink", ["swd", "jtag", "debug"]),
    (0x0483, 0x3753): ("ST-Link V3", "stlink", ["swd", "jtag", "debug"]),
    
    # Black Magic Probe variants
    (0x1D50, 0x6018): ("Black Magic Probe", "blackmagic", ["swd", "jtag", "debug", "uart"]),
    (0x1D50, 0x6017): ("Black Magic Probe (DFU)", "blackmagic_dfu", ["dfu"]),
    (0x1D50, 0x6024): ("Black Magic Probe V2.3", "blackmagic", ["swd", "jtag", "debug", "uart"]),
    
    # Bus Pirate variants
    (0x1209, 0x7331): ("Bus Pirate 5/6", "buspirate", ["spi", "i2c", "uart", "1wire", "jtag", "psu"]),
    (0x2047, 0x0900): ("Bus Pirate 5", "buspirate", ["spi", "i2c", "uart", "1wire", "jtag", "psu"]),
    (0x2047, 0x0901): ("Bus Pirate 6", "buspirate", ["spi", "i2c", "uart", "1wire", "jtag", "psu"]),
    (0x0403, 0x6001): ("Bus Pirate v3/v4", "buspirate_legacy", ["spi", "i2c", "uart", "1wire"]),
    
    # Tigard (FTDI FT2232H)
    (0x0403, 0x6010): ("Tigard / FT2232H", "tigard", ["spi", "i2c", "uart", "jtag", "swd"]),

    # RP2040-based devices (Curious Bolt, FaultyCat)
    # Note: Same VID:PID, requires runtime identification via serial probing
    (0x2E8A, 0x000A): ("RP2040 Device", "rp2040_unknown", ["unknown"]),
    (0x2E8A, 0x0003): ("RP2040 Device (alt)", "rp2040_unknown", ["unknown"]),

    # Curious Bolt (voltage glitching, logic analyzer, power analysis)
    (0xCAFE, 0x4002): ("Curious Bolt", "bolt", ["voltage_glitch", "logic_analyzer", "power_analysis"]),

    # Common UART adapters
    (0x1A86, 0x7523): ("CH340 UART", "uart", ["uart"]),
    (0x10C4, 0xEA60): ("CP2102 UART", "uart", ["uart"]),
    (0x067B, 0x2303): ("PL2303 UART", "uart", ["uart"]),
}

# Serial port patterns for fallback detection
SERIAL_PATTERNS = {
    "buspirate": ["/dev/ttyACM*", "/dev/tty.usbmodem*", "COM*"],
    "bolt": ["/dev/ttyACM*", "/dev/tty.usbmodem*"],
    "stlink": ["/dev/ttyACM*"],
}


# --------------------------------------------------------------------------
# Detection Functions
# --------------------------------------------------------------------------

def _detect_usb_devices() -> list[DeviceInfo]:
    """Detect devices via USB enumeration using pyusb."""
    devices = []
    
    try:
        import usb.core
        import usb.util
    except ImportError:
        # pyusb not installed, skip USB detection
        return devices
    
    for dev in usb.core.find(find_all=True):
        vid_pid = (dev.idVendor, dev.idProduct)
        
        if vid_pid in KNOWN_USB_DEVICES:
            name, device_type, caps = KNOWN_USB_DEVICES[vid_pid]
            
            # Try to get serial number
            serial = None
            try:
                serial = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else None
            except (usb.core.USBError, ValueError):
                pass
            
            devices.append(DeviceInfo(
                name=name,
                device_type=device_type,
                vid=dev.idVendor,
                pid=dev.idProduct,
                serial=serial,
                usb_path=f"{dev.bus}:{dev.address}",
                capabilities=caps.copy(),
            ))
    
    return devices


def _detect_serial_devices() -> list[DeviceInfo]:
    """Detect devices via serial port enumeration."""
    devices = []
    
    try:
        import serial.tools.list_ports
    except ImportError:
        return devices
    
    for port in serial.tools.list_ports.comports():
        vid_pid = (port.vid, port.pid) if port.vid and port.pid else None
        
        if vid_pid and vid_pid in KNOWN_USB_DEVICES:
            name, device_type, caps = KNOWN_USB_DEVICES[vid_pid]
            
            devices.append(DeviceInfo(
                name=name,
                device_type=device_type,
                port=port.device,
                vid=port.vid,
                pid=port.pid,
                serial=port.serial_number,
                capabilities=caps.copy(),
            ))
        elif port.vid and port.pid:
            # Unknown device with USB IDs - log for potential addition
            devices.append(DeviceInfo(
                name=f"Unknown ({port.vid:04x}:{port.pid:04x})",
                device_type="unknown",
                port=port.device,
                vid=port.vid,
                pid=port.pid,
                serial=port.serial_number,
                capabilities=[],
            ))
    
    return devices


def _identify_rp2040_device(device: DeviceInfo) -> DeviceInfo:
    """
    Attempt to identify RP2040-based devices (Bolt vs FaultyCat).
    
    Sends identification commands to distinguish between devices.
    """
    if device.device_type != "rp2040_unknown" or not device.port:
        return device
    
    try:
        import serial
        
        with serial.Serial(device.port, 115200, timeout=1) as ser:
            # Try Bolt identification
            ser.write(b"*IDN?\r\n")
            response = ser.readline().decode(errors='ignore').strip()
            
            if "bolt" in response.lower() or "curious" in response.lower():
                device.name = "Curious Bolt"
                device.device_type = "bolt"
                device.capabilities = ["glitch", "logic", "dpa"]
            elif "faulty" in response.lower() or "emfi" in response.lower():
                device.name = "FaultyCat"
                device.device_type = "faultycat"
                device.capabilities = ["emfi", "glitch", "jtag_scan"]
                
    except Exception:
        pass  # Can't identify, leave as unknown
    
    return device


def _deduplicate_devices(devices: list[DeviceInfo]) -> list[DeviceInfo]:
    """Remove duplicate device entries (USB + serial showing same device)."""
    seen = {}
    
    for dev in devices:
        # Key by serial number if available, otherwise by VID:PID:type
        if dev.serial:
            key = (dev.serial, dev.device_type)
        else:
            key = (dev.vid, dev.pid, dev.device_type, dev.port or dev.usb_path)
        
        if key not in seen:
            seen[key] = dev
        else:
            # Merge - prefer entry with serial port
            existing = seen[key]
            if dev.port and not existing.port:
                existing.port = dev.port
            if dev.usb_path and not existing.usb_path:
                existing.usb_path = dev.usb_path
    
    return list(seen.values())


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def detect(identify_unknown: bool = True) -> dict[str, DeviceInfo]:
    """
    Detect all connected hardware hacking tools.
    
    Args:
        identify_unknown: If True, attempt to identify RP2040 devices by probing.
        
    Returns:
        Dict mapping device_type to DeviceInfo. If multiple devices of same type,
        keys are suffixed with index (e.g., "stlink", "stlink_1").
    """
    devices = []
    
    # Gather from multiple sources
    devices.extend(_detect_usb_devices())
    devices.extend(_detect_serial_devices())
    
    # Deduplicate
    devices = _deduplicate_devices(devices)
    
    # Identify unknown RP2040 devices
    if identify_unknown:
        devices = [_identify_rp2040_device(d) for d in devices]
    
    # Filter out unknown devices for the return dict
    known_devices = [d for d in devices if d.device_type != "unknown"]
    
    # Build result dict with unique keys
    result = {}
    type_counts = {}
    
    for dev in known_devices:
        base_key = dev.device_type
        count = type_counts.get(base_key, 0)
        
        if count == 0:
            key = base_key
        else:
            key = f"{base_key}_{count}"
        
        type_counts[base_key] = count + 1
        result[key] = dev
    
    return result


def list_devices(include_unknown: bool = False) -> list[DeviceInfo]:
    """
    List all detected devices.
    
    Args:
        include_unknown: If True, include unrecognized USB serial devices.
        
    Returns:
        List of DeviceInfo for all detected devices.
    """
    devices = []
    devices.extend(_detect_usb_devices())
    devices.extend(_detect_serial_devices())
    devices = _deduplicate_devices(devices)
    
    if not include_unknown:
        devices = [d for d in devices if d.device_type != "unknown"]
    
    return devices


# --------------------------------------------------------------------------
# CLI Helper
# --------------------------------------------------------------------------

def print_detected_devices():
    """Print detected devices in a formatted table."""
    devices = list_devices(include_unknown=True)
    
    if not devices:
        print("No devices detected.")
        print("\nTroubleshooting:")
        print("  - Check USB connections")
        print("  - Ensure drivers are installed")
        print("  - Try: pip install pyusb pyserial")
        return
    
    print(f"{'Name':<25} {'Type':<15} {'Port':<20} {'VID:PID':<12} {'Capabilities'}")
    print("-" * 90)
    
    for dev in devices:
        vid_pid = f"{dev.vid:04x}:{dev.pid:04x}" if dev.vid and dev.pid else "N/A"
        port = dev.port or "N/A"
        caps = ", ".join(dev.capabilities[:3]) if dev.capabilities else "N/A"
        if len(dev.capabilities) > 3:
            caps += "..."
        
        print(f"{dev.name:<25} {dev.device_type:<15} {port:<20} {vid_pid:<12} {caps}")


if __name__ == "__main__":
    print_detected_devices()
