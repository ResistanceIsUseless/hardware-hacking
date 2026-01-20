#!/usr/bin/env python3
"""
Quick connection test for Bolt CTF setup
Tests all connected devices and verifies they're ready to use
"""

import sys
import os

print("=" * 60)
print("🔧 Bolt CTF Connection Test")
print("=" * 60)
print()

# Test 1: Curious Bolt (scope library)
print("[ 1 ] Testing Curious Bolt connection...")
try:
    from scope import Scope
    s = Scope()
    print("     ✅ Curious Bolt connected")
    print(f"     📍 Version: {getattr(s, 'version', 'Unknown')}")

    # Test glitch configuration
    s.glitch.repeat = 42
    s.glitch.ext_offset = 0
    print(f"     ✅ Glitch configuration working")
    print(f"        - repeat: {s.glitch.repeat} cycles (~{s.glitch.repeat * 8.3:.1f}ns)")
    print(f"        - ext_offset: {s.glitch.ext_offset} cycles")
except ImportError:
    print("     ❌ scope library not found")
    print("        Install: cp ~/hardware_hacking/tools/bolt/lib/scope.py")
    print("                 to Python site-packages")
except IOError as e:
    print(f"     ❌ Curious Bolt not detected: {e}")
    print("        Check USB connection: ls /dev/cu.usbmodem*")
except Exception as e:
    print(f"     ❌ Error: {e}")

print()

# Test 2: Serial port for Bolt CTF
print("[ 2 ] Testing Bolt CTF serial connection...")
try:
    import serial
    import serial.tools.list_ports

    # Find all serial ports
    ports = list(serial.tools.list_ports.comports())
    bolt_ctf_port = None

    for port in ports:
        if 'usbserial' in port.device:
            bolt_ctf_port = port.device
            break

    if bolt_ctf_port:
        print(f"     ✅ Bolt CTF serial port found: {bolt_ctf_port}")

        # Try to open it
        try:
            ser = serial.Serial(bolt_ctf_port, 115200, timeout=1)
            print(f"     ✅ Port opened successfully at 115200 baud")

            # Try to read some data
            ser.write(b'\n')
            import time
            time.sleep(0.1)
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"     ✅ Received data: {len(data)} bytes")
            else:
                print(f"     ⚠️  No immediate data (press a button on Bolt CTF)")

            ser.close()
        except Exception as e:
            print(f"     ❌ Could not open port: {e}")
    else:
        print(f"     ❌ Bolt CTF serial port not found")
        print(f"        Available ports:")
        for port in ports:
            print(f"          - {port.device}")
        print(f"        Check USB connection")

except ImportError:
    print("     ❌ pyserial not installed")
    print("        Install: pip install pyserial")
except Exception as e:
    print(f"     ❌ Error: {e}")

print()

# Test 3: Bus Pirate (optional)
print("[ 3 ] Testing Bus Pirate connection (optional)...")
try:
    sys.path.insert(0, os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh"))
    from detect import detect

    devices = detect()

    bp_found = False
    for dev in devices.values():
        if dev.device_type == "buspirate":
            print(f"     ✅ Bus Pirate found: {dev.port}")
            bp_found = True
            break

    if not bp_found:
        print(f"     ⚠️  Bus Pirate not detected (optional for CTF)")

except Exception as e:
    print(f"     ⚠️  Could not test Bus Pirate: {e}")

print()

# Test 4: glitch-o-bolt installation
print("[ 4 ] Testing glitch-o-bolt installation...")
try:
    glitch_path = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh/tooling/glitch-o-bolt")

    if os.path.exists(glitch_path):
        print(f"     ✅ glitch-o-bolt found at:")
        print(f"        {glitch_path}")

        # Check for config files
        configs = [f for f in os.listdir(glitch_path) if f.startswith('Config') and f.endswith('.py')]
        if configs:
            print(f"     ✅ Found {len(configs)} config files:")
            for cfg in sorted(configs)[:5]:
                print(f"        - {cfg}")
        else:
            print(f"     ⚠️  No config files found")
    else:
        print(f"     ❌ glitch-o-bolt not found")
        print(f"        Expected at: {glitch_path}")

except Exception as e:
    print(f"     ❌ Error: {e}")

print()

# Test 5: textual library (for glitch-o-bolt TUI)
print("[ 5 ] Testing textual library (for TUI)...")
try:
    import textual
    print(f"     ✅ textual installed: {textual.__version__}")
except ImportError:
    print(f"     ❌ textual not installed")
    print(f"        Install: pip install textual")
except Exception as e:
    print(f"     ❌ Error: {e}")

print()
print("=" * 60)
print("Summary")
print("=" * 60)
print()

# Determine readiness
ready = True
issues = []

try:
    from scope import Scope
    Scope()
except:
    ready = False
    issues.append("Curious Bolt not connected or scope library not installed")

try:
    import serial
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    if not any('usbserial' in p.device for p in ports):
        ready = False
        issues.append("Bolt CTF serial port not found")
except:
    ready = False
    issues.append("pyserial not installed")

try:
    import textual
except:
    issues.append("textual not installed (needed for glitch-o-bolt)")

if ready:
    print("🎉 All critical components ready!")
    print()
    print("Next steps:")
    print("  1. Read START_HERE.md for quick start")
    print("  2. Wire Curious Bolt GLITCH_OUT → Bolt CTF VMCU")
    print("  3. Run: cd hwh/tooling/glitch-o-bolt && python3 glitch-o-bolt.py")
    print()
else:
    print("⚠️  Some issues detected:")
    for issue in issues:
        print(f"  ❌ {issue}")
    print()
    print("See error messages above for details.")
    print()

print("=" * 60)
