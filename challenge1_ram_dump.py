#!/usr/bin/env python3
"""
Curious Bolt CTF - Challenge 1: RAM Dumping

This challenge exploits a design vulnerability in STM32F1 series where
debugging can only be disabled in software, not via hardware fuses.

Steps:
1. Press button 1 on Bolt CTF to load flag into RAM
2. Enter bootloader mode (hold BOOT, press RESET)
3. Use PyOCD to dump RAM
4. Extract flag from dump
"""

import subprocess
import sys
import os

print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  Curious Bolt CTF - Challenge 1: RAM Dumping                        ║
║                                                                      ║
║  Objective: Extract flag from RAM despite disabled debugging        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

print("\n" + "="*70)
print("SETUP INSTRUCTIONS")
print("="*70)

print("""
Hardware Wiring (ST-Link → Bolt CTF):
────────────────────────────────────────
  ST-Link SWDIO   →  Bolt CTF SWDIO
  ST-Link SWCLK   →  Bolt CTF SWCLK
  ST-Link GND     →  Bolt CTF GND
  ST-Link 3.3V    →  Bolt CTF VCC

Bolt CTF has a header labeled: SWCLK / GND / SWDIO
""")

input("\nPress Enter when ST-Link is connected...")

print("\n" + "="*70)
print("STEP 1: START CHALLENGE 1")
print("="*70)
print("""
On your Bolt CTF board:
  1. Press button 1 (Challenge 1)
  2. The flag is now loaded into RAM
""")

input("Press Enter after pressing button 1...")

print("\n" + "="*70)
print("STEP 2: ENTER BOOTLOADER MODE")
print("="*70)
print("""
On your Bolt CTF board:
  1. Press and HOLD the BOOT button
  2. While holding BOOT, press and release RESET
  3. Release BOOT button

The device is now in bootloader mode (debugging enabled).
""")

input("Press Enter after entering bootloader mode...")

print("\n" + "="*70)
print("STEP 3: CHECK PYOCD INSTALLATION")
print("="*70)

# Check if pyocd is installed
try:
    result = subprocess.run(['pyocd', '--version'], capture_output=True, text=True)
    print(f"✅ PyOCD installed: {result.stdout.strip()}")
except FileNotFoundError:
    print("❌ PyOCD not found. Installing...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyocd'])
    print("✅ PyOCD installed")

print("\n" + "="*70)
print("STEP 4: DUMP RAM WITH PYOCD")
print("="*70)

dump_file = "/tmp/bolt_ctf_sram.dump"

print(f"\nDumping RAM to: {dump_file}")
print("This will dump 20KB from RAM starting at 0x20000000...")
print("\nStarting PyOCD commander...")
print("(This will open an interactive session)")
print("\nCommands to run:")
print("  >>> savemem 0x20000000 20480 " + dump_file)
print("  >>> exit")
print()

# Launch pyocd commander interactively
subprocess.run(['pyocd', 'commander'])

print("\n" + "="*70)
print("STEP 5: EXTRACT FLAG")
print("="*70)

if os.path.exists(dump_file):
    print(f"✅ Dump file found: {dump_file}")
    print("\nSearching for flag...")

    # Run strings and grep for flag
    result = subprocess.run(
        f"strings {dump_file} | grep -i ctf",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.stdout:
        print("\n" + "="*70)
        print("🎉 FLAG FOUND!")
        print("="*70)
        print(result.stdout)
        print("="*70)
    else:
        print("⚠️  No flag found with 'ctf' keyword")
        print("Showing all strings in dump:")
        subprocess.run(f"strings {dump_file} | head -50", shell=True)
else:
    print(f"❌ Dump file not found: {dump_file}")
    print("Make sure you ran 'savemem' in PyOCD commander")

print("\n" + "="*70)
print("CHALLENGE 1 COMPLETE!")
print("="*70)
print("""
If you found the flag, congratulations! 🎉

Next challenges:
  - Challenge 2: Boolean glitching (power glitching required)
  - Challenge 3: I2C corruption (glitch the I2C line)
  - Challenge 4: Unreachable code execution (advanced)

Ready to try Challenge 2? Run: python3 challenge2_glitching.py
""")
