#!/usr/bin/env python3
"""
Glitching Attack Setup for Bolt CTF

Coordinates:
- Bus Pirate: Power control and monitoring
- Curious Bolt: Voltage glitching (when backend ready)
- Serial Monitor: Watch for successful glitches
"""

import sys
import time
import serial
import threading
sys.path.insert(0, '/Users/matthew/Library/Mobile Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh')

from hwh import detect, get_backend


class SerialMonitor:
    """Monitor Bolt CTF serial output for glitch success"""

    def __init__(self, port='/dev/cu.usbserial-110', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.messages = []
        self.thread = None

    def start(self):
        """Start monitoring"""
        self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
        print(f"[Monitor] Started on {self.port}")

    def _monitor(self):
        """Background monitoring loop"""
        while self.running:
            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting)
                text = data.decode('ascii', errors='replace')

                # Check for success indicators
                if "success" in text.lower() or "flag" in text.lower() or "pwned" in text.lower():
                    print(f"\n🎉 [GLITCH SUCCESS] {text}")
                elif text.strip() != "Hold one of the 4 challenge buttons to start them":
                    print(f"\n[Monitor] NEW OUTPUT: {text}")

                self.messages.append(text)
            time.sleep(0.05)

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.ser:
            self.ser.close()


def setup_power_control():
    """Setup Bus Pirate for power control"""
    print("\n" + "="*70)
    print("GLITCHING ATTACK SETUP")
    print("="*70)

    devices = detect()

    if 'buspirate' not in devices:
        print("[!] Bus Pirate not found")
        return None

    print("\n[1] Connecting to Bus Pirate...")
    bp = get_backend(devices['buspirate'])
    bp.connect()

    print("[2] Configuring power...")
    bp.set_psu(enabled=True, voltage_mv=3300, current_ma=300)

    info = bp.get_info()
    print(f"    Power: {info['psu_measured_mv']}mV @ {info['psu_measured_ma']}mA")

    return bp


def test_power_cycling(bp, monitor):
    """Test power cycling while monitoring output"""
    print("\n[3] Testing power cycling attack...")
    print("    This simulates crowbar/power glitching")

    for i in range(5):
        print(f"\n  [Cycle {i+1}/5]")

        # Power off
        bp.set_psu(enabled=False)
        print("    PSU OFF")
        time.sleep(0.5)

        # Power on
        bp.set_psu(enabled=True, voltage_mv=3300, current_ma=300)
        print("    PSU ON")

        # Wait for boot and output
        time.sleep(2)

        # Check current draw
        info = bp.get_info()
        print(f"    Current: {info['psu_measured_ma']}mA")


def glitching_attack_menu(bp, monitor):
    """Interactive glitching menu"""
    print("\n" + "="*70)
    print("GLITCHING ATTACK MENU")
    print("="*70)
    print("""
Available attacks:
  [1] Power cycle (5 times)
  [2] Rapid power glitch
  [3] Voltage drop test
  [4] Monitor only (watch for button presses)
  [5] Curious Bolt glitch (when backend ready)
  [q] Quit
""")

    while True:
        choice = input("\nSelect attack: ").strip()

        if choice == 'q':
            break
        elif choice == '1':
            test_power_cycling(bp, monitor)
        elif choice == '2':
            print("\n[Rapid Power Glitch]")
            for i in range(10):
                bp.set_psu(enabled=False)
                time.sleep(0.01)  # 10ms glitch
                bp.set_psu(enabled=True, voltage_mv=3300, current_ma=300)
                time.sleep(0.1)
                print(f"  Glitch {i+1}/10", end='\r')
            print("\n  Complete")
        elif choice == '3':
            print("\n[Voltage Drop Test]")
            voltages = [3300, 3000, 2700, 2500, 2300, 3300]
            for v in voltages:
                bp.set_psu(enabled=True, voltage_mv=v, current_ma=300)
                print(f"  Voltage: {v}mV")
                time.sleep(1)
        elif choice == '4':
            print("\n[Monitor Mode]")
            print("Watching serial output. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopped")
        elif choice == '5':
            print("\n[Curious Bolt Glitch]")
            print("⚠️  Curious Bolt backend not yet implemented")
            print("Coming soon: voltage glitching, trigger configuration")
        else:
            print("Invalid choice")


def main():
    """Main glitching setup"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  Bolt CTF Glitching Attack Setup                                    ║
║                                                                      ║
║  This tool coordinates glitching attacks on the Bolt CTF device     ║
║  while monitoring serial output for successful exploits.            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    # Setup serial monitor
    print("[*] Starting serial monitor on Bolt CTF output...")
    monitor = SerialMonitor()
    monitor.start()
    time.sleep(1)

    # Setup power control
    bp = setup_power_control()
    if not bp:
        monitor.stop()
        return 1

    try:
        # Launch glitching menu
        glitching_attack_menu(bp, monitor)

    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")

    finally:
        # Cleanup
        print("\n[*] Cleaning up...")
        monitor.stop()
        bp.disconnect()
        print("[+] Done")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
